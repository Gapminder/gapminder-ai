import duckdb
import polars as pl


results = pl.read_parquet("../output/results.parquet")

results.columns

df = results.filter(pl.col("model_id").str.contains("llama"))


conn = duckdb.connect()


simple_eval_check = conn.query("select * from df where simple_evaluator_matching <> auto_mark_correctness")
simple_eval_check
simple_eval_check.to_csv("./simple_eval_check.csv")


# NEXT: review the query and begin to check results.
q = """select
  *
from
  df
where
  not (
    llama3_evaluator_correctness = vertex_ai_evaluator_correctness
    and gpt4_evaluator_correctness = vertex_ai_evaluator_correctness
  )
  or (
    auto_mark_correctness <> 0
    and (
      llama3_evaluator_correctness = vertex_ai_evaluator_correctness
      and gpt4_evaluator_correctness = vertex_ai_evaluator_correctness
    )
    and auto_mark_correctness <> gpt4_evaluator_correctness 
  )
  or (
    simple_evaluator_matching <> 0
    and (
      llama3_evaluator_correctness = vertex_ai_evaluator_correctness
      and gpt4_evaluator_correctness = vertex_ai_evaluator_correctness
    )
    and simple_evaluator_matching <> gpt4_evaluator_correctness 
  )
  
  """

diffs = conn.query(q)

conn.query("select count(*) from df")
conn.query("select count(*) from diffs")

diffs.to_csv("to_check_all.csv")

410 / 30780

# FIXME: the simple evaluator seems not working very well?
# just use the exact matching algo

