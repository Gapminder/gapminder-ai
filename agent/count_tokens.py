import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from token_counting import get_token_encoder, count_tokens_in_file
from lib.spreadsheet import get_list_files
from lib.fileops import ensure_directories, move_to_excluded, remove_empty_dirs


def get_file_type(file_path):
    """Get file type from extension."""
    return file_path.suffix.lower()[1:] if file_path.suffix else "no_extension"


def main():
    # Initialize tiktoken encoder once to reuse
    encoding = get_token_encoder()

    # Get all files from sources directory
    sources_dir = Path("sources")
    if not sources_dir.exists():
        print("Sources directory not found!")
        return

    # Create the necessary directories if they don't exist
    ensure_directories()

    # Get list of files to exclude from the spreadsheet
    files_to_exclude = get_list_files(subset="excluded")

    # Collect token counts for each file
    token_counts = []
    excluded_count = 0
    moved_count = 0

    for file_path in sources_dir.rglob("*"):
        # Skip the excluded directory
        excluded_dir = sources_dir / "excluded"
        if str(file_path).startswith(str(excluded_dir)):
            continue

        if file_path.is_file():
            rel_path = str(file_path.relative_to(sources_dir))
            file_name = file_path.name

            # Check if the file should be excluded
            # Check both the full path and just the filename
            should_exclude = any(
                exclude_name in rel_path or exclude_name == file_name for exclude_name in files_to_exclude
            )

            if should_exclude:
                excluded_count += 1
                # Move the file to the excluded directory
                if move_to_excluded(file_path, preserve_structure=True):
                    moved_count += 1
                continue

            # Count tokens and add to our collection
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

    # Print exclusion and categorization info
    if excluded_count > 0:
        print(f"Excluded {excluded_count} files based on spreadsheet data.")
        print(f"Moved {moved_count} files to the excluded directory")

    print(f"Removed {removed_dirs} empty directories from {sources_dir}")

    # Sort by token count
    df = df.sort_values("tokens", ascending=False)

    # Calculate total tokens
    total_tokens = df["tokens"].sum()

    # Show the top N largest sources by token count
    top_n = 20  # Show top 20 files
    print("\nTop Largest Sources by Token Count:")
    print("=" * 100)
    top_files = df.head(top_n)[["file", "tokens", "file_type"]]

    # Calculate percentage of total tokens
    top_files["percent"] = (top_files["tokens"] / total_tokens * 100).round(2)

    # Format the output
    formatted_top = top_files.copy()
    formatted_top["tokens"] = formatted_top["tokens"].apply(lambda x: f"{x:,}")
    formatted_top["percent"] = formatted_top["percent"].apply(lambda x: f"{x}%")
    print(formatted_top.to_string(index=False))

    # Show cumulative stats for top files
    top_tokens = top_files["tokens"].sum()
    top_percent = (top_tokens / total_tokens * 100).round(2)
    print("-" * 100)
    print(f"Top {top_n} files: {top_tokens:,} tokens ({top_percent}% of total)")
    print("=" * 100)

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
