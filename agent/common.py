import os
import re

# Directory constants
SOURCES_DIR = "sources"
DOWNLOADS_DIR = "downloads"

# Google Workspace MIME types
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME_TYPE = "application/vnd.google-apps.presentation"
GOOGLE_DRAWING_MIME_TYPE = "application/vnd.google-apps.drawing"

GOOGLE_WORKSPACE_MIME_TYPES = [
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_SHEET_MIME_TYPE,
    GOOGLE_SLIDES_MIME_TYPE,
    GOOGLE_DRAWING_MIME_TYPE,
]

# Export MIME types
EXPORT_MIME_TYPES = {
    GOOGLE_DOC_MIME_TYPE: "text/html",  # Will be converted to markdown
    GOOGLE_SHEET_MIME_TYPE: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Excel
    GOOGLE_SLIDES_MIME_TYPE: "application/pdf",
    GOOGLE_DRAWING_MIME_TYPE: "image/png",
}

# File extension mappings
SUPPORTED_EXTENSIONS = {
    ".html": ".md",
    ".xlsx": "_sheets",
    ".pdf": ".txt",
    ".docx": ".txt",
}

UNSUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]


def ensure_directories():
    """Ensure the required directories exist."""
    os.makedirs(SOURCES_DIR, exist_ok=True)
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def clean_filename(filename):
    """Clean a filename to be safe for filesystem."""
    return re.sub(r"[^\w\-_.]", "_", filename)


def clean_filename_preserve_spaces(filename):
    """Clean a filename to be safe for filesystem while preserving spaces and hyphens.
    Only replaces slashes with underscores."""
    return filename.replace("/", "_")


def get_source_path(filename, extension=None):
    """Get the path in the sources directory for a file."""
    base_name = os.path.splitext(os.path.basename(filename))[0]
    if extension is None:
        extension = os.path.splitext(filename)[1]
    return os.path.join(SOURCES_DIR, f"{base_name}{extension}")


def get_export_mime_type(mime_type):
    """Get the export MIME type for a Google Workspace file."""
    return EXPORT_MIME_TYPES.get(mime_type)


def get_intermediate_filename(original_filename, mime_type):
    """Get the filename for the intermediate format (before conversion)."""
    base_name = os.path.splitext(original_filename)[0]

    if mime_type == GOOGLE_DOC_MIME_TYPE:
        return f"{base_name}.html"
    elif mime_type == GOOGLE_SHEET_MIME_TYPE:
        return f"{base_name}.xlsx"
    elif mime_type == GOOGLE_SLIDES_MIME_TYPE:
        return f"{base_name}.pdf"
    elif mime_type == GOOGLE_DRAWING_MIME_TYPE:
        return f"{base_name}.png"
    else:
        # For non-Google Workspace files, keep original extension
        return original_filename


def get_converted_filename(original_filename, mime_type):
    """Get the expected final converted filename based on the original file and mime type."""
    base_name = os.path.splitext(original_filename)[0]

    if mime_type == GOOGLE_DOC_MIME_TYPE:
        return f"{base_name}.md"  # HTML files are converted to markdown
    elif mime_type == GOOGLE_SHEET_MIME_TYPE:
        return f"{base_name}_sheets"  # Excel files are converted to directory of CSVs
    elif mime_type == GOOGLE_SLIDES_MIME_TYPE:
        return f"{base_name}.txt"  # PDFs are converted to text
    elif mime_type == GOOGLE_DRAWING_MIME_TYPE:
        return None  # Images are not yet supported for conversion
    else:
        # For regular files, check extension
        ext = os.path.splitext(original_filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return f"{base_name}{SUPPORTED_EXTENSIONS[ext]}"
        elif ext in UNSUPPORTED_EXTENSIONS:
            return None  # Images are not yet supported
        else:
            return None


def is_conversion_supported(mime_type, filename):
    """Check if conversion is supported for this file type."""
    return get_converted_filename(filename, mime_type) is not None


def clean_text_content(text):
    """Clean up text content by removing excessive newlines."""
    return re.sub(r"\n{3,}", "\n\n", text)  # Remove excessive newlines
