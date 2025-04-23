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
from lib.spreadsheet import get_excluded_files
from lib.fileops import ensure_directories as ensure_excluded_dir, move_to_excluded, remove_empty_dirs, EXCLUDED_DIR

# Get excluded files once at module level
EXCLUDED_FILES = set()


def update_excluded_files():
    """Update the global EXCLUDED_FILES set."""
    global EXCLUDED_FILES
    EXCLUDED_FILES = get_excluded_files()
    return EXCLUDED_FILES


def should_exclude_file(file_path):
    """Check if a file should be excluded based on the exclusion list.

    Args:
        file_path (str): The file path to check

    Returns:
        bool: True if the file should be excluded, False otherwise
    """
    file_name = os.path.basename(file_path)
    # Check if this file should be excluded
    return any(exclude_name in file_name for exclude_name in EXCLUDED_FILES)


def get_destination_path(file_path, extension):
    """Get the appropriate destination path based on whether the file is excluded or not.

    Args:
        file_path (str): The original file path
        extension (str): The extension to use for the converted file

    Returns:
        str: Path where the converted file should be saved
    """
    os.path.basename(file_path)

    # Check if this file should be excluded
    is_excluded = should_exclude_file(file_path)

    if is_excluded:
        # Save to sources/excluded directory
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        if extension.startswith("_"):  # For directories like "_sheets"
            return os.path.join(str(EXCLUDED_DIR), f"{base_name}{extension}")
        else:
            return os.path.join(str(EXCLUDED_DIR), f"{base_name}{extension}")
    else:
        # Use the regular get_source_path function for non-excluded files
        return get_source_path(file_path, extension)


def convert_html_to_markdown(html_file):
    """Convert HTML file to Markdown."""
    md_file = get_destination_path(html_file, ".md")

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

    # Ensure the directory exists
    os.makedirs(os.path.dirname(md_file), exist_ok=True)

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Converted {html_file} to {md_file}")
    return md_file


def convert_excel_to_csv(excel_file):
    """Convert Excel file to CSV."""
    sheets_dir = get_destination_path(excel_file, "_sheets")

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
    txt_file = get_destination_path(pdf_file, ".txt")

    if os.path.exists(txt_file):
        return txt_file

    try:
        with pdfplumber.open(pdf_file) as pdf:
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text() or "")

            text = "\n\n".join(text_content)
            text = clean_text_content(text)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(txt_file), exist_ok=True)

            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"Converted {pdf_file} to {txt_file}")
            return txt_file
    except Exception as e:
        print(f"Error converting PDF {pdf_file}: {e}")
        return None


def convert_docx_to_text(docx_file):
    """Convert DOCX file to text."""
    txt_file = get_destination_path(docx_file, ".txt")

    if os.path.exists(txt_file):
        return txt_file

    try:
        doc = Document(docx_file)
        text_content = []
        for paragraph in doc.paragraphs:
            text_content.append(paragraph.text)

        text = "\n\n".join(text_content)
        text = clean_text_content(text)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(txt_file), exist_ok=True)

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Converted {docx_file} to {txt_file}")
        return txt_file
    except Exception as e:
        print(f"Error converting DOCX {docx_file}: {e}")
        return None


def check_and_exclude_files():
    """Check converted files against excluded list and move them if needed."""
    # Ensure excluded directory exists
    ensure_excluded_dir()

    # Get all files in the sources directory
    sources_dir = os.path.join(os.path.dirname(__file__), "sources")
    excluded_count = 0

    for root, _, files in os.walk(sources_dir):
        # Skip the excluded directory
        if "excluded" in root.split(os.path.sep):
            continue

        for file in files:
            file_path = os.path.join(root, file)

            # Check if this file should be excluded
            rel_path = os.path.relpath(file_path, sources_dir)
            if any(exclude_name in rel_path or exclude_name == file for exclude_name in EXCLUDED_FILES):
                if move_to_excluded(file_path):
                    excluded_count += 1

    if excluded_count > 0:
        print(f"Moved {excluded_count} files to excluded directory")
        # Remove any empty directories left
        removed_dirs = remove_empty_dirs()
        if removed_dirs > 0:
            print(f"Removed {removed_dirs} empty directories")


def main():
    if not os.path.exists(DOWNLOADS_DIR):
        print(f"Downloads directory '{DOWNLOADS_DIR}' not found!")
        return

    # Ensure directories exist
    ensure_directories()
    ensure_excluded_dir()

    # Update excluded files list
    update_excluded_files()

    skipped_count = 0
    excluded_count = 0

    for filename in os.listdir(DOWNLOADS_DIR):
        file_path = os.path.join(DOWNLOADS_DIR, filename)

        if not os.path.isfile(file_path):
            continue

        ext = os.path.splitext(filename)[1].lower()

        # Check if file is in the excluded list
        if should_exclude_file(file_path):
            excluded_count += 1
            # Get converted path for the excluded file
            if ext == ".html":
                dest_path = get_destination_path(file_path, ".md")
            elif ext == ".xlsx":
                dest_path = get_destination_path(file_path, "_sheets")
            elif ext in [".pdf", ".docx"]:
                dest_path = get_destination_path(file_path, ".txt")
            else:
                dest_path = get_destination_path(file_path, ext)

            # Check if destination file exists
            if os.path.exists(dest_path):
                print(f"Skipping excluded file {filename} - already converted to {os.path.basename(dest_path)}")
                skipped_count += 1
                continue

            print(f"Converting excluded file {filename} directly to excluded directory")

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

    # Double-check for any files that might have been missed
    check_and_exclude_files()

    if skipped_count > 0:
        print(f"Skipped converting {skipped_count} files that were already converted and excluded")
    if excluded_count > 0:
        print(f"Processed {excluded_count} files from the excluded list")


if __name__ == "__main__":
    main()
