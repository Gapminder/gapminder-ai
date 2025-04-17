import pandas as pd
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


def extract_doc_id(url):
    """Extract Google Doc ID from URL."""
    if not url or not isinstance(url, str):
        return None

    # Match patterns like:
    # https://docs.google.com/document/d/DOC_ID/edit
    # https://docs.google.com/document/d/DOC_ID/
    match = re.search(r"/d/([^/]+)", url)
    return match.group(1) if match else None


def get_doc_name(service, file_id):
    """Get document name from Google Drive using file ID."""
    try:
        result = service.files().get(fileId=file_id, fields="name").execute()
        return result.get("name")
    except HttpError as e:
        print(f"Google Drive API error: {e}")
        return None
    except Exception as e:
        print(f"Error getting document name: {e}")
        return None


def main():
    # Initialize Google Drive service
    try:
        service = get_google_drive_service()
    except Exception as e:
        print(f"Failed to initialize Google Drive service: {e}")
        return

    # Define file paths
    questions_sources_path = "igno_index/Contentful Questions Export - Questions sources.csv"
    igno_index_path = "igno_index/Igno Index (World Views) - IgnoQs.csv"

    print("=== Debug Info ===")

    # Step 1: Read all globalIds from first file
    try:
        # Read first CSV with pandas
        df1 = pd.read_csv(questions_sources_path, dtype=str)
        print(f"Columns in {questions_sources_path}: {list(df1.columns)}")

        global_ids = set(df1["globalId"].dropna().unique())
        print(f"Found {len(global_ids)} global IDs")
    except Exception as e:
        print(f"Error reading {questions_sources_path}: {str(e)}")
        return

    # Step 2: Read Igno Index file and build mapping
    try:
        # Read second CSV, skipping first row (header is on second row)
        df2 = pd.read_csv(igno_index_path, skiprows=1, dtype=str)
        print(f"Columns in {igno_index_path}: {list(df2.columns)}")

        # Find matching columns (case insensitive)
        contentful_col = next((col for col in df2.columns if "contentful" in col.lower() and "id" in col.lower()), None)
        s2_col = next((col for col in df2.columns if "s2-doc" in col.lower() and "link" in col.lower()), None)

        if not contentful_col or not s2_col:
            print(f"Error: Could not find required columns in {igno_index_path}")
            print(f"Contentful ID column: {contentful_col}")
            print(f"S2-doc link column: {s2_col}")
            return

        # Build mapping
        contentful_to_s2 = {}
        matched_rows = df2[df2[contentful_col].isin(global_ids)]
        for _, row in matched_rows.iterrows():
            contentful_id = row[contentful_col]
            doc_url = row[s2_col]
            doc_name = None

            if pd.notna(doc_url) and isinstance(doc_url, str) and doc_url.strip():
                doc_url = doc_url.strip()
                file_id = extract_doc_id(doc_url)
                if file_id:
                    try:
                        doc_name = get_doc_name(service, file_id)
                        if doc_name is None:
                            print(f"Warning: Could not fetch name for Contentful ID {contentful_id}, URL: {doc_url}")
                            doc_name = doc_url  # Fallback to URL
                    except Exception as e:
                        print(f"Error fetching name for Contentful ID {contentful_id} (File ID: {file_id}): {e}")
                        doc_name = doc_url  # Fallback to URL
                else:
                    print(f"Warning: Could not extract File ID from URL for Contentful ID {contentful_id}: {doc_url}")
                    doc_name = doc_url  # Fallback to URL
            else:
                print(f"Warning: Invalid or missing URL for Contentful ID {contentful_id}. Value: {doc_url}")
                doc_name = None

            contentful_to_s2[contentful_id] = doc_name

        print("\n=== Results ===")
        print(f"Found {len(contentful_to_s2)} matching entries")

        # Find and print keys with NaN values
        nan_keys = [k for k, v in contentful_to_s2.items() if pd.isna(v)]
        if nan_keys:
            print("\nKeys with NaN values:")
            for k in nan_keys:
                print(f"- {k}")

        # Save to JSON file
        output_path = "igno_index/mapping.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(contentful_to_s2, f, indent=2, ensure_ascii=False)
        print(f"\nSaved mapping to {output_path}")

    except Exception as e:
        print(f"Error reading {igno_index_path}: {str(e)}")
        return


if __name__ == "__main__":
    main()
