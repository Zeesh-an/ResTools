#!/usr/bin/env python3
"""
PDF Direct Upload Summarizer using OpenAI

This script uploads a PDF directly to OpenAI and uses their file analysis
capabilities to summarize the methodology.
"""

import os
import sys
import time
from pathlib import Path
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # python-dotenv not installed, continue without it


def main():
    """Main function to run the PDF direct upload summarizer."""
    print("🚀 PDF Direct Upload Methodology Summarizer")
    print("=" * 50)
    
    # Initialize OpenAI client
    try:
        client = OpenAI()
    except Exception as e:
        print(f"❌ Error initializing OpenAI client: {e}")
        print("💡 Make sure you have set your OPENAI_API_KEY environment variable")
        return
    
    # Check for PDF files
    pdf_dir = Path("papers_pdf_id")
    if not pdf_dir.exists():
        print(f"❌ Directory {pdf_dir} does not exist")
        return
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in papers_pdf_id directory")
        return
    
    print(f"\n📚 Available PDF files ({len(pdf_files)}):")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf_file.name}")
    
    # Let user select a PDF
    try:
        choice = input(f"\n📝 Select a PDF file (1-{len(pdf_files)}) or press Enter for first file: ").strip()
        if not choice:
            choice = "1"
        
        pdf_index = int(choice) - 1
        if pdf_index < 0 or pdf_index >= len(pdf_files):
            print("❌ Invalid selection")
            return
        
        selected_pdf = pdf_files[pdf_index]
        print(f"\n🎯 Selected: {selected_pdf.name}")
        
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
        return
    
    # Upload PDF to OpenAI
    try:
        print(f"📤 Uploading PDF: {selected_pdf.name}")
        with open(selected_pdf, "rb") as file:
            uploaded_file = client.files.create(
                file=file,
                purpose="assistants"
            )
        print(f"✅ PDF uploaded successfully. File ID: {uploaded_file.id}")
        
    except Exception as e:
        print(f"❌ Error uploading PDF: {e}")
        return
    
    # Method 1: Try using Assistants API with file upload
    print(f"\n🤖 Method 1: Using Assistants API...")
    try:
        # Create an assistant
        assistant = client.beta.assistants.create(
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

            Please focus specifically on the methodology section and make it clear and easy to understand.""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "file_search"}]
        )
        
        # Create a thread
        thread = client.beta.threads.create()
        
        # Add the file to the thread
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Please analyze the attached PDF file and provide a comprehensive methodology summary in the specified format.",
            attachments=[
                {
                    "file_id": uploaded_file.id,
                    "tools": [{"type": "file_search"}]
                }
            ]
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        print("⏳ Analyzing PDF with Assistants API...")
        
        # Wait for completion
        while run.status in ['queued', 'in_progress', 'requires_action']:
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            print(f"   Status: {run.status}")
        
        if run.status == 'completed':
            # Get the response
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            
            # Display and save the summary
            print(f"\n📋 METHODOLOGY SUMMARY FOR: {selected_pdf.name}")
            print("=" * 60)
            print(response)
            print("=" * 60)
            
            # Save to file
            output_dir = Path("summaries")
            output_dir.mkdir(exist_ok=True)
            
            summary_filename = f"{selected_pdf.stem}_methodology_summary_direct.txt"
            output_path = output_dir / summary_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"METHODOLOGY SUMMARY FOR: {selected_pdf.name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(response)
            
            print(f"\n💾 Summary saved to: {output_path}")
            print(f"✅ Analysis completed successfully using Assistants API!")
            
        else:
            print(f"❌ Analysis failed with status: {run.status}")
            print("🔄 Trying alternative method...")
            raise Exception("Assistants API failed")
            
    except Exception as e:
        print(f"⚠️  Assistants API method failed: {e}")
        print(f"\n🤖 Method 2: Using Chat Completions with file reference...")
        
        # Method 2: Try using chat completions with file reference
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert research analyst who specializes in understanding and summarizing research methodologies from academic papers."
                    },
                    {
                        "role": "user",
                        "content": f"""I have uploaded a PDF file with ID: {uploaded_file.id}

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

Please focus specifically on the methodology section and make it clear and easy to understand like whats the approach, what are the key steps and architectural framework.

Note: The file ID is {uploaded_file.id} - please reference this file in your analysis."""
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            # Display and save the summary
            print(f"\n📋 METHODOLOGY SUMMARY FOR: {selected_pdf.name}")
            print("=" * 60)
            print(summary)
            print("=" * 60)
            
            # Save to file
            output_dir = Path("summaries")
            output_dir.mkdir(exist_ok=True)
            
            summary_filename = f"{selected_pdf.stem}_methodology_summary_direct.txt"
            output_path = output_dir / summary_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"METHODOLOGY SUMMARY FOR: {selected_pdf.name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(summary)
            
            print(f"\n💾 Summary saved to: {output_path}")
            print(f"✅ Analysis completed successfully using Chat Completions!")
            
        except Exception as e2:
            print(f"❌ Chat Completions method also failed: {e2}")
            print(f"\n💡 Alternative approaches:")
            print(f"   1. Use the text extraction method: python pdf_text_summarizer.py")
            print(f"   2. Check if your OpenAI plan supports file uploads")
            print(f"   3. Try with a smaller PDF file")
            print(f"\n📄 File uploaded with ID: {uploaded_file.id}")
            print(f"   You can use this file ID with other OpenAI tools")


if __name__ == "__main__":
    main()
