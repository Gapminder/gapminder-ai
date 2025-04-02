import tiktoken
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def count_tokens_in_file(file_path, encoding):
    """Count tokens in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tokens = encoding.encode(content)
        return len(tokens)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0


def get_file_type(file_path):
    """Get file type from extension."""
    return file_path.suffix.lower()[1:] if file_path.suffix else "no_extension"


def main():
    # Initialize tiktoken encoder
    encoding = tiktoken.get_encoding("cl100k_base")

    # Get all files from sources directory
    sources_dir = Path("sources")
    if not sources_dir.exists():
        print("Sources directory not found!")
        return

    # Collect token counts for each file
    token_counts = []
    for file_path in sources_dir.rglob("*"):
        if file_path.is_file():
            tokens = count_tokens_in_file(file_path, encoding)
            token_counts.append(
                {
                    "file": str(file_path.relative_to(sources_dir)),
                    "file_type": get_file_type(file_path),
                    "tokens": tokens,
                }
            )

    # Create DataFrame
    df = pd.DataFrame(token_counts)

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
    main()
