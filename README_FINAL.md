# Papers PDF Processor

A streamlined tool to read Google Sheets, download PDF papers, and update the sheet with PDF information.

## 🎯 What It Does

1. **Reads** your Google Sheet with research papers
2. **Detects** PDF links automatically  
3. **Downloads** PDFs to `papers_pdf_id/` folder with unique IDs
4. **Updates** Google Sheet with new columns:
   - `PDF Available` (Yes/No/Failed)
   - `PDF ID` (unique 8-character identifier)
   - `PDF Path` (local file path)

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup Google credentials (one-time)
# Download credentials.json from Google Cloud Console
# Enable Google Sheets API
```

### 2. Configure
Edit `config.json`:
```json
{
  "google_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
    "worksheet_name": "Sheet1",
    "credentials_file": "credentials.json"
  },
  "settings": {
    "read_range": "A:Z",
    "header_row": 1
  }
}
```

### 3. Run
```bash
python papers_processor.py
```

## 📁 Files

- `papers_processor.py` - Main script
- `config.json` - Configuration
- `credentials.json` - Google API credentials
- `requirements.txt` - Dependencies
- `papers_pdf_id/` - Downloaded PDFs folder

## 📊 Example Output

Your Google Sheet will have these new columns:
| Title | Link | PDF Available | PDF ID | PDF Path |
|-------|------|---------------|--------|----------|
| Paper 1 | https://arxiv.org/pdf/123.pdf | Yes | a1b2c3d4 | papers_pdf_id/a1b2c3d4.pdf |
| Paper 2 | https://example.com/page | No | | |

## ✅ Features

- ✅ Automatic PDF detection
- ✅ Unique ID generation for each PDF
- ✅ Google Sheets integration
- ✅ Error handling and retries
- ✅ Progress tracking
- ✅ Local backup of all data

## 🔧 Troubleshooting

**Permission Error**: Delete `token.json` and re-authenticate
**PDF Not Downloaded**: Check URL format and server availability
**Sheet Not Updated**: Verify write permissions in Google Cloud Console
