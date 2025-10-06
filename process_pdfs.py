#!/usr/bin/env python3
"""
PDF Processing Script

This script processes PDF links from your Google Sheet, downloads them,
and updates the sheet with PDF availability and unique IDs.
"""

from google_sheets_reader import GoogleSheetsReader


def main():
    """Process PDFs from Google Sheet."""
    try:
        print("🚀 Starting PDF Processing for Papers Summarizer")
        print("=" * 60)
        
        # Initialize reader
        reader = GoogleSheetsReader()
        
        # Get sheet information
        print("\n📊 Getting sheet information...")
        info = reader.get_sheet_info()
        if info:
            print(f"Sheet Title: {info.get('title', 'N/A')}")
            print("Available worksheets:")
            for sheet in info.get('sheets', []):
                print(f"  - {sheet['title']}")
        
        # Ask for link column name
        print("\n" + "=" * 60)
        link_column = input("📝 Enter the name of the column containing links (default: 'link'): ").strip()
        if not link_column:
            link_column = 'link'
        
        # Confirm before starting
        print(f"\n🔍 Will process links from column: '{link_column}'")
        print("📁 PDFs will be downloaded to: papers_pdf_id/")
        print("📝 Google Sheet will be updated with PDF information")
        
        confirm = input("\n❓ Do you want to continue? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Operation cancelled.")
            return
        
        # Start processing
        print(f"\n🎯 Starting PDF processing workflow...")
        df = reader.process_sheet_with_pdf_download(link_column)
        
        if not df.empty:
            print(f"\n✅ Processing Complete!")
            print(f"📊 Final data shape: {df.shape}")
            
            # Show summary
            pdf_available = df['PDF Available'].value_counts()
            print(f"\n📈 PDF Processing Summary:")
            for status, count in pdf_available.items():
                emoji = "📄" if status == "Yes" else "❌" if status == "Failed" else "🔗"
                print(f"  {emoji} {status}: {count}")
            
            # Show downloaded PDFs
            pdf_files = df[df['PDF Available'] == 'Yes']
            if not pdf_files.empty:
                print(f"\n📚 Downloaded PDFs:")
                for _, row in pdf_files.iterrows():
                    print(f"  🆔 {row['PDF ID']}: {row[link_column][:50]}...")
            
            print(f"\n💾 Files saved:")
            print(f"  📁 PDFs: papers_pdf_id/")
            print(f"  📄 Data: processed_sheet_data.csv")
            print(f"  📊 Sheet: Updated in Google Sheets")
            
        else:
            print("❌ No data found in sheet")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your config.json file")
        print("2. Verify credentials.json is properly set up")
        print("3. Ensure you have write permissions to the Google Sheet")
        print("4. Check your internet connection")


if __name__ == "__main__":
    main()
