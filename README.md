# Google Sheets Reader

A Python application to read data from Google Sheets using the Google Sheets API. The sheet URL and configuration are stored in a config file for easy management.

## Features

- Read data from Google Sheets using the official Google Sheets API
- Configurable sheet URL and settings via JSON config file
- Automatic authentication with Google services
- Export data to CSV format
- Support for custom ranges and worksheet selection
- Get spreadsheet metadata and worksheet information

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the JSON file and rename it to `credentials.json`
   - Place it in the project directory

### 3. Configure the Application

1. Copy `credentials.json.template` to `credentials.json` and fill in your actual credentials (or use the downloaded file from step 2)
2. Update `config.json` with your Google Sheet URL:

```json
{
  "google_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit#gid=0",
    "worksheet_name": "Sheet1",
    "credentials_file": "credentials.json"
  },
  "settings": {
    "read_range": "A:Z",
    "header_row": 1
  }
}
```

### 4. Get Your Google Sheet ID

From your Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit#gid=0
```

The `SHEET_ID_HERE` part is what you need to put in the config file.

## Usage

### Basic Usage

```python
from google_sheets_reader import GoogleSheetsReader

# Initialize reader with default config.json
reader = GoogleSheetsReader()

# Read the entire sheet
df = reader.read_sheet()

# Print first few rows
print(df.head())

# Save to CSV
df.to_csv('output.csv', index=False)
```

### Advanced Usage

```python
# Read specific range
df = reader.read_sheet(range_name='A1:C10')

# Read different worksheet
df = reader.read_sheet(worksheet_name='Data')

# Get spreadsheet information
info = reader.get_sheet_info()
print(f"Sheet title: {info['title']}")
print("Available worksheets:")
for sheet in info['sheets']:
    print(f"  - {sheet['title']}")
```

### Command Line Usage

Run the script directly to read and display sheet data:

```bash
python google_sheets_reader.py
```

This will:
1. Read the sheet specified in `config.json`
2. Display sheet information and first 5 rows
3. Save the data to `sheet_data.csv`

## Configuration Options

The `config.json` file supports the following options:

- `google_sheet.url`: Full URL to your Google Sheet
- `google_sheet.worksheet_name`: Name of the worksheet to read (default: "Sheet1")
- `google_sheet.credentials_file`: Path to your credentials JSON file
- `settings.read_range`: Range to read (e.g., "A:Z" for all columns, "A1:C10" for specific range)
- `settings.header_row`: Whether to use the first row as column headers (1 for yes, 0 for no)

## File Structure

```
Papers_Summarizer/
├── config.json                 # Configuration file
├── credentials.json           # Google API credentials (create this)
├── credentials.json.template  # Template for credentials
├── google_sheets_reader.py    # Main application
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── token.json                # Auto-generated auth token (after first run)
```

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Make sure you've downloaded `credentials.json` from Google Cloud Console
   - Ensure the file is in the same directory as the script

2. **"Invalid Google Sheets URL"**
   - Check that your URL is in the correct format
   - Make sure the sheet ID is properly extracted from the URL

3. **"Permission denied"**
   - Ensure the Google Sheet is shared with the email associated with your credentials
   - Check that the Google Sheets API is enabled in your Google Cloud project

4. **Authentication errors**
   - Delete `token.json` and run the script again to re-authenticate
   - Make sure your credentials are valid and not expired

### Making Sheets Public

If you want to read public sheets without authentication:
1. Make your Google Sheet public (View > Anyone with the link can view)
2. Use the sheet ID directly in the URL format: `https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0`

## License

This project is open source and available under the MIT License.
