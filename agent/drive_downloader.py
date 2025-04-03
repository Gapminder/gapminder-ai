import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import multiprocessing
from config import FOLDER_ID
from common import (
    GOOGLE_WORKSPACE_MIME_TYPES,
    get_export_mime_type,
    get_intermediate_filename,
    clean_filename_preserve_spaces,
)

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
        return []

    print("\nFiles found in Google Drive:")
    all_files = []
    for item in items:
        if item["mimeType"] != "application/vnd.google-apps.folder":
            print(f"- {item['name']} ({item['id']}, {item['mimeType']})")
            all_files.append(item)
        else:
            print(f"- Skipping folder: {item['name']}")
    return all_files


def _download_file_logic(service, file_id, final_filename, mime_type):
    """Core logic to download/export a file from Google Drive."""
    try:
        request = None
        if mime_type in GOOGLE_WORKSPACE_MIME_TYPES:
            export_mime_type = get_export_mime_type(mime_type)
            request = service.files().export(fileId=file_id, mimeType=export_mime_type)
            print(f"Exporting '{final_filename}' as {export_mime_type}...")
        else:
            request = service.files().get_media(fileId=file_id)
            print(f"Downloading '{final_filename}'...")

        if request is None:
            print(f"Skipping {final_filename} due to unknown type or error determining action.")
            return

        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                print(f"Process {os.getpid()}: Download {final_filename} {int(status.progress() * 100)}%")
            else:
                print(f"Process {os.getpid()}: Download {final_filename} status unknown, continuing...")

        with open(final_filename, "wb") as f:
            f.write(file_content.getvalue())
        print(f"Process {os.getpid()}: Successfully downloaded {final_filename}")

    except Exception as e:
        print(f"Process {os.getpid()}: An error occurred downloading {final_filename} (ID: {file_id}): {e}")


def download_worker(file_info):
    """Worker process function to handle downloading a single file."""
    try:
        service = get_google_drive_service()
        file_id = file_info["id"]
        original_name = clean_filename_preserve_spaces(file_info["name"])
        mime_type = file_info["mimeType"]
        base_download_path = os.path.join("downloads", original_name)

        final_filename = get_intermediate_filename(base_download_path, mime_type)

        if os.path.exists(final_filename):
            print(f"Process {os.getpid()}: Skipping {final_filename} - already exists.")
            return

        _download_file_logic(service, file_id, final_filename, mime_type)

    except Exception:
        pass


def main():
    if not os.path.exists("downloads"):
        print("Creating downloads directory.")
        os.makedirs("downloads")

    print("Initializing Google Drive service...")
    try:
        service = get_google_drive_service()
    except Exception:
        print("Failed to initialize main Google Drive service. Exiting.")
        return

    print(f"Listing files in folder ID: {FOLDER_ID}...")
    all_files = list_files_in_folder(service, FOLDER_ID)

    if not all_files:
        print("No files eligible for download found.")
        return

    # Filter out files that already exist
    files_to_download = []
    for file_info in all_files:
        original_name = clean_filename_preserve_spaces(file_info["name"])
        mime_type = file_info["mimeType"]
        base_download_path = os.path.join("downloads", original_name)
        final_filename = get_intermediate_filename(base_download_path, mime_type)

        if os.path.exists(final_filename):
            print(f"Skipping {final_filename} - already exists.")
            continue

        files_to_download.append(file_info)

    if not files_to_download:
        print("All files already downloaded.")
        return

    print(f"\nScheduling download of {len(files_to_download)} files out of {len(all_files)} total files...")
    num_processes = multiprocessing.cpu_count()
    print(f"Starting parallel download using {num_processes} processes...")

    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.map(download_worker, files_to_download)

    print("\nAll download tasks completed.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
