# Papers Summarizer - Research Methodology Analysis Tool

A comprehensive tool for downloading research papers from Google Sheets, processing PDFs, and generating AI-powered methodology summaries using OpenAI's GPT-4.

## 🚀 Features

- **Google Sheets Integration**: Read paper links from Google Sheets
- **PDF Download**: Automatically download PDFs from provided links
- **AI-Powered Analysis**: Generate comprehensive methodology summaries using OpenAI GPT-4
- **Batch Processing**: Process multiple PDFs at once
- **Google Sheets Update**: Add methodology summaries back to your spreadsheet
- **Individual Processing**: Process single PDFs for testing

## 📁 Project Structure

```
ResTools/
├── batch_direct_upload_processor.py  # Main batch processor (RECOMMENDED)
├── pdf_direct_upload.py             # Single PDF processor
├── process_pdfs.py                  # PDF downloader from Google Sheets
├── google_sheets_reader.py          # Google Sheets integration
├── config.json                      # Configuration file
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git ignore rules
├── papers_pdf_id/                   # Downloaded PDF files (ignored by git)
├── summaries/                       # Generated methodology summaries (ignored by git)
└── README.md                        # This file
```

## 🛠️ Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Create credentials (OAuth 2.0 Client ID)
5. Download `credentials.json` and place it in the project root
6. Copy `credentials.json.template` to `credentials.json` and fill in your details

### 3. Set Up OpenAI API Key

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
```

Or set environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 4. Configure Google Sheet

Update `config.json` with your Google Sheet details:

```json
{
  "google_sheet": {
    "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
    "worksheet_name": "Sheet1",
    "credentials_file": "credentials.json"
  },
  "settings": {
    "read_range": "A:Z",
    "header_row": true
  }
}
```

## 🎯 Usage

### Complete Workflow (Recommended)

1. **Download PDFs from Google Sheets**:
   ```bash
   python process_pdfs.py
   ```
   - Reads paper links from your Google Sheet
   - Downloads PDFs to `papers_pdf_id/` directory
   - Updates Google Sheet with PDF availability status

2. **Generate Methodology Summaries for All PDFs**:
   ```bash
   python batch_direct_upload_processor.py
   ```
   - Processes all available PDFs
   - Generates AI-powered methodology summaries
   - Adds "Methodology" column to Google Sheet
   - Saves individual summaries to `summaries/` directory

### Individual PDF Processing

For testing or single PDF analysis:

```bash
python pdf_direct_upload.py
```

## 📋 Methodology Summary Format

Each generated summary includes:

1. **Methodology Overview** (2-3 sentences describing the overall approach)
2. **Key Steps in Bullet Points** (Detailed step-by-step breakdown)
3. **Methodology Flow** (Logical sequence and flow description)
4. **Key Techniques/Tools Used** (Algorithms, frameworks, tools)
5. **Data Sources/Inputs** (What data or inputs are used)
6. **Output/Results** (What the methodology produces)

## 🔧 Configuration

### Google Sheets Setup

Your Google Sheet should have:
- A column with paper links (default: "link")
- Headers in the first row
- Proper sharing permissions for your Google account

### OpenAI Configuration

- Uses GPT-4 Turbo for analysis
- Handles file uploads up to 512MB
- Includes rate limiting to avoid API limits
- Fallback methods for reliability

## 📊 Output Files

- `processed_sheet_with_methodology.csv` - Local backup of updated sheet data
- `summaries/*.txt` - Individual methodology summaries for each PDF
- `papers_pdf_id/*.pdf` - Downloaded PDF files

## 🚨 Important Notes

### File Management
- PDF files and summaries are **ignored by Git** (see `.gitignore`)
- Keep your API keys secure and never commit them
- Regular backups of your Google Sheet are recommended

### API Limits
- OpenAI API has rate limits and costs per request
- Batch processing includes delays between requests
- Monitor your OpenAI usage and billing

### Error Handling
- Failed PDF downloads are marked in the sheet
- Failed summaries are logged with error messages
- Processing continues even if individual files fail

## 🔍 Troubleshooting

### Common Issues

1. **Google Sheets Permission Error**:
   - Check if `credentials.json` is properly configured
   - Ensure your Google account has access to the sheet
   - Verify Google Sheets API is enabled

2. **OpenAI API Error**:
   - Verify your API key is correct and has sufficient credits
   - Check if you have access to GPT-4 models
   - Ensure your API key has file upload permissions

3. **PDF Download Failures**:
   - Check if URLs are accessible
   - Verify PDF links are direct download links
   - Some academic sites may require authentication

4. **Memory Issues**:
   - Large PDFs may cause memory issues
   - Consider processing smaller batches
   - Monitor system resources during batch processing

### Getting Help

1. Check the error messages in the console output
2. Verify all configuration files are properly set up
3. Test with a single PDF first using `pdf_direct_upload.py`
4. Check OpenAI API status and your account limits

## 📈 Performance Tips

- **Batch Processing**: Use `batch_direct_upload_processor.py` for multiple PDFs
- **Rate Limiting**: Built-in delays prevent API rate limit issues
- **Error Recovery**: Failed files don't stop the entire batch
- **Local Storage**: Summaries are saved locally for backup

## 🔒 Security

- API keys are stored in `.env` file (ignored by Git)
- Google credentials are stored in `credentials.json` (ignored by Git)
- No sensitive data is committed to version control
- PDF files and summaries are kept local

## 📝 License

This project is for research and educational purposes. Please ensure you have proper permissions to download and analyze the research papers you're processing.

---

**Happy Research Analysis! 🎓📚**