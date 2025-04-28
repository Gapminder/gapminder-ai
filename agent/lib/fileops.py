import os
import shutil
from pathlib import Path

# Constants
SOURCES_DIR = Path("sources")
EXCLUDED_DIR = SOURCES_DIR / "excluded"


def ensure_directories():
    """Ensure necessary directories exist."""
    SOURCES_DIR.mkdir(exist_ok=True)
    EXCLUDED_DIR.mkdir(exist_ok=True)


def move_to_excluded(file_path, preserve_structure=True):
    """Move a file to the sources/excluded directory, preserving subdirectory structure if needed.

    Args:
        file_path (Path or str): Path to the file to be moved
        preserve_structure (bool): Whether to preserve directory structure

    Returns:
        bool: Whether the move was successful
    """
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"File does not exist: {file_path}")
        return False

    if not file_path.is_file():
        print(f"Not a file: {file_path}")
        return False

    # Skip if the file is already in the excluded directory
    if str(file_path).startswith(str(EXCLUDED_DIR)):
        return True

    if preserve_structure:
        # Get relative path from sources directory
        try:
            rel_path = file_path.relative_to(SOURCES_DIR)
            dest_file = EXCLUDED_DIR / rel_path
        except ValueError:
            # If file is not within sources directory, use just the filename
            dest_file = EXCLUDED_DIR / file_path.name
    else:
        # Put file directly in excluded directory without preserving structure
        dest_file = EXCLUDED_DIR / file_path.name

    # Create destination directory structure
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    # Move the file if it doesn't already exist in the destination
    if not dest_file.exists():
        try:
            shutil.move(str(file_path), str(dest_file))
            print(f"Moved to excluded: {file_path}")
            return True
        except Exception as e:
            print(f"Error moving file {file_path}: {e}")
            return False
    else:
        # File already exists in the excluded directory
        print(f"File already exists in excluded directory: {rel_path if 'rel_path' in locals() else file_path.name}")
        # Delete the original if it's a duplicate
        try:
            os.remove(file_path)
            print(f"Removed duplicate file: {file_path}")
            return True
        except Exception as e:
            print(f"Error removing duplicate file {file_path}: {e}")
            return False


def remove_empty_dirs(directory=SOURCES_DIR):
    """Recursively remove empty directories.

    Args:
        directory (Path or str): Directory to check for empty subdirectories

    Returns:
        int: Number of directories removed
    """
    directory = Path(directory)
    removed_count = 0

    for root, dirs, files in os.walk(directory, topdown=False):
        root_path = Path(root)

        # Skip the excluded directory itself
        if str(root_path).startswith(str(EXCLUDED_DIR)):
            continue

        for dir_name in dirs:
            dir_path = root_path / dir_name

            # Skip the excluded directory
            if "excluded" in str(dir_path):
                continue

            try:
                # Check if directory is empty (no files/subdirs)
                if not list(dir_path.iterdir()):
                    print(f"Removing empty directory: {dir_path}")
                    os.rmdir(dir_path)
                    removed_count += 1
            except (OSError, PermissionError) as e:
                print(f"Error removing directory {dir_path}: {e}")

    return removed_count
