from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SPREADSHEET_ID


def get_spreadsheet_service():
    """Get Google Sheets API service using service account."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            "service-account.json", scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sheets_service = build("sheets", "v4", credentials=credentials)
        return sheets_service
    except Exception as e:
        print(f"Error creating service account credentials for sheets: {e}")
        raise


def get_excluded_files():
    """Fetch the list of files to exclude from the Google Sheets spreadsheet."""
    try:
        sheets_service = get_spreadsheet_service()

        # Get spreadsheet data
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:I")  # Include all columns up to Exclude
            .execute()
        )

        values = result.get("values", [])
        if not values:
            print("No data found in spreadsheet.")
            return set()

        # Find the indices of the File, Expected Converted File, and Exclude columns
        headers = values[0]
        file_col_idx = headers.index("File") if "File" in headers else 0
        expected_file_col_idx = headers.index("Expected Converted File") if "Expected Converted File" in headers else -1
        exclude_col_idx = headers.index("Exclude") if "Exclude" in headers else -1

        if exclude_col_idx == -1:
            print("Warning: 'Exclude' column not found in the spreadsheet.")
            return set()

        # Extract filenames where Exclude is TRUE
        excluded_files = set()
        for row in values[1:]:  # Skip header row
            if len(row) > exclude_col_idx and row[exclude_col_idx].upper() == "TRUE":
                # Extract filename from HYPERLINK formula
                file_name = (
                    row[file_col_idx].split('"')[-2]
                    if row[file_col_idx].startswith("=HYPERLINK")
                    else row[file_col_idx]
                )
                excluded_files.add(file_name)

                # Also add the expected converted filename if it exists
                if expected_file_col_idx != -1 and len(row) > expected_file_col_idx and row[expected_file_col_idx]:
                    excluded_files.add(row[expected_file_col_idx])

        print(f"Found {len(excluded_files)} files to exclude from processing.")
        return excluded_files

    except Exception as e:
        print(f"Warning: Could not fetch exclusion data from spreadsheet: {e}")
        return set()
