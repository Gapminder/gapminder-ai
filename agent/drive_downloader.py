import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from config import FOLDER_ID
from common import GOOGLE_WORKSPACE_MIME_TYPES, get_export_mime_type, get_intermediate_filename

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_google_drive_service():
    """Get Google Drive API service using service account."""
    try:
        credentials = service_account.Credentials.from_service_account_file("service-account.json", scopes=SCOPES)
        return build("drive", "v3", credentials=credentials)
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

    items = results.get("files", [])

    if not items:
        print("No files found.")
        return

    print("Files:")
    for item in items:
        print(f"{item['name']} ({item['id']})")
    return items


def download_file(service, file_id, filename, mime_type):
    """Download a file from Google Drive."""
    try:
        # Handle Google Workspace files
        if mime_type in GOOGLE_WORKSPACE_MIME_TYPES:
            export_mime_type = get_export_mime_type(mime_type)
            filename = get_intermediate_filename(filename, mime_type)
            request = service.files().export(fileId=file_id, mimeType=export_mime_type)
        else:
            # Handle regular files
            request = service.files().get_media(fileId=file_id)

        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%")

        # Save the file
        with open(filename, "wb") as f:
            f.write(file.getvalue())
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    # Get the Google Drive service
    service = get_google_drive_service()

    # List all files in the folder
    print("Listing files in folder...")
    files = list_files_in_folder(service, FOLDER_ID)

    if files:
        # Create a downloads directory if it doesn't exist
        if not os.path.exists("downloads"):
            os.makedirs("downloads")

        # Download each file
        print("\nDownloading files...")
        for file in files:
            if file["mimeType"] != "application/vnd.google-apps.folder":  # Skip folders
                filename = os.path.join("downloads", file["name"])

                # Check if file already exists
                if os.path.exists(filename):
                    print(f"\nSkipping {file['name']} - already exists")
                    continue

                print(f"\nDownloading {file['name']}...")
                download_file(service, file["id"], filename, file["mimeType"])


if __name__ == "__main__":
    main()
