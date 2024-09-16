import duckdb
import polars as pl


results = pl.read_parquet("../output/results.parquet")

results.columns

df = results.filter(pl.col("model_id").str.contains("llama"))


conn = duckdb.connect()


conn.query("select * from df")

q = """select
  *
from
  df
where
  not (
    llama3_evaluator_correctness = vertex_ai_evaluator_correctness
    and gpt4_evaluator_correctness = vertex_ai_evaluator_correctness
    and (
      simple_evaluator_matching <> 0
      and simple_evaluator_matching = gpt4_evaluator_correctness
    )
  )
  and simple_evaluator_matching <> 0"""

diffs = conn.query(q)

conn.query("select count(*) from df")
conn.query("select count(*) from diffs")

diffs.to_csv("to_check.csv")

1281 / 30780

