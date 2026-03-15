import pandas as pd
import os
import glob
import time

def process_and_segregate_csv(csv_path, output_excel_path):
    print(f"Reading {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Check if 'MAIN_CATEGORY' exists in the columns
    if 'MAIN_CATEGORY' not in df.columns:
        print("Column 'MAIN_CATEGORY' not found in the CSV. Using 'CATEGORIES' if available.")
        if 'CATEGORIES' in df.columns:
             category_col = 'CATEGORIES'
        else:
             print("No category column found. Available columns:", df.columns)
             return
    else:
        category_col = 'MAIN_CATEGORY'

    # Fill NaN categories with 'Unknown'
    df[category_col] = df[category_col].fillna('Unknown')
    
    print(f"Segregating by {category_col} and saving to {output_excel_path}...")
    
    # Create an Excel writer object
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        # Group by the category column
        grouped = df.groupby(category_col)
        
        for category, group_df in grouped:
            # Sheet names in Excel cannot exceed 31 characters and cannot contain certain characters
            safe_sheet_name = str(category).replace('/', '_').replace('\\', '_').replace('?', '').replace('*', '').replace('[', '').replace(']', '')[:31]
            
            # If sheet name is empty, name it 'Unknown'
            if not safe_sheet_name.strip():
                safe_sheet_name = 'Unknown'
                
            group_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            print(f" - Added sheet: {safe_sheet_name} with {len(group_df)} rows")
            
    print(f"Successfully created {output_excel_path}")

def watch_folder_for_csv(folder_path, output_dir):
    print(f"Watching folder '{folder_path}' for new CSV files...")
    processed_files = set()
    
    while True:
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
        for csv_file in csv_files:
            if csv_file not in processed_files:
                filename = os.path.basename(csv_file)
                base_name = os.path.splitext(filename)[0]
                output_excel = os.path.join(output_dir, f"{base_name}_segregated.xlsx")
                
                print(f"New file detected: {csv_file}")
                process_and_segregate_csv(csv_file, output_excel)
                processed_files.add(csv_file)
                
        time.sleep(5) # Check every 5 seconds

if __name__ == "__main__":
    # You can change these paths. By default, it looks for an 'exports' folder
    # where you save your Google Maps Extractor CSVs.
    WATCH_DIR = "./exports"
    
    # 💡 HOW TO UPLOAD AUTOMATICALLY TO MS EXCEL ONLINE 💡
    # Change this OUTPUT_DIR path to your local OneDrive directory path. 
    # Example: OUTPUT_DIR = r"C:\Users\Daksh\OneDrive\Documents"
    # Once saved there, Windows automatically syncs it to your Online MS Excel!
    OUTPUT_DIR = "./output_excel"
    
    os.makedirs(WATCH_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=====================================================")
    print(f"Put your downloaded CSV files into the '{WATCH_DIR}' folder.")
    print(f"The segregated Excel files will appear in '{OUTPUT_DIR}'.")
    print("=====================================================")
    
    watch_folder_for_csv(WATCH_DIR, OUTPUT_DIR)
