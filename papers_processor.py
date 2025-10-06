#!/usr/bin/env python3
"""
Papers PDF Processor

A streamlined script to read Google Sheets, download PDF papers,
and update the sheet with PDF availability and unique IDs.
"""

import json
import os
import pandas as pd
import requests
import uuid
from urllib.parse import urlparse
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import time


class PapersProcessor:
    """Main class for processing papers and updating Google Sheets."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, config_file='config.json'):
        """Initialize the processor."""
        self.config = self._load_config(config_file)
        self.service = None
        self.pdf_dir = Path("papers_pdf_id")
        self.pdf_dir.mkdir(exist_ok=True)
        self._authenticate()
    
    def _load_config(self, config_file):
        """Load configuration from JSON file."""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        creds = None
        token_file = 'token.json'
        
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config['google_sheet']['credentials_file'], self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('sheets', 'v4', credentials=creds)
    
    def _extract_sheet_id(self, url):
        """Extract sheet ID from Google Sheets URL."""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid Google Sheets URL: {url}")
        return match.group(1)
    
    def _is_pdf_url(self, url):
        """Check if a URL points to a PDF file."""
        if not url or not isinstance(url, str):
            return False
        
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        if path.endswith('.pdf'):
            return True
        
        pdf_patterns = ['pdf', '/pdf/', 'format=pdf', 'type=pdf', 'filetype=pdf', 'download=pdf']
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in pdf_patterns)
    
    def _download_pdf(self, url, unique_id):
        """Download a PDF from the given URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            filename = f"{unique_id}.pdf"
            filepath = self.pdf_dir / filename
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(filepath)
            
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None
    
    def read_sheet(self):
        """Read data from Google Sheet."""
        url = self.config['google_sheet']['url']
        sheet_id = self._extract_sheet_id(url)
        worksheet_name = self.config['google_sheet']['worksheet_name']
        range_name = self.config['settings']['read_range']
        
        full_range = f"{worksheet_name}!{range_name}"
        
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=sheet_id,
                range=full_range
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return pd.DataFrame()
            
            df = pd.DataFrame(values)
            
            if self.config['settings']['header_row'] and len(df) > 0:
                df.columns = df.iloc[0]
                df = df.drop(df.index[0]).reset_index(drop=True)
            
            return df
            
        except HttpError as err:
            print(f"Error reading sheet: {err}")
            return pd.DataFrame()
    
    def process_pdfs(self, df, link_column='link'):
        """Process PDF links and download them."""
        if link_column not in df.columns:
            print(f"Column '{link_column}' not found")
            return df
        
        # Add new columns
        df['PDF Available'] = 'No'
        df['PDF ID'] = ''
        df['PDF Path'] = ''
        
        total_links = len(df)
        pdf_count = 0
        
        print(f"Processing {total_links} links...")
        
        for index, row in df.iterrows():
            url = row[link_column]
            
            if pd.isna(url) or not url.strip():
                continue
            
            print(f"Processing {index + 1}/{total_links}: {url[:50]}...")
            
            if self._is_pdf_url(url):
                unique_id = str(uuid.uuid4())[:8]
                pdf_path = self._download_pdf(url, unique_id)
                
                if pdf_path:
                    df.at[index, 'PDF Available'] = 'Yes'
                    df.at[index, 'PDF ID'] = unique_id
                    df.at[index, 'PDF Path'] = pdf_path
                    pdf_count += 1
                    print(f"  ✅ Downloaded: {unique_id}")
                else:
                    df.at[index, 'PDF Available'] = 'Failed'
                    print(f"  ❌ Failed")
                
                time.sleep(1)  # Be respectful to servers
            else:
                print(f"  🔗 Not a PDF")
        
        print(f"\nCompleted: {pdf_count} PDFs downloaded")
        return df
    
    def update_sheet(self, df):
        """Update Google Sheet with processed data."""
        url = self.config['google_sheet']['url']
        sheet_id = self._extract_sheet_id(url)
        worksheet_name = self.config['google_sheet']['worksheet_name']
        
        try:
            # Clean data for Google Sheets
            df_clean = df.fillna('')
            headers = df_clean.columns.tolist()
            
            # Convert to list with proper formatting
            data_rows = []
            for _, row in df_clean.iterrows():
                row_data = []
                for value in row:
                    if pd.isna(value):
                        row_data.append('')
                    else:
                        str_value = str(value).replace('\n', ' ').replace('\r', ' ')
                        row_data.append(str_value)
                data_rows.append(row_data)
            
            data = [headers] + data_rows
            
            # Calculate range
            end_col = chr(ord('A') + len(headers) - 1)
            end_row = len(data)
            range_name = f"{worksheet_name}!A1:{end_col}{end_row}"
            
            body = {'values': data}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            print(f"✅ Updated {updated_cells} cells in Google Sheet")
            return True
            
        except HttpError as err:
            print(f"❌ Error updating sheet: {err}")
            return False
    
    def run(self, link_column='link'):
        """Run the complete workflow."""
        print("🚀 Starting Papers Processing Workflow")
        print("=" * 50)
        
        # Step 1: Read sheet
        print("📖 Reading Google Sheet...")
        df = self.read_sheet()
        
        if df.empty:
            print("❌ No data found")
            return
        
        print(f"✅ Loaded {len(df)} rows")
        
        # Step 2: Process PDFs
        print(f"\n📄 Processing PDF links from column '{link_column}'...")
        df = self.process_pdfs(df, link_column)
        
        # Step 3: Update sheet
        print("\n📝 Updating Google Sheet...")
        success = self.update_sheet(df)
        
        # Step 4: Save local copy
        output_file = 'processed_papers.csv'
        df.to_csv(output_file, index=False)
        print(f"💾 Local copy saved: {output_file}")
        
        # Summary
        pdf_summary = df['PDF Available'].value_counts()
        print(f"\n📊 Summary:")
        for status, count in pdf_summary.items():
            emoji = "📄" if status == "Yes" else "❌" if status == "Failed" else "🔗"
            print(f"  {emoji} {status}: {count}")
        
        if success:
            print("\n🎉 All done! Check your Google Sheet for updates.")
        else:
            print("\n⚠️  Sheet update failed, but local data is saved.")


def main():
    """Main function."""
    try:
        processor = PapersProcessor()
        link_column = input("Enter link column name (default: 'link'): ").strip() or 'link'
        processor.run(link_column)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Check your config.json and credentials.json files")


if __name__ == "__main__":
    main()
