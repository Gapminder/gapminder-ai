# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Usage
#
# Use this notebook to generate a file which contains results which auto mark correctness is different from LLM agent evaluator. Then merge the result back.

# %% [markdown]
# ## Generate file

# %%
# going to use duckdb
# %load_ext sql

# %%
# %sql duckdb://

# %%
import os.path as osp
import pandas as pd

output_dir = '../output/archives/20240401'

# %%
result_file = osp.join(output_dir, 'results.xlsx')

result_df = pd.read_excel(result_file)

# %% magic_args="--save result_to_check_1 " language="sql"
# select * 
# from result_df 
# where auto_mark_correctness != correctness

# %% magic_args="--save result_to_check_2" language="sql"
# select 
#     *,
#     case 
#         when auto_mark_correctness = 0 and correctness = 3 and not contains(lower(raw_output), lower(correct_answer)) then 1
#         when (correctness = 1 or correctness = 2) and contains(lower(raw_output), lower(correct_answer)) then 1
#         when auto_mark_correctness = 0 and correctness = 0 then 1
#         when auto_mark_correctness = 1 OR auto_mark_correctness = 2 OR auto_mark_correctness = 3 then 1
#     else 0 
#     end as need_to_check
# from result_to_check_1
# where need_to_check = 1

# %%
# result_to_check = %sql select * exclude (need_to_check) from result_to_check_2

# %%
result_to_check_df = result_to_check.DataFrame()

# %%
result_to_check_df.to_excel(osp.join(output_dir, 'human_rating.xlsx'), index=False)

# %%

# %%

# %%
raise Exception("Please edit the human_rating file.")

# %% [markdown]
# ## Edit file, and then run below cells to merge back

# %%
rating_file = osp.join(output_dir, 'human_rating.xlsx')

# %%
human_ratings = pd.read_excel(rating_file)

# %%
human_ratings[~pd.isnull(human_ratings.human_rating_score)]

# %%
result_df_copy = result_df.copy()

# %%
result_df_copy = result_df_copy.reset_index()

# %% magic_args="merged_results << " language="sql"
# select 
#     r.* exclude (human_rating_score),
#     l.human_rating_score
# from 
#     result_df_copy r left join human_ratings l
#     on r.experiment_date = l.experiment_date 
#     and r.question_id = l.question_id 
#     and r.model_id = l.model_id 
#     and r.model_params = l.model_params 
#     and r.prompt_template = l.prompt_template

# %%
merged_results_df = merged_results.DataFrame()

# %%
merged_results_df

# %%
result_df_copy

# %%
assert merged_results_df.shape == result_df.shape

# %%
merged_results_df[~pd.isnull(merged_results_df.human_rating_score)]

# %%
merged_results_df.to_excel(osp.join(output_dir, 'results.xlsx'), index=False)

# %%
