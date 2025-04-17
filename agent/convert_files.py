import os
import pandas as pd
import pypandoc
import pdfplumber
from docx import Document
from bs4 import BeautifulSoup
from common import (
    DOWNLOADS_DIR,
    UNSUPPORTED_EXTENSIONS,
    ensure_directories,
    clean_filename,
    get_source_path,
    clean_text_content,
    remove_markdown_header_ids,
)


def convert_html_to_markdown(html_file):
    """Convert HTML file to Markdown."""
    md_file = get_source_path(html_file, ".md")

    if os.path.exists(md_file):
        return md_file

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Preprocess HTML to remove all styles
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove all <style> tags
    for style in soup.find_all("style"):
        style.decompose()

    # Remove all style attributes from tags
    for tag in soup.find_all(True):
        if "style" in tag.attrs:
            del tag["style"]

    html_content = str(soup)

    # Use pandoc for conversion
    try:
        markdown_content = pypandoc.convert_text(
            html_content, "markdown+pipe_tables", format="html-native_spans-native_divs", extra_args=["--wrap=none"]
        )
    except OSError as e:
        print(f"Error converting {html_file} with pandoc: {e}")
        print("Ensure pandoc is installed and accessible in your system's PATH.")
        return None
    markdown_content = clean_text_content(markdown_content)
    markdown_content = remove_markdown_header_ids(markdown_content)
    markdown_content = markdown_content.rstrip("#")  # Remove trailing headers

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Converted {html_file} to {md_file}")
    return md_file


def convert_excel_to_csv(excel_file):
    """Convert Excel file to CSV."""
    os.path.splitext(os.path.basename(excel_file))[0]
    sheets_dir = get_source_path(excel_file, "_sheets")

    if os.path.exists(sheets_dir):
        return sheets_dir

    # Read all sheets
    excel_data = pd.read_excel(excel_file, sheet_name=None)
    os.makedirs(sheets_dir, exist_ok=True)

    # Convert each sheet to CSV
    for sheet_name, df in excel_data.items():
        safe_sheet_name = clean_filename(sheet_name)
        csv_file = os.path.join(sheets_dir, f"{safe_sheet_name}.csv")

        df.to_csv(csv_file, index=False)
        print(f"Converted sheet '{sheet_name}' to {csv_file}")

    return sheets_dir


def convert_pdf_to_text(pdf_file):
    """Convert PDF file to text."""
    txt_file = get_source_path(pdf_file, ".txt")

    if os.path.exists(txt_file):
        return txt_file

    try:
        with pdfplumber.open(pdf_file) as pdf:
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text() or "")

            text = "\n\n".join(text_content)
            text = clean_text_content(text)

            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"Converted {pdf_file} to {txt_file}")
            return txt_file
    except Exception as e:
        print(f"Error converting PDF {pdf_file}: {e}")
        return None


def convert_docx_to_text(docx_file):
    """Convert DOCX file to text."""
    txt_file = get_source_path(docx_file, ".txt")

    if os.path.exists(txt_file):
        return txt_file

    try:
        doc = Document(docx_file)
        text_content = []
        for paragraph in doc.paragraphs:
            text_content.append(paragraph.text)

        text = "\n\n".join(text_content)
        text = clean_text_content(text)

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Converted {docx_file} to {txt_file}")
        return txt_file
    except Exception as e:
        print(f"Error converting DOCX {docx_file}: {e}")
        return None


def main():
    if not os.path.exists(DOWNLOADS_DIR):
        print(f"Downloads directory '{DOWNLOADS_DIR}' not found!")
        return

    ensure_directories()

    for filename in os.listdir(DOWNLOADS_DIR):
        file_path = os.path.join(DOWNLOADS_DIR, filename)

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
            elif ext in UNSUPPORTED_EXTENSIONS:
                print(f"Skipping {filename} - image conversion not yet supported")
            else:
                print(f"Skipping {filename} with extension {ext} - no conversion implemented")
        except Exception as e:
            print(f"Error converting {filename}: {e}")


if __name__ == "__main__":
    main()
