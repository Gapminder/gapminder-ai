import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import FOLDER_ID, SPREADSHEET_ID
from common import SOURCES_DIR, get_converted_filename, clean_filename_preserve_spaces
from token_counting import get_token_encoder, count_tokens_in_file, count_tokens_in_directory
from lib.fileops import ensure_directories, move_to_excluded, remove_empty_dirs

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets"]

# Google Drive file URL format
DRIVE_FILE_URL = "https://drive.google.com/file/d/{file_id}/view"

# Column definitions
COLUMNS = [
    "File",
    "Contentful ID",
    "MIME Type",
    "Expected Converted File",
    "Conversion Status",
    "Successfully Converted",
    "Conversion Supported",
    "Token Count",
    "Exclude",  # New column that will be preserved
]

# Columns that should be preserved when updating (0-based index)
PRESERVED_COLUMNS = [8]  # Preserve the "Exclude" column


def get_google_services():
    """Get Google Drive and Sheets API services using service account."""
    try:
        credentials = service_account.Credentials.from_service_account_file("service-account.json", scopes=SCOPES)
        drive_service = build("drive", "v3", credentials=credentials)
        sheets_service = build("sheets", "v4", credentials=credentials)
        return drive_service, sheets_service
    except Exception as e:
        print(f"Error creating service account credentials: {e}")
        raise


def list_files_in_folder(service, folder_id):
    """List all files in the specified Google Drive folder."""
    results = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)",
            pageSize=1000,
        )
        .execute()
    )

    return results.get("files", [])


def load_mappings():
    """Load both original and reverse mappings from mapping.json."""
    from collections import defaultdict

    mapping_path = os.path.join(os.path.dirname(__file__), "igno_index", "mapping.json")
    with open(mapping_path, "r") as f:
        mapping = json.load(f)

    # Create reverse mapping: filename_description -> list_of_ids
    reverse_mapping = defaultdict(list)
    for contentful_id, filename_description in mapping.items():
        reverse_mapping[filename_description].append(contentful_id)

    return mapping, reverse_mapping


def get_existing_sheet_data(sheets_service):
    """Get existing data from the sheet to preserve certain columns."""
    result = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:I")  # Include all columns up to Exclude
        .execute()
    )

    return result.get("values", [])


def check_file_conversion(filename, mime_type, encoding=None):
    """Check if a file has been properly converted.

    Returns:
        tuple: (is_converted, details, token_count)
            - is_converted: bool indicating if file is converted
            - details: str with additional information about conversion status
            - token_count: int number of tokens in converted file(s)
    """
    # Clean the filename to be safe for filesystem while preserving spaces and hyphens
    safe_filename = clean_filename_preserve_spaces(filename)
    converted_filename = get_converted_filename(safe_filename, mime_type)
    if not converted_filename:
        return False, "Conversion not supported", 0

    # Get paths for both regular sources and excluded sources
    converted_path = os.path.join(SOURCES_DIR, converted_filename)
    excluded_path = os.path.join(SOURCES_DIR, "excluded", converted_filename)

    # Debug print original and expected names
    # print(f"\nOriginal filename: {filename}")
    # print(f"Safe filename: {safe_filename}")
    # print(f"Expected converted name: {converted_filename}")

    # Handle Excel/Sheets conversion to CSVs
    if converted_filename.endswith("_sheets"):
        # For sheets, we need the exact directory name
        # Check both regular and excluded paths
        if os.path.exists(converted_path):
            csv_files = [f for f in os.listdir(converted_path) if f.endswith(".csv")]
            if csv_files:
                token_count = count_tokens_in_directory(converted_path, encoding)
                return True, f"Converted to {len(csv_files)} CSV files", token_count
        elif os.path.exists(excluded_path):
            csv_files = [f for f in os.listdir(excluded_path) if f.endswith(".csv")]
            if csv_files:
                token_count = count_tokens_in_directory(excluded_path, encoding)
                return True, f"Converted to {len(csv_files)} CSV files (excluded)", token_count

        return False, "No CSV files found in sheets directory", 0

    # Check for file in regular sources
    if os.path.exists(converted_path) and os.path.getsize(converted_path) > 0:
        token_count = count_tokens_in_file(converted_path, encoding)
        return True, "Successfully converted", token_count

    # Check for file in excluded sources
    if os.path.exists(excluded_path) and os.path.getsize(excluded_path) > 0:
        token_count = count_tokens_in_file(excluded_path, encoding)
        return True, "Successfully converted (excluded)", token_count

    return False, "Converted file not found or empty", 0


