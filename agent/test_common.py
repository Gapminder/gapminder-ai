from common import get_converted_filename, get_intermediate_filename, GOOGLE_DOC_MIME_TYPE


def test_get_converted_filename_with_dots_in_name():
    """Test that filenames with dots in the base name are handled correctly."""
    # Test Google Doc conversion (should become .md) and perserve spaces
    filename = "q 631.1 - Vaccination of children "
    result = get_converted_filename(filename, GOOGLE_DOC_MIME_TYPE)
    assert result == "q 631.1 - Vaccination of children .md"

    # Test Google Sheet conversion (should become _sheets directory)
    # add later

    # Test Google Slides conversion (should become .txt)
    # add later


def test_get_converted_filename_with_standard_extensions():
    """Test that standard file extensions are handled correctly."""
    # Test HTML file (should become .md)
    filename = "index.html"
    result = get_converted_filename(filename, "text/html")
    assert result == "index.md"

    # Test PDF file (should become .txt)
    filename = "document.pdf"
    result = get_converted_filename(filename, "application/pdf")
    assert result == "document.txt"


def test_get_converted_filename_with_unsupported_types():
    """Test that unsupported file types return None."""
    # Test unsupported image file
    filename = "image.jpg"
    result = get_converted_filename(filename, "image/jpeg")
    assert result is None


def test_get_intermediate_filename_with_dots_in_name():
    """Test that intermediate filenames with dots in the base name are handled correctly."""
    # Test Google Doc conversion (should become .html)
    filename = "downloads/q 631.1 - Vaccination of children "
    result = get_intermediate_filename(filename, GOOGLE_DOC_MIME_TYPE)
    assert result == "downloads/q 631.1 - Vaccination of children .html"

    # Test Google Sheet conversion (should become .xlsx)
    # add later

    # Test Google Slides conversion (should become .pdf)
    # add later

    # Test non-Google file (should keep original name)
    filename = "downloads/document.pdf"
    result = get_intermediate_filename(filename, "application/pdf")
    assert result == "downloads/document.pdf"
