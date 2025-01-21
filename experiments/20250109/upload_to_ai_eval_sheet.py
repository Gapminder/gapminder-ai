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

res.shape

last_eval_time = "20250109"
lang = "en-US"
result_map = {0: "fail", 1: "very_wrong", 2: "wrong", 3: "correct"}