def check_conversion_status():
    """Check the conversion status of all files in the drive folder."""
    drive_service, sheets_service = get_google_services()
    id_to_filename, filename_to_id = load_mappings()
    found_ids = set()

    # Get list of files from drive
    print("Listing files in folder...")
    files = list_files_in_folder(drive_service, FOLDER_ID)

    # Get existing sheet data to preserve certain columns
    existing_data = get_existing_sheet_data(sheets_service)
    existing_exclude = {}
    if len(existing_data) > 1:  # If we have data beyond headers
        file_col_idx = 0  # "File" column is first
        exclude_col_idx = PRESERVED_COLUMNS[0]
        for row in existing_data[1:]:  # Skip header row
            if len(row) > exclude_col_idx:
                # Extract filename from HYPERLINK formula
                file_name = (
                    row[file_col_idx].split('"')[-2]
                    if row[file_col_idx].startswith("=HYPERLINK")
                    else row[file_col_idx]
                )
                exclude_val = row[exclude_col_idx] if len(row) > exclude_col_idx else ""
                existing_exclude[file_name] = exclude_val

    # Initialize token encoder once to reuse
    encoding = get_token_encoder()

    # Prepare data for spreadsheet
    data = []
    total_tokens = 0
    for file in files:
        if file["mimeType"] == "application/vnd.google-apps.folder":
            continue

        is_converted, details, tokens = check_file_conversion(file["name"], file["mimeType"], encoding)
        safe_filename = file["name"].replace("/", "_")
        converted_filename = get_converted_filename(safe_filename, file["mimeType"])

        if is_converted:
            total_tokens += tokens

        # Create hyperlink formula for the file name
        file_url = DRIVE_FILE_URL.format(file_id=file["id"])
        # Escape any quotes in the filename
        display_name = file["name"].replace('"', '""')
        file_hyperlink = f'=HYPERLINK("{file_url}", "{display_name}")'

        # Get base filename without extension for mapping lookup
        contentful_ids = filename_to_id.get(file["name"], ["Not Published"])

        # Join multiple IDs with commas if present
        contentful_id = ", ".join(sorted(contentful_ids)) if isinstance(contentful_ids, list) else contentful_ids

        # Track found IDs
        if contentful_ids != ["Not Published"]:
            found_ids.update(contentful_ids)

        # Get existing exclude value or empty string if not found
        exclude_value = existing_exclude.get(file["name"], "")

        # If file was found in excluded directory, mark it as excluded
        if "(excluded)" in details and not exclude_value:
            exclude_value = "TRUE"

        row_data = [
            file_hyperlink,  # File with hyperlink
            contentful_id,  # Contentful ID
            file["mimeType"],  # MIME Type
            converted_filename or "N/A",  # Expected converted filename
            details,  # Conversion details
            "YES" if is_converted else "NO",  # Conversion successful
            "YES" if converted_filename else "NO",  # Conversion supported
            str(tokens) if is_converted else "0",  # Token count
            exclude_value,  # Preserve existing exclude value
        ]

        data.append(row_data)

    # Sort by filename
    data.sort(key=lambda row: row[0].lower())  # Sort by filename (first column)

    # Insert header
    data.insert(0, COLUMNS)

    # Update the spreadsheet
    print("Updating spreadsheet...")
    sheets_service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:Z").execute()

    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body={"values": data},
    ).execute()

    # Process files that are in the excluded directory
    process_excluded_files()

    print(f"Updated conversion status for {len(data) - 1} files.")
    print(f"Total tokens counted: {total_tokens:,}")


def process_excluded_files():
    """Make sure all files in the excluded spreadsheet column are actually in the excluded directory."""
    # Ensure directories exist
    ensure_directories()

    # Get sheets service
    credentials = service_account.Credentials.from_service_account_file(
        "service-account.json", scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    sheets_service = build("sheets", "v4", credentials=credentials)

    # Get existing sheet data
    result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:I").execute()

    values = result.get("values", [])
    if not values:
        return

    # Find indices
    headers = values[0]
    file_col_idx = headers.index("File") if "File" in headers else 0
    expected_file_col_idx = headers.index("Expected Converted File") if "Expected Converted File" in headers else -1
    exclude_col_idx = headers.index("Exclude") if "Exclude" in headers else -1

    if exclude_col_idx == -1:
        return

    files_to_exclude = []
    for row in values[1:]:  # Skip header
        if len(row) > exclude_col_idx and row[exclude_col_idx].upper() == "TRUE":
            # Get file name
            file_name = (
                row[file_col_idx].split('"')[-2] if row[file_col_idx].startswith("=HYPERLINK") else row[file_col_idx]
            )
            files_to_exclude.append(file_name)

            # Also add expected converted file if available
            if expected_file_col_idx != -1 and len(row) > expected_file_col_idx and row[expected_file_col_idx]:
                files_to_exclude.append(row[expected_file_col_idx])

    # Process sources directory
    excluded_count = 0
    sources_path = os.path.join(os.path.dirname(__file__), SOURCES_DIR)
    for root, _, files in os.walk(sources_path):
        # Skip the excluded directory
        if "excluded" in root.split(os.path.sep):
            continue

        for file_name in files:
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, sources_path)

            # Check if this file should be excluded
            if any(exclude_name in rel_path or exclude_name == file_name for exclude_name in files_to_exclude):
                if move_to_excluded(file_path, preserve_structure=True):
                    excluded_count += 1

    if excluded_count > 0:
        print(f"Moved {excluded_count} additional files to excluded directory")
        # Clean up empty directories
        removed_dirs = remove_empty_dirs()
        if removed_dirs > 0:
            print(f"Removed {removed_dirs} empty directories")


if __name__ == "__main__":
    check_conversion_status()
