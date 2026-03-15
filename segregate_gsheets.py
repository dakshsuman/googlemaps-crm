import pandas as pd
import os
import glob
import time
import shutil
import gspread
from gspread.exceptions import WorksheetNotFound

def process_and_upload_to_gsheets(csv_path, gc, spreadsheet_url):
    print(f"\n--- Reading {csv_path} ---")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return False

    # Check for category column (handle both upper and lower case)
    if 'main_category' in df.columns.str.lower():
        category_col = df.columns[df.columns.str.lower() == 'main_category'][0]
    elif 'categories' in df.columns.str.lower():
        category_col = df.columns[df.columns.str.lower() == 'categories'][0]
    else:
        print("No category column ('main_category' or 'categories') found in CSV. Available columns:", df.columns)
        return False

    # Fill NaN categories with 'Unknown'
    df[category_col] = df[category_col].fillna('Unknown')
    
    # Fill any other NaN/NaT values with empty string to avoid JSON serialization errors when uploading
    df = df.fillna("")
    
    # Open the Google Sheet
    print(f"Connecting to Google Sheet...")
    try:
        spreadsheet = gc.open_by_url(spreadsheet_url)
    except Exception as e:
        print(f"! Error opening spreadsheet. Check your URL and permissions.")
        print(f"! DID YOU FORGET TO SHARE THE SHEET WITH YOUR BOT? Add this email as an Editor:")
        print(f"! => scraper@scrapper-490307.iam.gserviceaccount.com <=")
        # Wait a little bit before returning so it doesn't spam
        time.sleep(5) 
        return False

    print("Uploading all data to the main sheet...")
    try:
        worksheet = spreadsheet.sheet1
        
        # We append to the main sheet so we don't accidentally overwrite past queries
        existing_data = worksheet.get_all_values()
        
        data_to_upload = []
        if not existing_data:
            # Sheet is empty, add headers first
            data_to_upload.append(df.columns.values.tolist())
            
        data_to_upload.extend(df.values.tolist())
        
        print(f"Uploading {len(df)} rows to tab '{worksheet.title}'...")
        worksheet.append_rows(data_to_upload)
        print(f" - Successfully appended data to '{worksheet.title}'")
        
    except Exception as e:
        print(f"! Error uploading to Google Sheets: {e}")
        print(f"   DID YOU FORGET TO SHARE THE SHEET WITH YOUR BOT? Add this email as an Editor:")
        print(f"   => scraper@scrapper-490307.iam.gserviceaccount.com <=")
        return False
            
    return True

def watch_exports_folder(exports_path, credentials_file, spreadsheet_url):
    print("Authenticating with Google Sheets...")
    try:
        gc = gspread.service_account(filename=credentials_file)
        print("Successfully authenticated!")
    except Exception as e:
        print(f"Failed to authenticate with Google Sheets: {e}")
        return
    if spreadsheet_url == "YOUR_GOOGLE_SHEET_URL_HERE":
        print("! WARNING: You have not set your Google Sheet URL in the script yet.")
        return

    print(f"\nWatching your exports folder at '{exports_path}' for new Google Maps Extractor CSV files...")
    
    processed_files = set()
    
    while True:
        csv_files = glob.glob(os.path.join(exports_path, "*.csv"))
        for csv_file in csv_files:
            if csv_file in processed_files:
                continue
                
            # Wait a few seconds to ensure the file finishes saving completely
            if time.time() - os.path.getmtime(csv_file) < 3:
                continue
                
            # Quick check if it's our target file (reading just the first 2 rows for speed)
            try:
                check_df = pd.read_csv(csv_file, nrows=2)
                lower_cols = check_df.columns.str.lower()
                if 'main_category' not in lower_cols and 'categories' not in lower_cols:
                    # Mark as processed anyway so we don't keep trying to read an invalid file
                    processed_files.add(csv_file)
                    continue 
            except Exception:
                continue
                
            print(f"\n>>> Scraper File Detected in Exports: {os.path.basename(csv_file)}")
            
            # Process and upload
            success = process_and_upload_to_gsheets(csv_file, gc, spreadsheet_url)
            
            if success:
                processed_files.add(csv_file)
                print(f"-> Successfully processed and uploaded to Google Sheets!")
            
            print(f"Finished processing. Continuing to watch...")
                
        time.sleep(3) # Check every 3 seconds

if __name__ == "__main__":
    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1L0CnAoE85aCC5xddnl1GVpZ4YtxW6YSbYDECECRo1JM/edit?usp=sharing"
    CREDENTIALS_FILE = r"D:\scrapper-490307-b5fd8fb67cdd.json"
    
    EXPORTS_DIR = "./exports"
    
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    
    watch_exports_folder(EXPORTS_DIR, CREDENTIALS_FILE, SPREADSHEET_URL)
