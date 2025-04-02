# Google Drive File Downloader

This script allows you to list and download files from a specific Google Drive folder using a service account.

## Setup Instructions

1. Create and activate virtual environment using UV:
   ```bash
   # Create virtual environment
   uv venv
   
   # Activate virtual environment
   source .venv/bin/activate
   ```

2. Install dependencies using UV:
   ```bash
   uv pip install -r requirements.txt
   ```

3. Get service account key:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "IAM & Admin" > "Service Accounts"
   - Find the service account: `gapminderbot@gapminder-ai.iam.gserviceaccount.com`
   - Click on the service account email
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Click "Create"
   - Save the downloaded JSON file as `service-account.json` in the same directory as this script

4. Share the Google Drive folder:
   - Open the Google Drive folder you want to access
   - Click "Share"
   - Add the service account email: `gapminderbot@gapminder-ai.iam.gserviceaccount.com`
   - Give it "Viewer" access
   - Click "Share"

## Usage

1. Make sure your virtual environment is activated:
   ```bash
   source .venv/bin/activate
   ```

2. Download files from Google Drive:
   ```bash
   python drive_downloader.py
   ```
   This will:
   - List all files in the specified Google Drive folder
   - Create a `downloads` directory if it doesn't exist
   - Download all files from the folder to the `downloads` directory
   - Skip any files that have already been downloaded

3. Convert downloaded files to appropriate formats:
   ```bash
   python convert_files.py
   ```
   This will:
   - Create a `sources` directory if it doesn't exist
   - Convert Google Docs (HTML) to Markdown (.md) in the `sources` directory
   - Convert Excel files to CSV (one file per sheet) in `sources/<filename>_sheets/`
   - Skip other file types
   - Keep original files in the `downloads` directory

## Notes

- The script uses read-only access to Google Drive
- Downloaded files are saved in a `downloads` directory
- Converted files are saved in a `sources` directory
- The script skips Google Drive folders and only downloads files
- Progress is shown for each download
- Make sure to keep your `service-account.json` file secure and never commit it to version control
- Google Workspace files are automatically exported to compatible formats:
  - Documents → HTML (then converted to Markdown in `sources/`)
  - Spreadsheets → Excel (.xlsx, then converted to CSV in `sources/<filename>_sheets/`)
  - Presentations → PDF
  - Drawings → PNG 