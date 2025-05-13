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


def get_list_files(subset="excluded"):
    """Fetch list of files from spreadsheet based on subset criteria.

    Args:
        subset: One of "excluded", "included", or "all" to filter files

    Returns:
        Set of filenames matching the subset criteria

    Raises:
        ValueError: If subset is not one of the allowed values
    """
    if subset not in ("excluded", "included", "all"):
        raise ValueError("subset must be one of: 'excluded', 'included', 'all'")
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

        # Extract filenames based on subset criteria
        files = set()
        for row in values[1:]:  # Skip header row
            # Skip rows that don't have a filename
            if len(row) <= file_col_idx or not row[file_col_idx]:
                continue

            # Extract filename from HYPERLINK formula if present
            file_name = (
                row[file_col_idx].split('"')[-2] if row[file_col_idx].startswith("=HYPERLINK") else row[file_col_idx]
            )

            # Check if we should include this file based on subset
            include_file = False
            if subset == "all":
                include_file = True
            elif len(row) > exclude_col_idx:
                is_excluded = row[exclude_col_idx].upper() == "TRUE"
                include_file = (subset == "excluded" and is_excluded) or (subset == "included" and not is_excluded)

            if include_file:
                files.add(file_name)
                # Also add the expected converted filename if it exists
                if expected_file_col_idx != -1 and len(row) > expected_file_col_idx and row[expected_file_col_idx]:
                    files.add(row[expected_file_col_idx])

        print(f"Found {len(files)} files in subset '{subset}'.")
        return files

    except Exception as e:
        print(f"Warning: Could not fetch file data from spreadsheet: {e}")
        return set()
