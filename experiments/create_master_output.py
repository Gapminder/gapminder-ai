"""
Notebook to upload the results to ai eval sheets.
"""

from glob import glob
import polars as pl
from typing import List


def create_master_output(output_folder: str, language: str = "en-US") -> pl.DataFrame:
    """Create a master output DataFrame from parquet files in a folder.

    Args:
        output_folder: Folder containing parquet files with results
        language: Language code to add to results (default: "en-US")

    Returns:
        DataFrame with standardized columns for upload
    """
    # Define mapping for correctness values
    result_map = {-1: "n/a", 0: "fail", 1: "very_wrong", 2: "wrong", 3: "correct"}

    # Read and combine all parquet files
    res_list = [pl.read_parquet(x) for x in glob(f"{output_folder}/*parquet")]
    res = pl.concat(res_list)

    # Add metadata columns and map correctness
    res = res.with_columns(
        pl.lit(language).alias("language"),
        pl.lit(output_folder.split("/")[-1]).alias("last_evaluation_datetime"),
        pl.col("final_correctness").replace_strict(result_map).alias("result"),
    )

    # Select and rename columns for upload with correct order
    return res.select(
        [
            pl.col("question_id"),
            pl.col("language"),
            pl.col("prompt_variation_id"),
            pl.col("model_config_id").alias("model_configuration_id"),
            pl.col("last_evaluation_datetime"),
            pl.col("result"),
        ]
    )


final_df1 = create_master_output("20250208")
final_df1

final_df1.write_csv("master_output_20250208.csv")

final_df2 = create_master_output("./20250205")
final_df2

final_df2.write_csv("master_output_20250205.csv")


def create_combined_raw_output(output_folders: List[str]) -> pl.DataFrame:
    """Create a combined DataFrame from raw parquet files in multiple folders.

    Args:
        output_folders: List of folders containing raw parquet files

    Returns:
        Combined DataFrame with all raw data
    """
    # Find all parquet files in all folders
    parquet_files = []
    for folder in output_folders:
        parquet_files.extend(glob(f"{folder}/*parquet"))

    # Read and combine all parquet files
    dfs = [pl.read_parquet(file) for file in parquet_files]
    return pl.concat(dfs)


raw_outputs = create_combined_raw_output(
    ["./20240921-20241205/", "./20250109/", "./20250120/", "./20250205", "20250208"]
)

raw_outputs

# mc039 is no longer the latest
raw_outputs = raw_outputs.filter(pl.col("model_config_id") != "mc039")

raw_outputs["question_id"].unique()


raw_outputs.write_parquet("./latest_model_responses.parquet")
