import pandas as pd
import matplotlib.pyplot as plt
import shutil
import os
from pathlib import Path
from token_counting import get_token_encoder, count_tokens_in_file
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SPREADSHEET_ID  # Importing the spreadsheet ID from config


def get_file_type(file_path):
    """Get file type from extension."""
    return file_path.suffix.lower()[1:] if file_path.suffix else "no_extension"


def get_excluded_files():
    """Fetch the list of files to exclude from the Google Sheets spreadsheet."""
    try:
        # Create credentials and build service
        credentials = service_account.Credentials.from_service_account_file(
            "service-account.json", scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sheets_service = build("sheets", "v4", credentials=credentials)

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

        # Find the indices of the File and Exclude columns
        headers = values[0]
        file_col_idx = headers.index("File") if "File" in headers else 0
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

        print(f"Found {len(excluded_files)} files to exclude from processing.")
        return excluded_files

    except Exception as e:
        print(f"Warning: Could not fetch exclusion data from spreadsheet: {e}")
        return set()


def move_to_excluded(file_path, sources_dir):
    """Move a file to the sources/excluded directory, preserving subdirectory structure."""
    rel_path = file_path.relative_to(sources_dir)
    excluded_dir = sources_dir / "excluded"

    # Create the destination directory (and parents)
    dest_file = excluded_dir / rel_path
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    # Move the file if it doesn't already exist in the destination
    if not dest_file.exists():
        try:
            shutil.move(str(file_path), str(dest_file))
            return True
        except Exception as e:
            print(f"Error moving file {file_path}: {e}")
            return False
    else:
        # File already exists in the excluded directory
        print(f"File already exists in excluded directory: {rel_path}")
        # Delete the original if it's a duplicate
        try:
            os.remove(file_path)
            print(f"Removed duplicate file: {file_path}")
            return True
        except Exception as e:
            print(f"Error removing duplicate file {file_path}: {e}")
            return False


def remove_empty_dirs(directory):
    """Recursively remove empty directories."""
    removed_count = 0

    for root, dirs, files in os.walk(directory, topdown=False):
        # Skip the excluded directory
        if "excluded" in root.split(os.path.sep):
            continue

        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)

            # Skip the excluded directory
            if "excluded" in dir_path:
                continue

            try:
                # Check if directory is empty (no files/subdirs)
                if not os.listdir(dir_path):
                    print(f"Removing empty directory: {dir_path}")
                    os.rmdir(dir_path)
                    removed_count += 1
            except (OSError, PermissionError) as e:
                print(f"Error removing directory {dir_path}: {e}")

    return removed_count


def main():
    # Initialize tiktoken encoder once to reuse
    encoding = get_token_encoder()

    # Get all files from sources directory
    sources_dir = Path("sources")
    if not sources_dir.exists():
        print("Sources directory not found!")
        return

    # Create the excluded directory if it doesn't exist
    excluded_dir = sources_dir / "excluded"
    excluded_dir.mkdir(exist_ok=True)

    # Get list of files to exclude from the spreadsheet
    files_to_exclude = get_excluded_files()

    # Collect token counts for each file
    token_counts = []
    excluded_count = 0
    moved_count = 0
    for file_path in sources_dir.rglob("*"):
        # Skip the excluded directory itself
        if str(file_path).startswith(str(excluded_dir)):
            continue

        if file_path.is_file():
            rel_path = str(file_path.relative_to(sources_dir))

            # Check if the file should be excluded
            # Since the spreadsheet has full filenames and our files might be in subdirectories,
            # we check if any excluded filename is in the file path
            should_exclude = any(exclude_name in rel_path for exclude_name in files_to_exclude)

            if should_exclude:
                excluded_count += 1
                # Move the file to the excluded directory
                if move_to_excluded(file_path, sources_dir):
                    moved_count += 1
                continue

            tokens = count_tokens_in_file(file_path, encoding)
            token_counts.append(
                {
                    "file": rel_path,
                    "file_type": get_file_type(file_path),
                    "tokens": tokens,
                }
            )

    # Remove empty directories after moving files
    removed_dirs = remove_empty_dirs(sources_dir)

    # Create DataFrame
    df = pd.DataFrame(token_counts)

    # Print exclusion info
    if excluded_count > 0:
        print(f"Excluded {excluded_count} files based on spreadsheet data.")
        print(f"Moved {moved_count} files to {excluded_dir}")
        print(f"Removed {removed_dirs} empty directories from {sources_dir}")

    # Sort by token count
    df = df.sort_values("tokens", ascending=False)

    # Calculate total tokens
    total_tokens = df["tokens"].sum()

    # Print summary table by file
    print("\nToken Count Summary by File:")
    print("=" * 100)
    print(df[["file", "tokens"]].to_string(index=False))
    print("=" * 100)

    # Print summary by file type
    print("\nToken Count Summary by File Type:")
    print("=" * 80)
    type_summary = df.groupby("file_type").agg({"tokens": ["count", "sum", "mean", "min", "max"]}).round(2)
    type_summary.columns = [
        "Number of Files",
        "Total Tokens",
        "Average Tokens",
        "Min Tokens",
        "Max Tokens",
    ]
    print(type_summary.to_string())
    print("=" * 80)

    print(f"\nTotal tokens across all files: {total_tokens:,}")

    # Create histograms
    plt.figure(figsize=(15, 10))

    # Overall distribution
    plt.subplot(2, 1, 1)
    plt.hist(df["tokens"], bins=30, edgecolor="black")
    plt.title("Overall Distribution of Token Counts")
    plt.xlabel("Number of Tokens")
    plt.ylabel("Number of Files")
    plt.grid(True, alpha=0.3)

    # Distribution by file type
    plt.subplot(2, 1, 2)
    for file_type in df["file_type"].unique():
        type_data = df[df["file_type"] == file_type]["tokens"]
        plt.hist(type_data, bins=20, alpha=0.5, label=file_type)
    plt.title("Distribution of Token Counts by File Type")
    plt.xlabel("Number of Tokens")
    plt.ylabel("Number of Files")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save histograms
    plt.savefig("token_distribution.png")
    print("\nHistograms saved as 'token_distribution.png'")


if __name__ == "__main__":
    main()
