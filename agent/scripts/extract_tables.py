#!/usr/bin/env python3

import json
from pathlib import Path
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Union, TypedDict

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TableData(TypedDict):
    table_index: int
    has_headers: bool
    headers: Optional[List[str]]
    data: List[Union[Dict[str, str], List[str]]]


class TableResult(TypedDict):
    source_file: str
    tables: List[TableData]


class TableExtractor:
    def __init__(self, downloads_dir: str = "downloads", output_dir: str = "metadata"):
        self.downloads_dir = Path(downloads_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def extract_tables_from_html(self, html_content: str) -> List[TableData]:
        """Extract all tables from HTML content and convert to list of dictionaries."""
        soup = BeautifulSoup(html_content, "html.parser")
        tables: List[TableData] = []

        for idx, table in enumerate(soup.find_all("table")):
            table_data: List[Union[Dict[str, str], List[str]]] = []
            rows = table.find_all("tr")

            # Extract headers if present
            headers: List[str] = []
            header_row = rows[0] if rows else None
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

            # Extract rows
            for row in rows[1:] if headers else rows:
                cells = row.find_all(["td", "th"])
                row_data = [cell.get_text(strip=True) for cell in cells]
                if any(row_data):  # Only add non-empty rows
                    if headers:
                        # Create dict if we have headers
                        row_dict = dict(zip(headers, row_data))
                        table_data.append(row_dict)
                    else:
                        # Just add as list if no headers
                        table_data.append(row_data)

            if table_data:  # Only add non-empty tables
                table_entry: TableData = {
                    "table_index": idx,
                    "has_headers": bool(headers),
                    "headers": headers if headers else None,
                    "data": table_data,
                }
                tables.append(table_entry)

        return tables

    def process_file(self, html_file: Path) -> Optional[TableResult]:
        """Process a single HTML file and return extracted tables."""
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            tables = self.extract_tables_from_html(content)

            if not tables:
                logger.warning(f"No tables found in {html_file}")
                return None

            result: TableResult = {"source_file": html_file.name, "tables": tables}
            return result

        except Exception as e:
            logger.error(f"Error processing {html_file}: {str(e)}")
            return None

    def process_all_files(self) -> None:
        """Process all HTML files in the downloads directory."""
        html_files = list(self.downloads_dir.glob("*.html"))

        if not html_files:
            logger.warning(f"No HTML files found in {self.downloads_dir}")
            return

        for html_file in html_files:
            logger.info(f"Processing {html_file}")
            result = self.process_file(html_file)

            if result:
                # Create JSON filename based on original filename
                json_filename = html_file.stem + ".json"
                json_path = self.output_dir / json_filename

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"Created {json_path}")


def main() -> None:
    extractor = TableExtractor()
    extractor.process_all_files()


if __name__ == "__main__":
    main()
