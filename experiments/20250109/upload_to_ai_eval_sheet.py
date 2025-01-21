"""
Notebook to upload the results to ai eval sheets.
"""


from lib.config import read_config
from lib.pilot.utils import read_ai_eval_spreadsheet

import polars as pl


config = read_config()


ai_eval_sheet = read_ai_eval_spreadsheet()


backup = ai_eval_sheet.evaluation_results.data.df.copy()

backup.columns


# read result data
res1 = pl.read_parquet("./mc041_output.parquet")
res2 = pl.read_parquet("./mc043_output.parquet")
res3 = pl.read_parquet("./mc044_output.parquet")
res4 = pl.read_parquet("./mc045_output.parquet")

res1.shape
res2.shape
res3.shape
res4.shape

res = pl.concat([res1, res2, res3, res4])

# Define mapping for correctness values
result_map = {0: "fail", 1: "very_wrong", 2: "wrong", 3: "correct"}

# Add language and evaluation time columns
res = res.with_columns(
    pl.lit("en-US").alias("language"),
    pl.lit("20250109").alias("last_evaluation_datetime")
)

# Map final_correctness to result using the mapping
res = res.with_columns(
    pl.col("final_correctness").map_dict(result_map).alias("result")
)

# Select relevant columns for upload
upload_df = res.select([
    "model_config_id",
    "question_id", 
    "prompt_variation_id",
    "response",
    "language",
    "last_evaluation_datetime",
    "result"
])

# Print shape and preview
print(upload_df.shape)
print(upload_df.head())


