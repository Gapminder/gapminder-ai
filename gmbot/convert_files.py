import os
from html2text import HTML2Text
import pandas as pd
import re
import pdfplumber
from docx import Document


def convert_html_to_markdown(html_file):
    """Convert HTML file to Markdown."""
    # Check if markdown file already exists
    sources_dir = "sources"
    os.makedirs(sources_dir, exist_ok=True)
    md_file = os.path.join(sources_dir, os.path.splitext(os.path.basename(html_file))[0] + ".md")

    if os.path.exists(md_file):
        # print(f"Skipping {html_file} - markdown file already exists: {md_file}")
        return md_file

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Use html2text for conversion
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines

    markdown_content = h.handle(html_content)

    # Clean up the markdown
    markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)  # Remove excessive newlines
    markdown_content = re.sub(r"#+\s*$", "", markdown_content)  # Remove trailing headers

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Converted {html_file} to {md_file}")
    return md_file


def convert_excel_to_csv(excel_file):
    """Convert Excel file to CSV."""
    # Check if sheets directory already exists
    sources_dir = "sources"
    os.makedirs(sources_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(excel_file))[0]
    sheets_dir = os.path.join(sources_dir, base_name + "_sheets")

    if os.path.exists(sheets_dir):
        # print(f"Skipping {excel_file} - sheets directory already exists: {sheets_dir}")
        return sheets_dir

    # Read all sheets
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    os.makedirs(sheets_dir, exist_ok=True)

    # Convert each sheet to CSV
    for sheet_name, df in excel_data.items():
        # Clean sheet name for filename
        safe_sheet_name = re.sub(r"[^\w\-_.]", "_", sheet_name)
        csv_file = os.path.join(sheets_dir, f"{safe_sheet_name}.csv")

        df.to_csv(csv_file, index=False)
        print(f"Converted sheet '{sheet_name}' to {csv_file}")

    return sheets_dir


def convert_pdf_to_text(pdf_file):
    """Convert PDF file to text."""
    sources_dir = "sources"
    os.makedirs(sources_dir, exist_ok=True)
    txt_file = os.path.join(sources_dir, os.path.splitext(os.path.basename(pdf_file))[0] + ".txt")

    if os.path.exists(txt_file):
        # print(f"Skipping {pdf_file} - text file already exists: {txt_file}")
        return txt_file

    try:
        with pdfplumber.open(pdf_file) as pdf:
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text() or "")

            text = "\n\n".join(text_content)

            # Clean up the text
            text = re.sub(r"\n{3,}", "\n\n", text)  # Remove excessive newlines

            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"Converted {pdf_file} to {txt_file}")
            return txt_file
    except Exception as e:
        print(f"Error converting PDF {pdf_file}: {e}")
        return None


def convert_docx_to_text(docx_file):
    """Convert DOCX file to text."""
    sources_dir = "sources"
    os.makedirs(sources_dir, exist_ok=True)
    txt_file = os.path.join(sources_dir, os.path.splitext(os.path.basename(docx_file))[0] + ".txt")

    if os.path.exists(txt_file):
        # print(f"Skipping {docx_file} - text file already exists: {txt_file}")
        return txt_file

    try:
        doc = Document(docx_file)
        text_content = []
        for paragraph in doc.paragraphs:
            text_content.append(paragraph.text)

        text = "\n\n".join(text_content)

        # Clean up the text
        text = re.sub(r"\n{3,}", "\n\n", text)  # Remove excessive newlines

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Converted {docx_file} to {txt_file}")
        return txt_file
    except Exception as e:
        print(f"Error converting DOCX {docx_file}: {e}")
        return None


def convert_image_to_text(image_file):
    """Convert image file to text using OCR."""
    # Note: This is a placeholder. You'll need to implement OCR using a library
    # like pytesseract or cloud OCR services
    print(f"Image to text conversion not implemented yet for {image_file}")
    return None


def main():
    downloads_dir = "downloads"

    if not os.path.exists(downloads_dir):
        print(f"Downloads directory '{downloads_dir}' not found!")
        return

    # Create sources directory
    sources_dir = "sources"
    os.makedirs(sources_dir, exist_ok=True)

    for filename in os.listdir(downloads_dir):
        file_path = os.path.join(downloads_dir, filename)

        if not os.path.isfile(file_path):
            continue

        ext = os.path.splitext(filename)[1].lower()

        try:
            if ext == ".html":
                convert_html_to_markdown(file_path)
            elif ext == ".xlsx":
                convert_excel_to_csv(file_path)
            elif ext == ".pdf":
                convert_pdf_to_text(file_path)
            elif ext == ".docx":
                convert_docx_to_text(file_path)
            elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
                convert_image_to_text(file_path)
            else:
                print(f"Skipping {filename} with extension {ext} - " "no conversion implemented")
                pass
        except Exception as e:
            print(f"Error converting {filename}: {e}")


if __name__ == "__main__":
    main()
