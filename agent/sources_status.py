import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import FOLDER_ID, SPREADSHEET_ID
from common import SOURCES_DIR, get_converted_filename, get_source_path, clean_filename_preserve_spaces
from token_counting import get_token_encoder, count_tokens_in_file, count_tokens_in_directory

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

    # Handle Excel/Sheets conversion to CSVs
    if converted_filename.endswith("_sheets"):
        # For sheets, we need the exact directory name
        converted_path = os.path.join(SOURCES_DIR, converted_filename)
        if not os.path.exists(converted_path):
            return False, "Sheets directory not found", 0
        csv_files = [f for f in os.listdir(converted_path) if f.endswith(".csv")]
        if not csv_files:
            return False, "No CSV files found in sheets directory", 0

        # Count tokens in all CSV files
        token_count = count_tokens_in_directory(converted_path, encoding)
        return True, f"Converted to {len(csv_files)} CSV files", token_count

    # For regular files, use get_source_path to handle the extension
    converted_path = get_source_path(safe_filename, os.path.splitext(converted_filename)[1])

    # Handle regular file conversions
    if not os.path.exists(converted_path):
        return False, "Converted file not found", 0

    # Check if file is empty
    if os.path.getsize(converted_path) == 0:
        return False, "Converted file is empty", 0

    # Count tokens in the converted file
    token_count = count_tokens_in_file(converted_path, encoding)
    return True, "Successfully converted", token_count


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
        base_filename = os.path.splitext(file["name"])[0]
        contentful_ids = filename_to_id.get(base_filename, ["Not Published"])

        # Join multiple IDs with commas if present
        contentful_id = ", ".join(sorted(contentful_ids)) if isinstance(contentful_ids, list) else contentful_ids

        # Track found IDs
        if contentful_ids != ["Not Published"]:
            found_ids.update(contentful_ids)

        # Get existing exclude value or empty string if not found
        exclude_val = existing_exclude.get(file["name"], "")

        row_data = [
            file_hyperlink,
            contentful_id,
            file["mimeType"],
            converted_filename or "N/A",
            details,
            "Yes" if is_converted else "No",
            "Yes" if converted_filename else "No",
            tokens,
            exclude_val,  # Preserve existing value or empty string
        ]
        data.append(row_data)

    # Prepare the values for the sheet
    values = [COLUMNS] + data

    # Update the spreadsheet
    body = {"values": values}

    print("Updating spreadsheet...")
    result = (
        sheets_service.spreadsheets()
        .values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A1",  # Start from the first cell
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )

    print(f"Updated {result.get('updatedCells')} cells in the spreadsheet")
    print(f"Total tokens in converted files: {total_tokens:,}")

    # Report missing mapping entries
    all_ids = set(id_to_filename.keys())
    missing_ids = all_ids - found_ids
    if missing_ids:
        print("\nMissing files in Google Drive (from mapping.json):")
        for contentful_id in sorted(missing_ids, key=int):
            print(f"ID: {contentful_id} - File: {id_to_filename[contentful_id]}")
    else:
        print("\nAll mapping entries were found in Google Drive")


if __name__ == "__main__":
    check_conversion_status()
