#!/usr/bin/env python3
"""
Batch Text Methodology Processor

This script processes all available PDFs using text extraction, generates methodology summaries using OpenAI,
and updates the Google Sheet with a new "Methodology" column.
"""

import os
import sys
import time
import re
import pandas as pd
from pathlib import Path
from openai import OpenAI
from google_sheets_reader import GoogleSheetsReader

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # python-dotenv not installed, continue without it

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class BatchTextMethodologyProcessor:
    """Class to handle batch processing of PDF methodology summaries using text extraction."""
    
    def __init__(self):
        """Initialize the processor."""
        self.client = None
        self.sheets_reader = None
        self.pdf_dir = Path("papers_pdf_id")
        self.summaries_dir = Path("summaries")
        self.summaries_dir.mkdir(exist_ok=True)
        
        # Check dependencies
        if not PDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise ImportError("No PDF extraction library available. Please install PyPDF2 or pdfplumber.")
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI()
        except Exception as e:
            print(f"❌ Error initializing OpenAI client: {e}")
            print("💡 Make sure you have set your OPENAI_API_KEY environment variable")
            raise
        
        # Initialize Google Sheets reader
        try:
            self.sheets_reader = GoogleSheetsReader()
        except Exception as e:
            print(f"❌ Error initializing Google Sheets reader: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path, method='pdfplumber'):
        """Extract text from PDF using different methods."""
        text = ""
        
        try:
            if method == 'pdfplumber' and PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            
            elif method == 'PyPDF2' and PDF_AVAILABLE:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            
            else:
                print(f"❌ {method} not available. Please install it: pip install {method}")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            return None
        
        return text.strip()
    
    def format_for_google_sheets(self, text):
        """
        Convert markdown formatting to Google Sheets compatible format.
        
        Args:
            text (str): Text with markdown formatting
        
        Returns:
            str: Text formatted for Google Sheets
        """
        if not text:
            return ""
        
        # Convert **bold** to a format that works in Google Sheets
        # We'll keep the ** for now as Google Sheets can handle it in some contexts
        # or we can convert to a different format
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\n\s*\n', '\n', text)  # Remove multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)    # Replace multiple spaces with single space
        
        # Clean up bullet points for better readability
        text = re.sub(r'^\s*-\s*', '• ', text, flags=re.MULTILINE)
        
        # Limit length to avoid Google Sheets cell limits (50,000 characters)
        if len(text) > 45000:
            text = text[:45000] + "\n\n[Summary truncated due to length]"
        
        return text.strip()
    
    def generate_methodology_summary(self, pdf_path):
        """
        Generate methodology summary for a single PDF using text extraction.
        
        Args:
            pdf_path (Path): Path to the PDF file
        
        Returns:
            str: Methodology summary or None if failed
        """
        try:
            print(f"📖 Extracting text from: {pdf_path.name}")
            
            # Extract text from PDF
            method = 'pdfplumber' if PDFPLUMBER_AVAILABLE else 'PyPDF2'
            text = self.extract_text_from_pdf(pdf_path, method)
            
            if not text:
                print(f"❌ Could not extract text from {pdf_path.name}")
                return None
            
            print(f"✅ Extracted {len(text)} characters of text")
            
            # Generate summary using OpenAI
            print(f"🤖 Generating methodology summary...")
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research analyst who specializes in understanding and summarizing research methodologies from academic papers."
                    },
                    {
                        "role": "user",
                        "content": f"""Please analyze the following text from a research paper and provide a comprehensive summary of the methodology in the specified format:

TEXT TO ANALYZE:
{text[:8000]}  # Limit to avoid token limits

Please provide a summary in the following format:

1. **Methodology Overview** (2-3 sentences describing the overall approach)

2. **Key Steps in Bullet Points:**
   - Step 1: [Description]
   - Step 2: [Description]
   - Step 3: [Description]
   - [Continue as needed]

3. **Methodology Flow:**
   [Describe the logical flow and sequence of the methodology in paragraph form]

4. **Key Techniques/Tools Used:**
   - [List main techniques, algorithms, or tools used]

5. **Data Sources/Inputs:**
   - [Describe what data or inputs are used in the methodology]

6. **Output/Results:**
   - [Describe what the methodology produces or outputs]

Please focus specifically on the methodology section and make it clear and easy to understand like whats the approach, what are the key steps and architectural framework. Keep the summary concise but comprehensive."""
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            # Save individual summary to file
            summary_filename = f"{pdf_path.stem}_methodology_summary.txt"
            summary_path = self.summaries_dir / summary_filename
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"METHODOLOGY SUMMARY FOR: {pdf_path.name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(summary)
            
            print(f"💾 Individual summary saved to: {summary_path}")
            
            return summary
            
        except Exception as e:
            print(f"❌ Error generating summary for {pdf_path.name}: {e}")
            return None
    
    def process_all_pdfs(self):
        """
        Process all available PDFs and generate methodology summaries.
        
        Returns:
            dict: Dictionary mapping PDF IDs to methodology summaries
        """
        if not self.pdf_dir.exists():
            print(f"❌ PDF directory {self.pdf_dir} does not exist")
            return {}
        
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        if not pdf_files:
            print("❌ No PDF files found")
            return {}
        
        print(f"📚 Found {len(pdf_files)} PDF files to process")
        
        summaries = {}
        successful = 0
        failed = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n{'='*60}")
            print(f"Processing {i}/{len(pdf_files)}: {pdf_file.name}")
            print(f"{'='*60}")
            
            # Extract PDF ID from filename (assuming format: {id}.pdf)
            pdf_id = pdf_file.stem
            
            # Generate methodology summary
            summary = self.generate_methodology_summary(pdf_file)
            
            if summary:
                # Format for Google Sheets
                formatted_summary = self.format_for_google_sheets(summary)
                summaries[pdf_id] = formatted_summary
                successful += 1
                print(f"✅ Successfully processed: {pdf_file.name}")
            else:
                summaries[pdf_id] = "Failed to generate summary"
                failed += 1
                print(f"❌ Failed to process: {pdf_file.name}")
            
            # Add delay to avoid rate limiting
            if i < len(pdf_files):
                print("⏳ Waiting 2 seconds before next PDF...")
                time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"📊 BATCH PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"Total PDFs: {len(pdf_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(successful/len(pdf_files)*100):.1f}%")
        
        return summaries
    
    def update_google_sheet_with_methodology(self, summaries):
        """
        Update Google Sheet with methodology summaries.
        
        Args:
            summaries (dict): Dictionary mapping PDF IDs to summaries
        """
        try:
            print(f"\n📊 Updating Google Sheet with methodology summaries...")
            
            # Read current sheet data
            df = self.sheets_reader.read_sheet()
            if df.empty:
                print("❌ No data found in Google Sheet")
                return False
            
            print(f"📋 Current sheet data shape: {df.shape}")
            
            # Add methodology column
            df['Methodology'] = ''
            
            # Map summaries to rows based on PDF ID
            methodology_added = 0
            for index, row in df.iterrows():
                if 'PDF ID' in df.columns and pd.notna(row['PDF ID']):
                    pdf_id = str(row['PDF ID']).strip()
                    if pdf_id in summaries:
                        df.at[index, 'Methodology'] = summaries[pdf_id]
                        methodology_added += 1
                        print(f"✅ Added methodology for PDF ID: {pdf_id}")
            
            print(f"📝 Added methodology summaries to {methodology_added} rows")
            
            # Update the Google Sheet
            success = self.sheets_reader.update_sheet_with_pdf_info(df)
            
            if success:
                print(f"✅ Successfully updated Google Sheet with methodology column")
                
                # Save local copy
                output_file = 'processed_sheet_with_methodology.csv'
                df.to_csv(output_file, index=False)
                print(f"💾 Local copy saved to: {output_file}")
                
                return True
            else:
                print(f"❌ Failed to update Google Sheet")
                return False
                
        except Exception as e:
            print(f"❌ Error updating Google Sheet: {e}")
            return False
    
    def run_batch_processing(self):
        """Run the complete batch processing workflow."""
        print("🚀 Starting Batch Text Methodology Processing")
        print("=" * 60)
        
        try:
            # Step 1: Process all PDFs
            print("\n📚 Step 1: Processing all available PDFs...")
            summaries = self.process_all_pdfs()
            
            if not summaries:
                print("❌ No summaries generated. Exiting.")
                return
            
            # Step 2: Update Google Sheet
            print(f"\n📊 Step 2: Updating Google Sheet...")
            success = self.update_google_sheet_with_methodology(summaries)
            
            if success:
                print(f"\n🎉 BATCH PROCESSING COMPLETED SUCCESSFULLY!")
                print(f"📋 Methodology summaries added to Google Sheet")
                print(f"📁 Individual summaries saved in: {self.summaries_dir}")
            else:
                print(f"\n⚠️  Batch processing completed with errors")
                print(f"📁 Individual summaries saved in: {self.summaries_dir}")
                print(f"💡 You may need to manually update the Google Sheet")
            
        except Exception as e:
            print(f"❌ Batch processing failed: {e}")
            print(f"💡 Check your OpenAI API key and Google Sheets permissions")


def main():
    """Main function to run batch processing."""
    try:
        processor = BatchTextMethodologyProcessor()
        processor.run_batch_processing()
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        print(f"💡 Make sure you have:")
        print(f"   1. Valid OpenAI API key")
        print(f"   2. Proper Google Sheets configuration")
        print(f"   3. PDF files in papers_pdf_id/ directory")
        print(f"   4. PyPDF2 or pdfplumber installed: pip install PyPDF2 pdfplumber")


if __name__ == "__main__":
    main()
