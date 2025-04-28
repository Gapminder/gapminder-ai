"""
Notebook for converting some old experiment results
"""

import pandas as pd
import polars as pl
from typing import Dict


# read experiment results
res1 = pd.read_excel("../yival_experiment_archives/20240921/results.xlsx")
res2 = pd.read_excel("../yival_experiment_archives/20241122/results.xlsx")
res3 = pd.read_excel("../yival_experiment_archives/20241205/results.xlsx")


res1
res2
res3

res1.columns
res2.columns
res3.columns

# do some renaming of columns
column_mapping = {
    "gpt4_evaluator_gpt4_eval_correctness": "gpt4_evaluator_gpt4_correctness",
    "vertex_ai_evaluator_gemini_eval_correctness": "vertex_ai_evaluator_gemini_correctness",  # noqa
    "vertex_ai_evaluator_claude_eval_correctness": "vertex_ai_evaluator_claude_correctness",  # noqa
}
res1 = res1.rename(columns=column_mapping)

# combine all
res = pd.concat([res1, res2, res3], ignore_index=True)
res.columns

# we only need qwen and xai data, so we need to filter them
res = res[res.model_id.isin(["qwen-max-2024-09-19", "xai/grok-beta"])]


# make sure columns have correct types
res["question_id"] = res["question_id"].map(str)


# check if we have all questions?
len(res.question_id.unique())


# I will need the model_config_id for models
model_config_mapping = {"qwen-max-2024-09-19": "mc039", "xai/grok-beta": "mc040"}
res["model_config_id"] = res["model_id"].map(model_config_mapping)

# I will need the prompt_variation_id for all prompts
prompts = pd.read_csv("../20250109/ai_eval_sheets/prompt_variations.csv")
prompts.columns


# create a column for question_prompt_template, formatted by data in question_template
prompts["final_prompt_template"] = prompts.apply(
    lambda row: row["question_prompt_template"].format(question=row["question_template"]),
    axis=1,
)

prompts_mapping = prompts.set_index("final_prompt_template")["variation_id"].to_dict()

len(prompts_mapping)

res["prompt_variation_id"] = res["prompt_template"].map(prompts_mapping)

res

# now create the final score
res.human_rating_score.dropna()  # no human rating. just use evaluators data


res = pl.from_pandas(res)

res.columns


# copy the function from other notebook
def calculate_final_score(row: pl.Series) -> int:
    """Calculate final correctness score based on majority agreement"""
    scores = [
        row["gpt4_evaluator_gpt4_correctness"],  # type: ignore
        row["vertex_ai_evaluator_claude_correctness"],  # type: ignore
        row["vertex_ai_evaluator_gemini_correctness"],  # type: ignore
    ]

    # Count occurrences of each score
    score_counts: Dict[int, int] = {}
    for score in scores:
        score_counts[score] = score_counts.get(score, 0) + 1  # type: ignore

    # Find the score with highest count
    max_count = max(score_counts.values())
    if max_count >= 2:
        # Return the score that appears at least twice
        return next(score for score, count in score_counts.items() if count == max_count)
    else:
        # All scores different
        return 0


res_ = res.with_columns(
    final_correctness=pl.struct(
        [
            "gpt4_evaluator_gpt4_correctness",
            "vertex_ai_evaluator_claude_correctness",
            "vertex_ai_evaluator_gemini_correctness",
        ]
    ).map_elements(
        calculate_final_score, return_dtype=pl.Int32
    )  # type: ignore
)

res_ = res_.select(
    pl.col(
        [
            "model_config_id",
            "question_id",
            "prompt_variation_id",
            "raw_output",
            "gpt4_evaluator_gpt4_correctness",
            "vertex_ai_evaluator_claude_correctness",
            "vertex_ai_evaluator_gemini_correctness",
            "final_correctness",
        ]
    )
)

res_ = res_.rename(
    {
        "raw_output": "response",
        "gpt4_evaluator_gpt4_correctness": "gpt4_correctness",
        "vertex_ai_evaluator_claude_correctness": "claude_correctness",
        "vertex_ai_evaluator_gemini_correctness": "gemini_correctness",
    }
)

res_


# let's check if it's same sturcture as other new experiment outputs
other = pl.read_parquet("../20250109/mc041_output.parquet")
other


# good, create the output
output1 = res_.filter(pl.col("model_config_id") == "mc039")
output2 = res_.filter(pl.col("model_config_id") == "mc040")

output1

output2

# Find which question_ids in output2 are not in output1
output1_qids = set(output1.get_column("question_id").unique())
output2_qids = set(output2.get_column("question_id").unique())

missing_qids = output2_qids - output1_qids
print(f"Found {len(missing_qids)} questions in output2 that are not in output1:")
print(sorted(list(missing_qids)))


# write the outputs
output1.write_parquet("./mc039_output.parquet")
output2.write_parquet("./mc040_output.parquet")
