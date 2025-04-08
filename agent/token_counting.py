import tiktoken
from pathlib import Path


def get_token_encoder():
    """Get the tiktoken encoder."""
    return tiktoken.get_encoding("cl100k_base")


def count_tokens_in_file(file_path, encoding=None):
    """Count tokens in a single file.

    Args:
        file_path: Path to the file (str or Path object)
        encoding: Optional tiktoken encoding. If not provided, will create a new one.

    Returns:
        int: Number of tokens in the file, or 0 if there was an error
    """
    if encoding is None:
        encoding = get_token_encoder()

    try:
        file_path = Path(file_path)
        if not file_path.is_file():
            return 0

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tokens = encoding.encode(content)
        return len(tokens)
    except Exception as e:
        print(f"Error counting tokens in {file_path}: {e}")
        return 0


def count_tokens_in_directory(directory_path, encoding=None):
    """Count tokens in all files in a directory.

    Args:
        directory_path: Path to the directory (str or Path object)
        encoding: Optional tiktoken encoding. If not provided, will create a new one.

    Returns:
        int: Total number of tokens in all files in the directory
    """
    if encoding is None:
        encoding = get_token_encoder()

    try:
        directory_path = Path(directory_path)
        if not directory_path.is_dir():
            return 0

        total_tokens = 0
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                total_tokens += count_tokens_in_file(file_path, encoding)
        return total_tokens
    except Exception as e:
        print(f"Error counting tokens in directory {directory_path}: {e}")
        return 0
