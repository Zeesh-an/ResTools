#!/usr/bin/env python3
"""
Google Sheets Reader

This script reads data from a Google Sheet using the Google Sheets API.
The sheet URL and configuration are stored in config.json.
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


class GoogleSheetsReader:
    """A class to read data from Google Sheets."""
    
    # Scopes required for Google Sheets API
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, config_file='config.json'):
        """
        Initialize the Google Sheets Reader.
        
        Args:
            config_file (str): Path to the configuration file
        """
        self.config = self._load_config(config_file)
        self.service = None
        self._authenticate()
        
        # Setup PDF download directory
        self.pdf_dir = Path("papers_pdf_id")
        self.pdf_dir.mkdir(exist_ok=True)
    
    def _load_config(self, config_file):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file '{config_file}' not found.")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file '{config_file}'.")
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        creds = None
        token_file = 'token.json'
        
        # Load existing token
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credentials_file = self.config['google_sheet']['credentials_file']
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{credentials_file}' not found. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('sheets', 'v4', credentials=creds)
    
    def _extract_sheet_id(self, url):
        """Extract sheet ID from Google Sheets URL."""
        # Pattern to match Google Sheets URL
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid Google Sheets URL: {url}")
        return match.group(1)
    
    def read_sheet(self, sheet_id=None, worksheet_name=None, range_name=None):
        """
        Read data from Google Sheet.
        
        Args:
            sheet_id (str, optional): Sheet ID. If not provided, uses config.
            worksheet_name (str, optional): Worksheet name. If not provided, uses config.
            range_name (str, optional): Range to read. If not provided, uses config.
        
        Returns:
            pandas.DataFrame: Sheet data as DataFrame
        """
        # Use config values if parameters not provided
        if sheet_id is None:
            url = self.config['google_sheet']['url']
            sheet_id = self._extract_sheet_id(url)
        
        if worksheet_name is None:
            worksheet_name = self.config['google_sheet']['worksheet_name']
        
        if range_name is None:
            range_name = self.config['settings']['read_range']
        
        # Construct the full range
        full_range = f"{worksheet_name}!{range_name}"
        
        try:
            # Call the Sheets API
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=sheet_id,
                range=full_range
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print('No data found.')
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(values)
            
            # Set first row as header if specified in config
            if self.config['settings']['header_row'] and len(df) > 0:
                df.columns = df.iloc[0]
                df = df.drop(df.index[0]).reset_index(drop=True)
            
            return df
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return pd.DataFrame()
    
    def get_sheet_info(self, sheet_id=None):
        """
        Get information about the spreadsheet.
        
        Args:
            sheet_id (str, optional): Sheet ID. If not provided, uses config.
        
        Returns:
            dict: Spreadsheet metadata
        """
        if sheet_id is None:
            url = self.config['google_sheet']['url']
            sheet_id = self._extract_sheet_id(url)
        
        try:
            sheet = self.service.spreadsheets()
            result = sheet.get(spreadsheetId=sheet_id).execute()
            
            info = {
                'title': result.get('properties', {}).get('title', ''),
                'sheets': []
            }
            
            for sheet_info in result.get('sheets', []):
                info['sheets'].append({
                    'title': sheet_info.get('properties', {}).get('title', ''),
                    'sheet_id': sheet_info.get('properties', {}).get('sheetId', ''),
                    'grid_properties': sheet_info.get('properties', {}).get('gridProperties', {})
                })
            
            return info
            
        except HttpError as err:
            print(f"An error occurred: {err}")
            return {}
    
    def _is_pdf_url(self, url):
        """
        Check if a URL points to a PDF file.
        
        Args:
            url (str): URL to check
        
        Returns:
            bool: True if URL appears to be a PDF
        """
        if not url or not isinstance(url, str):
            return False
        
        # Check URL extension
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Direct PDF file extensions
        if path.endswith('.pdf'):
            return True
        
        # Common PDF URL patterns
        pdf_patterns = [
            'pdf', '/pdf/', 'format=pdf', 'type=pdf', 
            'filetype=pdf', 'download=pdf'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in pdf_patterns)
    
    def _generate_unique_id(self):
        """Generate a unique ID for PDF files."""
        return str(uuid.uuid4())[:8]  # Short unique ID
    
    def _download_pdf(self, url, unique_id):
        """
        Download a PDF from the given URL.
        
        Args:
            url (str): URL of the PDF to download
            unique_id (str): Unique identifier for the file
        
        Returns:
            str: Path to downloaded file, or None if failed
        """
        try:
            print(f"Downloading PDF from: {url}")
            
            # Set headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Make request with timeout
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check if content is actually PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                print(f"Warning: Content type is {content_type}, may not be a PDF")
            
            # Create filename
            filename = f"{unique_id}.pdf"
            filepath = self.pdf_dir / filename
            
            # Download file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Successfully downloaded: {filepath}")
            return str(filepath)
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error downloading {url}: {e}")
            return None
    
    def process_links_and_download_pdfs(self, df, link_column='link'):
        """
        Process links in DataFrame, download PDFs, and add PDF status column.
        
        Args:
            df (pandas.DataFrame): DataFrame containing links
            link_column (str): Name of the column containing links
        
        Returns:
            pandas.DataFrame: Updated DataFrame with PDF status and IDs
        """
        if link_column not in df.columns:
            print(f"Warning: Column '{link_column}' not found in DataFrame")
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
            
            print(f"\nProcessing row {index + 1}/{total_links}: {url[:50]}...")
            
            if self._is_pdf_url(url):
                print("  -> Detected as PDF")
                unique_id = self._generate_unique_id()
                
                # Download PDF
                pdf_path = self._download_pdf(url, unique_id)
                
                if pdf_path:
                    df.at[index, 'PDF Available'] = 'Yes'
                    df.at[index, 'PDF ID'] = unique_id
                    df.at[index, 'PDF Path'] = pdf_path
                    pdf_count += 1
                    print(f"  -> PDF downloaded with ID: {unique_id}")
                else:
                    df.at[index, 'PDF Available'] = 'Failed'
                    print("  -> PDF download failed")
                
                # Small delay to be respectful to servers
                time.sleep(1)
            else:
                print("  -> Not a PDF link")
        
        print(f"\nProcessing complete!")
        print(f"Total links processed: {total_links}")
        print(f"PDFs downloaded: {pdf_count}")
        print(f"PDFs stored in: {self.pdf_dir}")
        
        return df
    
    def update_sheet_with_pdf_info(self, df, sheet_id=None, worksheet_name=None):
        """
        Update the Google Sheet with PDF information.
        
        Args:
            df (pandas.DataFrame): DataFrame with PDF information
            sheet_id (str, optional): Sheet ID. If not provided, uses config.
            worksheet_name (str, optional): Worksheet name. If not provided, uses config.
        """
        if sheet_id is None:
            url = self.config['google_sheet']['url']
            sheet_id = self._extract_sheet_id(url)
        
        if worksheet_name is None:
            worksheet_name = self.config['google_sheet']['worksheet_name']
        
        try:
            print(f"Updating sheet: {sheet_id}")
            print(f"Worksheet: {worksheet_name}")
            print(f"Data shape: {df.shape}")
            
            # Clean the data - replace NaN with empty strings and handle special characters
            df_clean = df.fillna('')  # Replace NaN with empty strings
            
            # Prepare data for update (including headers)
            headers = df_clean.columns.tolist()
            
            # Convert DataFrame to list, ensuring all values are strings
            data_rows = []
            for _, row in df_clean.iterrows():
                row_data = []
                for value in row:
                    if pd.isna(value):
                        row_data.append('')
                    else:
                        # Convert to string and handle any problematic characters
                        str_value = str(value)
                        # Replace any problematic characters that might cause JSON issues
                        str_value = str_value.replace('\n', ' ').replace('\r', ' ')
                        row_data.append(str_value)
                data_rows.append(row_data)
            
            data = [headers] + data_rows
            
            # Determine the range based on data size
            end_col = chr(ord('A') + len(headers) - 1)  # Convert to Excel column letter
            end_row = len(data)
            range_name = f"{worksheet_name}!A1:{end_col}{end_row}"
            
            print(f"Updating range: {range_name}")
            
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            updated_range = result.get('updatedRange', 'Unknown')
            print(f"✅ Successfully updated {updated_cells} cells in range {updated_range}")
            
            return True
            
        except HttpError as err:
            print(f"❌ Error updating sheet: {err}")
            if err.resp.status == 403:
                print("🔐 Permission denied. Please check:")
                print("  1. Your credentials have write access")
                print("  2. The sheet is shared with your account")
                print("  3. Google Sheets API is enabled")
            elif err.resp.status == 400:
                print("📝 Bad request. The data format might be invalid")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def process_sheet_with_pdf_download(self, link_column='link'):
        """
        Complete workflow: read sheet, process PDFs, update sheet.
        
        Args:
            link_column (str): Name of the column containing links
        
        Returns:
            pandas.DataFrame: Final processed DataFrame
        """
        print("Starting complete PDF processing workflow...")
        
        # Step 1: Read the sheet
        print("\n1. Reading Google Sheet...")
        df = self.read_sheet()
        
        if df.empty:
            print("No data found in sheet")
            return df
        
        # Step 2: Process PDFs
        print("\n2. Processing PDF links...")
        df = self.process_links_and_download_pdfs(df, link_column)
        
        # Step 3: Update the sheet
        print("\n3. Updating Google Sheet...")
        update_success = self.update_sheet_with_pdf_info(df)
        if not update_success:
            print("⚠️  Google Sheet update failed. Local data is saved.")
            print("💡 You can try running 'python update_sheet.py' to retry the update.")
        
        # Step 4: Save local copy
        output_file = 'processed_sheet_data.csv'
        df.to_csv(output_file, index=False)
        print(f"\n4. Local copy saved to: {output_file}")
        
        return df


def main():
    """Main function to demonstrate usage."""
    try:
        # Initialize reader
        reader = GoogleSheetsReader()
        
        # Get sheet information
        print("Getting sheet information...")
        info = reader.get_sheet_info()
        if info:
            print(f"Sheet Title: {info.get('title', 'N/A')}")
            print("Available worksheets:")
            for sheet in info.get('sheets', []):
                print(f"  - {sheet['title']}")
        
        # Ask user what they want to do
        print("\n" + "="*50)
        print("What would you like to do?")
        print("1. Just read the sheet (original functionality)")
        print("2. Process PDFs and update sheet (new functionality)")
        print("="*50)
        
        choice = input("Enter your choice (1 or 2): ").strip()
        
        if choice == "1":
            # Original functionality - just read
            print("\nReading sheet data...")
            df = reader.read_sheet()
            
            if not df.empty:
                print(f"Data shape: {df.shape}")
                print("\nFirst 5 rows:")
                print(df.head())
                
                # Save to CSV
                output_file = 'sheet_data.csv'
                df.to_csv(output_file, index=False)
                print(f"\nData saved to {output_file}")
            else:
                print("No data to display.")
                
        elif choice == "2":
            # New functionality - process PDFs
            link_column = input("Enter the name of the column containing links (default: 'link'): ").strip()
            if not link_column:
                link_column = 'link'
            
            print(f"\nStarting PDF processing workflow with column: '{link_column}'")
            df = reader.process_sheet_with_pdf_download(link_column)
            
            if not df.empty:
                print(f"\nFinal data shape: {df.shape}")
                print("\nFirst 5 rows with PDF information:")
                print(df.head())
                
                # Show summary
                pdf_available = df['PDF Available'].value_counts()
                print(f"\nPDF Processing Summary:")
                for status, count in pdf_available.items():
                    print(f"  {status}: {count}")
                    
        else:
            print("Invalid choice. Please run the script again and choose 1 or 2.")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease make sure:")
        print("1. Your config.json file is properly configured")
        print("2. You have downloaded credentials.json from Google Cloud Console")
        print("3. The Google Sheet is accessible and you have write permissions")
        print("4. You have internet connection for PDF downloads")


if __name__ == "__main__":
    main()
