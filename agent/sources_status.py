import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
from config import FOLDER_ID, SPREADSHEET_ID
from common import SOURCES_DIR, get_converted_filename, get_source_path
from token_counting import get_token_encoder, count_tokens_in_file, count_tokens_in_directory

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets"]


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


def check_file_conversion(filename, mime_type, encoding=None):
    """Check if a file has been properly converted.

    Returns:
        tuple: (is_converted, details, token_count)
            - is_converted: bool indicating if file is converted
            - details: str with additional information about conversion status
            - token_count: int number of tokens in converted file(s)
    """
    converted_filename = get_converted_filename(filename, mime_type)
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
    converted_path = get_source_path(filename, os.path.splitext(converted_filename)[1])

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

    # Get list of files from drive
    print("Listing files in folder...")
    files = list_files_in_folder(drive_service, FOLDER_ID)

    # Initialize token encoder once to reuse
    encoding = get_token_encoder()

    # Prepare data for spreadsheet
    data = []
    total_tokens = 0
    for file in files:
        if file["mimeType"] == "application/vnd.google-apps.folder":
            continue

        is_converted, details, tokens = check_file_conversion(file["name"], file["mimeType"], encoding)
        converted_filename = get_converted_filename(file["name"], file["mimeType"])

        if is_converted:
            total_tokens += tokens

        data.append(
            {
                "File Name": file["name"],
                "File ID": file["id"],
                "MIME Type": file["mimeType"],
                "Expected Converted File": converted_filename or "N/A",
                "Conversion Status": details,
                "Successfully Converted": "Yes" if is_converted else "No",
                "Conversion Supported": "Yes" if converted_filename else "No",
                "Token Count": f"{tokens:,}" if tokens > 0 else "0",
            }
        )

    # Convert to DataFrame for easier handling
    df = pd.DataFrame(data)

    # Add summary row
    summary_row = ["TOTAL", "", "", "", "", "", "", f"{total_tokens:,}"]

    # Prepare the values for the sheet
    values = [df.columns.tolist()] + df.values.tolist() + [summary_row]

    # Update the spreadsheet
    body = {"values": values}

    print("Updating spreadsheet...")
    result = (
        sheets_service.spreadsheets()
        .values()
        .update(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A1",  # Start from the first cell
            valueInputOption="RAW",
            body=body,
        )
        .execute()
    )

    print(f"Updated {result.get('updatedCells')} cells in the spreadsheet")
    print(f"Total tokens in converted files: {total_tokens:,}")


if __name__ == "__main__":
    check_conversion_status()
