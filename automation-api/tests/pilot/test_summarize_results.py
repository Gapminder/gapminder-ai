from pathlib import Path

import polars as pl
import pytest

from lib.pilot.summarize_results import (
    calculate_final_score,
    extract_custom_id_info,
    extract_score,
    main,
)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "data" / "example_batch"


@pytest.fixture
def example_data_dir(tmp_path):
    """Copy test data to a temporary directory for testing"""
    # Copy test files to temporary directory
    for src_file in TEST_DATA_DIR.glob("*.jsonl"):
        dest_file = tmp_path / src_file.name
        dest_file.write_text(src_file.read_text())

    return tmp_path


def test_main_processing(example_data_dir, tmp_path):
    """Test end-to-end processing flow"""
    # Run the main function with our test data
    main(example_data_dir, tmp_path)

    # Verify output files were created
    output_files = list(tmp_path.glob("*.parquet"))
    assert len(output_files) == 2, "Should generate 2 parquet files"
    master_output_file = list(tmp_path.glob("master_output*.csv"))
    assert len(master_output_file) == 1, "Should generate 1 master output"

    # Check the content of the output file
    df = pl.read_parquet(output_files[0])

    # Verify expected columns
    expected_columns = {
        "model_config_id",
        "question_id",
        "prompt_variation_id",
        "response",
        "final_correctness",
    }
    assert set(df.columns).issuperset(expected_columns)

    # Verify row count matches input data
    assert df.height > 0, "Output should contain data rows"


def test_extract_score():
    """Test score extraction from evaluation responses"""
    assert extract_score("This answer is grade A\n\nA") == 0
    assert extract_score("The answer deserves a B\nB") == 1
    assert extract_score("This response is a C quality answer\n\nC") == 2
    assert extract_score("Final grade: D\nD") == 3
    assert extract_score("???") == -1


def test_extract_custom_id():
    """Test custom ID parsing"""
    info = extract_custom_id_info("model123-q42-pv7", "model123")
    assert info["model_config_id"] == "model123"
    assert info["question_id"] == "q42"
    assert info["prompt_variation_id"] == "pv7"

    # Test with metric ID
    info = extract_custom_id_info("model123-q42-pv7-correctness", "model123")
    assert info["model_config_id"] == "model123"
    assert info["question_id"] == "q42"
    assert info["prompt_variation_id"] == "pv7"
    assert info["metric_id"] == "correctness"


def test_calculate_final_score():
    """Test score calculation logic with various scenarios"""

    # If all scores are -1 or list is empty, return -1
    assert calculate_final_score([]) == -1, "Empty list should return -1"
    assert calculate_final_score([-1, -1, -1]) == -1, "All -1 scores should return -1"

    # If there's a clear majority winner, return that winner
    assert calculate_final_score([0, 0, 0]) == 0, "All identical scores should return that score"
    assert calculate_final_score([1, 1, 2]) == 1, "Clear majority should win"
    assert calculate_final_score([1, 1, 2, -1, -1]) == 1, "Should filter out -1 scores"

    # Otherwise, return 0 for ties
    assert calculate_final_score([1, 2, 3]) == 0, "All different scores should return 0"
    assert calculate_final_score([1, 1, 2, 2]) == 0, "Tied scores should return 0"

    # Edge cases
    assert calculate_final_score([-1, -1, -1, -1]) == -1, "All error scores should return -1"
    assert calculate_final_score([-1]) == -1, "Single error score should return -1"
    assert calculate_final_score([0]) == 0, "Single valid score should return that score"
    assert calculate_final_score([1, 2, 3, 2, 2, 1, 3, 3, 3, 3]) == 3, "Should handle longer lists"
    assert calculate_final_score([-1, -1, 1]) == 1, "Single valid score with errors should return that score"
