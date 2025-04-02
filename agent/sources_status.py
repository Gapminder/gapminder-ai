import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
from config import FOLDER_ID, SPREADSHEET_ID
from common import get_converted_filename

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


def check_conversion_status():
    """Check the conversion status of all files in the drive folder."""
    drive_service, sheets_service = get_google_services()

    # Get list of files from drive
    print("Listing files in folder...")
    files = list_files_in_folder(drive_service, FOLDER_ID)

    # Prepare data for spreadsheet
    data = []
    for file in files:
        if file["mimeType"] == "application/vnd.google-apps.folder":
            continue

        converted_filename = get_converted_filename(file["name"], file["mimeType"])
        if converted_filename:
            converted_path = os.path.join("sources", converted_filename)
            is_converted = os.path.exists(converted_path)
        else:
            is_converted = False

        data.append(
            {
                "File Name": file["name"],
                "File ID": file["id"],
                "MIME Type": file["mimeType"],
                "Expected Converted File": converted_filename or "N/A",
                "Conversion Status": "Converted" if is_converted else "Not Converted",
                "Conversion Supported": "Yes" if converted_filename else "No",
            }
        )

    # Convert to DataFrame for easier handling
    df = pd.DataFrame(data)

    # Prepare the values for the sheet
    values = [df.columns.tolist()] + df.values.tolist()

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


if __name__ == "__main__":
    check_conversion_status()
