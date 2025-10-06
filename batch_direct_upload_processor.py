#!/usr/bin/env python3
"""
Batch Direct Upload Processor

This script processes all available PDFs using the existing pdf_direct_upload.py functions,
generates methodology summaries using OpenAI, and updates the Google Sheet with a new "Methodology" column.
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


class BatchDirectUploadProcessor:
    """Class to handle batch processing using existing pdf_direct_upload.py functions."""
    
    def __init__(self):
        """Initialize the processor."""
        self.client = None
        self.sheets_reader = None
        self.pdf_dir = Path("papers_pdf_id")
        self.summaries_dir = Path("summaries")
        self.summaries_dir.mkdir(exist_ok=True)
        
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
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\n\s*\n', '\n', text)  # Remove multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)    # Replace multiple spaces with single space
        
        # Clean up bullet points for better readability
        text = re.sub(r'^\s*-\s*', '• ', text, flags=re.MULTILINE)
        
        # Limit length to avoid Google Sheets cell limits (50,000 characters)
        if len(text) > 45000:
            text = text[:45000] + "\n\n[Summary truncated due to length]"
        
        return text.strip()
    
    def upload_pdf_to_openai(self, pdf_path):
        """
        Upload PDF to OpenAI using the same method as pdf_direct_upload.py
        
        Args:
            pdf_path (Path): Path to the PDF file
        
        Returns:
            str: File ID if successful, None if failed
        """
        try:
            print(f"📤 Uploading PDF: {pdf_path.name}")
            with open(pdf_path, "rb") as file:
                uploaded_file = self.client.files.create(
                    file=file,
                    purpose="assistants"
                )
            print(f"✅ PDF uploaded successfully. File ID: {uploaded_file.id}")
            return uploaded_file.id
            
        except Exception as e:
            print(f"❌ Error uploading PDF: {e}")
            return None
    
    def generate_methodology_summary_with_assistants(self, file_id, pdf_name):
        """
        Generate methodology summary using Assistants API (same as pdf_direct_upload.py)
        
        Args:
            file_id (str): OpenAI file ID
            pdf_name (str): Name of the PDF file
        
        Returns:
            str: Methodology summary or None if failed
        """
        try:
            print(f"🤖 Analyzing methodology for: {pdf_name}")
            
            # Create an assistant (same as pdf_direct_upload.py)
            assistant = self.client.beta.assistants.create(
                name="PDF Methodology Analyzer",
                instructions="""You are an expert research analyst who specializes in understanding and summarizing research methodologies from academic papers. 
                
                When given a PDF file, analyze it and provide a comprehensive summary of the methodology in the following format:

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

                Please focus specifically on the methodology section and make it clear and easy to understand like whats the approach, what are the key steps and architectural framework.""",
                model="gpt-4-turbo-preview",
                tools=[{"type": "file_search"}]
            )
            
            # Create a thread
            thread = self.client.beta.threads.create()
            
            # Add the file to the thread
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Please analyze the attached PDF file and provide a comprehensive methodology summary in the specified format.",
                attachments=[
                    {
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    }
                ]
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            print("⏳ Analyzing PDF with Assistants API...")
            
            # Wait for completion
            while run.status in ['queued', 'in_progress', 'requires_action']:
                time.sleep(2)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                print(f"   Status: {run.status}")
            
            if run.status == 'completed':
                # Get the response
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                response = messages.data[0].content[0].text.value
                
                # Save individual summary to file
                summary_filename = f"{Path(pdf_name).stem}_methodology_summary.txt"
                summary_path = self.summaries_dir / summary_filename
                
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"METHODOLOGY SUMMARY FOR: {pdf_name}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(response)
                
                print(f"💾 Individual summary saved to: {summary_path}")
                
                return response
                
            else:
                print(f"❌ Analysis failed with status: {run.status}")
                return None
                
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            return None
    
    def generate_methodology_summary_with_chat(self, file_id, pdf_name):
        """
        Generate methodology summary using Chat Completions (fallback method from pdf_direct_upload.py)
        
        Args:
            file_id (str): OpenAI file ID
            pdf_name (str): Name of the PDF file
        
        Returns:
            str: Methodology summary or None if failed
        """
        try:
            print(f"🤖 Using Chat Completions fallback method...")
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert research analyst who specializes in understanding and summarizing research methodologies from academic papers."
                    },
                    {
                        "role": "user",
                        "content": f"""I have uploaded a PDF file with ID: {file_id}

Please analyze this PDF and provide a comprehensive summary of the methodology in the following format:

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

Please focus specifically on the methodology section and make it clear and easy to understand like whats the approach, what are the key steps and architectural framework.

Note: The file ID is {file_id} - please reference this file in your analysis."""
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            # Save individual summary to file
            summary_filename = f"{Path(pdf_name).stem}_methodology_summary.txt"
            summary_path = self.summaries_dir / summary_filename
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"METHODOLOGY SUMMARY FOR: {pdf_name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(summary)
            
            print(f"💾 Individual summary saved to: {summary_path}")
            
            return summary
            
        except Exception as e:
            print(f"❌ Chat Completions method also failed: {e}")
            return None
    
    def generate_methodology_summary(self, pdf_path):
        """
        Generate methodology summary for a single PDF using existing pdf_direct_upload.py methods.
        
        Args:
            pdf_path (Path): Path to the PDF file
        
        Returns:
            str: Methodology summary or None if failed
        """
        try:
            # Step 1: Upload PDF to OpenAI
            file_id = self.upload_pdf_to_openai(pdf_path)
            if not file_id:
                return None
            
            # Step 2: Try Assistants API first (same as pdf_direct_upload.py)
            summary = self.generate_methodology_summary_with_assistants(file_id, pdf_path.name)
            
            if summary:
                return summary
            
            # Step 3: Fallback to Chat Completions if Assistants API fails
            print("🔄 Assistants API failed, trying Chat Completions...")
            summary = self.generate_methodology_summary_with_chat(file_id, pdf_path.name)
            
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
            
            # Generate methodology summary using existing methods
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
                print("⏳ Waiting 3 seconds before next PDF...")
                time.sleep(3)
        
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
        print("🚀 Starting Batch Direct Upload Processing")
        print("=" * 60)
        print("Using existing pdf_direct_upload.py methods")
        
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
        processor = BatchDirectUploadProcessor()
        processor.run_batch_processing()
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        print(f"💡 Make sure you have:")
        print(f"   1. Valid OpenAI API key")
        print(f"   2. Proper Google Sheets configuration")
        print(f"   3. PDF files in papers_pdf_id/ directory")


if __name__ == "__main__":
    main()
