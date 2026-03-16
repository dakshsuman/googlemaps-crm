from flask import Flask, render_template, request, jsonify
import gspread
import os
import json

app = Flask(__name__)

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1L0CnAoE85aCC5xddnl1GVpZ4YtxW6YSbYDECECRo1JM/edit?usp=sharing"
CREDENTIALS_FILE = r"D:\scrapper-490307-b5fd8fb67cdd.json"

def get_worksheet():
    # To support Vercel later, we check if credentials file exists, else we can fall back to ENV vars
    if os.path.exists(CREDENTIALS_FILE):
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
    else:
        # Assuming Vercel environment where we load from dict
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            creds_dict = json.loads(creds_json)
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            raise Exception("No credentials found!")
        
    spreadsheet = gc.open_by_url(SPREADSHEET_URL)
    return spreadsheet.sheet1

def ensure_columns(worksheet):
    # Fetch headers explicitly
    headers = worksheet.row_values(1)
    if not headers:
        return headers
        
    # Check if we need to add columns to the grid itself
    needed_cols = 0
    if "CRM_Status" not in headers: needed_cols += 1
    if "CRM_Notes" not in headers: needed_cols += 1
    
    if needed_cols > 0 and worksheet.col_count < len(headers) + needed_cols:
        worksheet.add_cols(len(headers) + needed_cols - worksheet.col_count)
        
    # Ensure Status column exists
    if "CRM_Status" not in headers:
        headers.append("CRM_Status")
        worksheet.update_cell(1, len(headers), "CRM_Status")
        
    # Ensure Notes column exists
    if "CRM_Notes" not in headers:
        headers.append("CRM_Notes")
        worksheet.update_cell(1, len(headers), "CRM_Notes")

    return headers

def get_all_leads():
    try:
        worksheet = get_worksheet()
        headers = ensure_columns(worksheet)
        
        # Read all data manually to perfectly align rows and handle empty cells
        all_values = worksheet.get_all_values()
        
        leads = []
        if len(all_values) > 1:
            data_rows = all_values[1:]
            
            for idx, row in enumerate(data_rows):
                # idx starts at 0, representing row 2 in the sheet
                row_num = idx + 2 
                
                # Zip headers with row array to create a dict, buffering missing empty cells
                row_dict = {headers[i]: (row[i] if i < len(row) else '') for i in range(len(headers))}
                
                # Extract fields expected by CRM frontend
                category_val = row_dict.get('main_category', row_dict.get('categories', row_dict.get('category', 'Unknown')))
                
                # Handle missig rating/reviews
                try: rating = float(row_dict.get('rating', 0.0) or 0.0)
                except: rating = 0.0
                
                try: reviews = int(row_dict.get('reviews', 0) or 0)
                except: reviews = 0
                
                address_str = row_dict.get('address', '')
                state_val = 'Unknown'
                if address_str:
                    import re
                    match = re.search(r'([A-Za-z\s]+)(?:,\s*)?\d{5,6}', address_str)
                    if match:
                        state_val = match.group(1).split(',')[-1].strip()
                
                lead = {
                    'id': row_num,  # we use Google Sheet row number as the ID!
                    'place_id': row_dict.get('place_id', ''),
                    'name': row_dict.get('name', 'Unknown'),
                    'phone': row_dict.get('phone', ''),
                    'website': row_dict.get('website', ''),
                    'rating': rating,
                    'reviews': reviews,
                    'address': address_str,
                    'state': state_val,
                    'category': category_val,
                    'status': row_dict.get('CRM_Status', '') or 'Pending',
                    'notes': row_dict.get('CRM_Notes', '')
                }
                leads.append(lead)
            
        return leads, worksheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return [], None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    leads, _ = get_all_leads()
    stats = {
        'Pending': 0, 'In Progress': 0, 'Accepted': 0, 
        'Rejected': 0, 'No Answer': 0, 'Call Back': 0, 'Total': 0
    }
    
    for lead in leads:
        status = lead['status']
        if status in stats:
            stats[status] += 1
        else:
            stats['Pending'] += 1
        stats['Total'] += 1
        
    return jsonify(stats)

@app.route('/api/leads', methods=['GET'])
def get_leads_api():
    status_filter = request.args.get('status', 'Pending')
    search_q = request.args.get('search', '').lower()
    
    leads, _ = get_all_leads()
    
    filtered_leads = []
    for lead in leads:
        if status_filter and status_filter != 'All' and lead['status'] != status_filter:
            continue
            
        if search_q:
            if search_q not in str(lead['name']).lower() and search_q not in str(lead['phone']).lower():
                continue
                
        filtered_leads.append(lead)
        
    return jsonify(filtered_leads)

@app.route('/api/leads/<int:row_id>', methods=['PUT', 'GET'])
def update_lead(row_id):
    if request.method == 'GET':
        leads, _ = get_all_leads()
        lead = next((l for l in leads if l['id'] == row_id), None)
        return jsonify(lead or {}), (200 if lead else 404)
        
    data = request.json
    status = data.get('status')
    notes = data.get('notes')
    
    if not status and notes is None:
        return jsonify({"success": False, "error": "No data provided"}), 400
        
    try:
        worksheet = get_worksheet()
        headers = ensure_columns(worksheet)
        
        updates = []
        if status is not None:
            status_col_idx = headers.index('CRM_Status') + 1
            cell = gspread.utils.rowcol_to_a1(row_id, status_col_idx)
            updates.append({'range': cell, 'values': [[status]]})
            
        if notes is not None:
            notes_col_idx = headers.index('CRM_Notes') + 1
            cell = gspread.utils.rowcol_to_a1(row_id, notes_col_idx)
            updates.append({'range': cell, 'values': [[notes]]})
            
        if updates:
            worksheet.batch_update(updates)
            
        return jsonify({"success": True})
    except Exception as e:
        print(f"Update error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask Web App connected to Google Sheets...")
    app.run(host='0.0.0.0', port=5000, debug=True)
