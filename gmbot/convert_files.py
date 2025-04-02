import os
from html2text import HTML2Text
import pandas as pd
import re


def convert_html_to_markdown(html_file):
    """Convert HTML file to Markdown."""
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
    markdown_content = re.sub(
        r"\n{3,}", "\n\n", markdown_content
    )  # Remove excessive newlines
    markdown_content = re.sub(
        r"#+\s*$", "", markdown_content
    )  # Remove trailing headers

    # Save as markdown
    md_file = os.path.splitext(html_file)[0] + ".md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Converted {html_file} to {md_file}")
    return md_file


def convert_excel_to_csv(excel_file):
    """Convert Excel file to CSV."""
    # Read all sheets
    excel_data = pd.read_excel(excel_file, sheet_name=None)

    # Create a directory for the sheets
    base_name = os.path.splitext(excel_file)[0]
    sheets_dir = base_name + "_sheets"
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
    # Note: This is a placeholder. You'll need to implement PDF to text conversion
    # using a library like PyPDF2 or pdfplumber
    print(f"PDF to text conversion not implemented yet for {pdf_file}")
    return None


def main():
    downloads_dir = "downloads"

    if not os.path.exists(downloads_dir):
        print(f"Downloads directory '{downloads_dir}' not found!")
        return

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
            else:
                print(f"Skipping {filename} - no conversion needed")
        except Exception as e:
            print(f"Error converting {filename}: {e}")


if __name__ == "__main__":
    main()
