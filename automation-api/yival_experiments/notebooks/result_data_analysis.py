# # Result Data Analysis
#
# This notebook is for producing tables listed in https://docs.google.com/spreadsheets/d/1ln5ui3f13AfAQkBuEMbNomBXlZLhkQPYVEpBlZjUtu0/edit?pli=1#gid=0
#
# Latest Update: 2024-10-02

# going to use duckdb
# %load_ext sql

# %sql duckdb://

import pandas as pd
import polars as pl
from lib.pilot.helpers import read_ai_eval_spreadsheet, get_questions, get_model_configs, get_prompt_variants
from lib.config import read_config
import matplotlib.pyplot as plt

# load env
config = read_config()



# ## prepare data

# results to be analyzed
# manually download from AI eval spreadsheet.
result = pd.concat([
    pd.read_csv('./data/Gapminder AI evaluations - Master Output.csv'),
    # pd.read_csv('./data/Gapminder AI evaluations - Latest Results.csv'),
])

# load ai eval spreadsheet
ai_eval_sheet = read_ai_eval_spreadsheet()

result

# cleanup
result.columns = result.columns.map(lambda x: x.lower().replace(' ', '_'))

result



# + magic_args="--save result_to_analyze " language="sql"
# select
#     *,
#     CASE
#     WHEN ((Result = 'correct')) THEN (3)
#     WHEN ((Result = 'wrong')) THEN (2)
#     WHEN ((Result = 'very_wrong')) THEN (1)
#     WHEN ((Result = 'fail')) THEN (0)
#     ELSE 0
#   END AS score
# from result
# where model_configuration_id != 'mc026'  -- exclude qwen 1201

# + magic_args="--with result_to_analyze --save result_chn_prompt_renamed" language="sql"
# select
#    * exclude (prompt_variation_id),
#    replace(prompt_variation_id, '_zh', '') as prompt_variation_id
# from result_to_analyze
# -




# models
all_models = ai_eval_sheet.gen_ai_model_configs.data.df

all_models.tail()

# prompts
all_prompts = ai_eval_sheet.prompt_variations.data.df

all_prompts.tail()

# all_prompts_filtered = %sql select variation_id, prompt_family, prompt_variation, language, question_template, question_prompt_template from all_prompts where prompt_family != 'none';
all_prompts_filtered.DataFrame().to_csv('./data/outputs/prompts_table.csv', index=False)





# question in eval sheet
eval_questions = ai_eval_sheet.questions.data.df

eval_questions.columns

# all questions in contentful export
all_questions = pd.read_csv('./data/contentful_questions_data.csv')

# + magic_args="--save questions_and_topics" language="sql"
# SELECT
#   e."question_id",
#   e."published_version_of_question",
#   e."language",
#   l.wrongPercentage AS human_wrong_percentage,
#   str_split (l.included_in_tests_within_these_topic_ids, ';') AS topic_list,
#   filter (topic_list, (x -> x like 'sdg-world-__')) [1] AS sdg_topic,
#   filter (
#     topic_list,
#     (
#       x -> list_contains (
#         main.list_value (
#           'refugees',
#           'population',
#           'sustainable-development-misconception-study-2020',
#           '2017_gapminder_test',
#           'climate-misconception-study-2024',
#           'sdg-world-un-goals'
#         ),
#         x
#       )
#     )
#   ) AS other_topics_list,
#   list_string_agg(other_topics_list) as other_topics
# FROM
#   eval_questions AS e
#   LEFT JOIN all_questions AS l ON (
#     (
#       replace(e."question_id", '_text', '') = CAST(l.globalId AS VARCHAR)
#     )
#   )
# ORDER BY
#   e."language",
#   l.globalId;
# -

# export a csv for supplement tables
# question_table = %sql select * exclude (topic_list, other_topics_list) from questions_and_topics;
question_table_df = question_table.DataFrame()

question_table_df.to_csv('./data/outputs/question_table.csv', index=False)





# + magic_args="--save q_and_t" language="sql"
# -- only keep question id and topic list.
# select
#     question_id,
#     first(human_wrong_percentage) as human_wrong_percentage,
#     first(topic_list) as topic_list,
#     first(sdg_topic) as sdg_topic,
#     first(other_topics_list) as other_topics
# from questions_and_topics
# group by question_id
# -






# ## Summary

# ### Correctness Break Down by Model

# + magic_args="result_by_models <<" language="sql"
# select
#     m.model_id as model_id,
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from result_to_analyze r left join all_models m on r.model_configuration_id = m.model_config_id
# GROUP BY m.model_id
# order by correct_rate desc
# -
result_by_models_df = result_by_models.DataFrame()
result_by_models_df



# ### The Top 5 and Bottom 5 prompts of a model

# + magic_args="--save by_prompt_and_model" language="sql"
# select
#     model_configuration_id,
#     prompt_variation_id,
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate,
#     row_number() over (partition by model_configuration_id order by correct_rate desc) as rank
# from result_chn_prompt_renamed
# GROUP BY prompt_variation_id, model_configuration_id

# + magic_args="--save by_prompt_and_model_with_rank by_prompt_and_model_with_rank_df <<" language="sql"
# select *
# from by_prompt_and_model
# where
#    list_contains([1,2,3,4,5, 108, 107, 106, 105, 104], rank)
# order by model_configuration_id, rank
# -

by_prompt_and_model_with_rank_df = by_prompt_and_model_with_rank_df.DataFrame()

by_prompt_and_model_with_rank_df

by_prompt_and_model_with_rank_df.to_csv('./data/outputs/new_prompt_model_bottoms.csv')

# + magic_args="avg_model_correct_rate <<" language="sql"
# select model_configuration_id, mean(correct_rate)
# from by_prompt_and_model
# group by model_configuration_id
# order by model_configuration_id
# -
avg_model_correct_rate_df = avg_model_correct_rate.DataFrame()

avg_model_correct_rate_df






# ## Model, Prompt Family, Topic aggregations

# + magic_args="--save res_with_prompt_family" language="sql"
# select
#     r.*,
#     p.prompt_family
# from result_to_analyze r left join all_prompts p on r.prompt_variation_id = p.variation_id

# + magic_args="--save res_with_prompt_family_exclude_ind" language="sql"
# select * from res_with_prompt_family where score != 0
# -

# ### highest variance by model

# + magic_args="--save prompt_variance_stat" language="sql"
# select
#       model_configuration_id,
#       question_id,
#       stddev_pop(score) / mean (score) * 100 as variance,
#       -- count(DISTINCT score) as variance
#     from
#       res_with_prompt_family_exclude_ind
#     group by
#       model_configuration_id,
#       question_id
#     order by
#       "variance" desc

# + magic_args="--save prompt_variance_stat_2" language="sql"
# select 
#     model_configuration_id,
#     question_id,
#     variance,
#     rank() over (PARTITION by (model_configuration_id) order by variance desc) as rank
# from prompt_variance_stat

# + magic_args="high_variance_questions <<" language="sql"
# select * from prompt_variance_stat_2 where rank <= 10
# -

high_variance_questions_df = high_variance_questions.DataFrame()

high_variance_questions_df.to_csv('./data/outputs/new_high_variance_questions.csv', index=False)









# ### Model vs Prompt Family

# +
# I need to check the variance cause by Prompt Family for each Model.
# So I will first check the answer variance of each question, then get the average variance of all questions.

# + magic_args="--save model_prompt_stat1" language="sql"
# select
#       prompt_family,
#       model_configuration_id,
#       question_id,
#       count(*) as total_amount,
#       count(*) filter (score = 3) / total_amount * 100 as correct_rate,
#       stddev_pop(score) / mean (score) * 100 as variance,
#       -- count(DISTINCT score) as variance
#       mode(score) as mode_score
#     from
#       res_with_prompt_family_exclude_ind
#     group by
#       prompt_family,
#       model_configuration_id,
#       question_id
#     order by
#       "correct_rate" desc
# + magic_args="--save model_prompt_stat2" language="sql"
# select
#       r.prompt_family,
#       r.model_configuration_id,
#       r.question_id,
#       (1 - count(*) filter (r.score = s1.mode_score) / count(*)) * 100 as variance_2
#       -- count(*)
#     from
#       res_with_prompt_family_exclude_ind r
#     left join model_prompt_stat1 s1
#     on
#       r.prompt_family = s1.prompt_family AND
#       r.model_configuration_id = s1.model_configuration_id AND
#       r.question_id = s1.question_id
#     group by
#       r.prompt_family,
#       r.model_configuration_id,
#       r.question_id

# + magic_args="--save model_prompt_stat3" language="sql"
# select
#       prompt_family,
#       model_configuration_id,
#       question_id,
#       count(*) as total_amount,
#       count(*) filter (score = 0) / total_amount * 100 as indecisive_rate
#     from
#       res_with_prompt_family
#     group by
#       prompt_family,
#       model_configuration_id,
#       question_id

# + magic_args="model_prompt_stats <<" language="sql"
# select
#   r1.prompt_family,
#   r1.model_configuration_id,
#   mean (correct_rate) as cr,
#   mean (indecisive_rate) as ir,
#   mean (variance) as variance
# from
#   model_prompt_stat1 r1
#   left join model_prompt_stat2 r2 on r1.prompt_family = r2.prompt_family
#       and r1.model_configuration_id = r2.model_configuration_id
#       and r1.question_id = r2.question_id
#   left join model_prompt_stat3 r3 on r1.prompt_family = r3.prompt_family
#       and r1.model_configuration_id = r3.model_configuration_id
#       and r1.question_id = r3.question_id
# group by
#   r1.prompt_family,
#   r1.model_configuration_id
# order by
#   r1.model_configuration_id,
#   r1.prompt_family
#
# -

tmp_df1 = model_prompt_stats.DataFrame()

tmp_df1.set_index(['prompt_family', 'model_configuration_id'])

tmp_df1.to_csv('./data/outputs/new_model_vs_prompt_family.csv', index=False)





# ### Model vs Topic
# Same as above, need to calculate variance per question first and get the average.

# + magic_args="--save model_question_stat1" language="sql"
# select
#     question_id,
#     model_configuration_id,
#     count(*) filter (
#       score = 3
#     ) / count(*) * 100 as correct_rate,
#     stddev_pop(score) / mean(score) * 100 as variance
#     -- count(DISTINCT score) as variance
#   from
#     (select * from result_to_analyze where score != 0)
#   group by
#     question_id,
#     model_configuration_id

# + magic_args="--save model_question_stat2" language="sql"
#   select
#     question_id,
#     model_configuration_id,
#     count(*) filter (
#       score = 0
#     ) / count(*) * 100 as indecisive_rate
#   from
#     result_to_analyze
#   group by
#     question_id,
#     model_configuration_id

# + magic_args="--save model_question_stat_all" language="sql"
# select
#     r1.*,
#     r2.indecisive_rate
#   from
#     model_question_stat1 r1
#   left join model_question_stat2 r2 on
#     r1.question_id = r2.question_id
#     and r1.model_configuration_id = r2.model_configuration_id

# + magic_args="--save model_topic_stat" language="sql"
#   select
#     r.*,
#     q.sdg_topic,
#     q.other_topics,
#     q.human_wrong_percentage,
#     case
#       when q.sdg_topic is null then other_topics
#       else list_append(q.other_topics, q.sdg_topic)
#     end as all_topics
#
#   from
#     model_question_stat_all r
#   left join q_and_t q on
#     r.question_id = q.question_id

# + magic_args="--with model_topic_stat model_topic_res <<" language="sql"
# select
#   model_configuration_id,
#   topic,
#   count(*) as "number of qs",
#   mean (correct_rate) as correct_rate,
#   mean (indecisive_rate) as indecisive_rate,
#   mode (variance) as variance
# from
#   (
#     select
#       * exclude (all_topics, sdg_topic, other_topics),
#       unnest (all_topics) as topic
#     from
#       model_topic_stat
#   )
# group by
#   topic,
#   model_configuration_id
# order by
#   topic,
#   model_configuration_id
# -

model_topic_res_df = model_topic_res.DataFrame().set_index(['model_configuration_id', 'topic'])

model_topic_res_df.to_csv('./data/outputs/new_model_vs_topic.csv')

model_topic_res_df.describe()







# ## Questions where AI worse than human and monkey

# ### human score

100 - all_questions['wrongPercentage'].mean()



# + language="sql"
# select * from model_topic_stat;

# + magic_args="model_topic_diff <<" language="sql"
# select
#   question_id,
#   model_configuration_id,
#     (100 - correct_rate) as ai_wrong_percentage,
#     human_wrong_percentage,
#     2/3 * 100 as monkey_wrong_percentage,
#   ai_wrong_percentage - human_wrong_percentage as compare_to_human,
#     ai_wrong_percentage - monkey_wrong_percentage as compare_to_monkey,
#     sdg_topic,
#     other_topics
# from model_topic_stat
# where compare_to_human > 0 OR compare_to_monkey > 0
# order by
#     "sdg_topic",
#     cast(other_topics as varchar),
#     "model_configuration_id"
# -

model_topic_diff

model_topic_diff_df = model_topic_diff.DataFrame()

model_topic_diff_df.shape

model_topic_diff_df.to_csv('./data/outputs/new_ai_worse_all.csv', index=False)



# +
# make a complete list combining worse than human and worse than monkey

# + magic_args="all_worse_questions <<" language="sql"
# select question_id, model_configuration_id 
# from
#     model_topic_diff_df

# + magic_args="very_wrong_res <<" language="sql"
# select * from result_to_analyze where result = 'very_wrong'
# -



# +
# now find one case for very wrong for these questions.
# -

r1 = all_worse_questions.DataFrame()
r2 = very_wrong_res.DataFrame()

r2_ = r2.groupby(['question_id', 'model_configuration_id']).agg(lambda x: x.sample(1)).reset_index()

# + magic_args="--save all_worse_very_wrong" language="sql"
# select 
#     r1.question_id, r1.model_configuration_id, prompt_variation_id
# from 
#      r1 
#     left join 
#      r2_ 
#     on 
#         r1.question_id = r2_.question_id and r1.model_configuration_id = r2_.model_configuration_id

# + language="sql"
# select *
# from r1
# where 
#     question_id = '1640' and model_configuration_id = 'mc039'

# + language="sql"
# select *
# from r2_
# where 
#     question_id = '1640' and model_configuration_id = 'mc039'

# +
# Why??? Because there is no very wrong answer for this combination!
# -



# all_worse_very_wrong_df = %sql select * from all_worse_very_wrong

all_worse_very_wrong_df = all_worse_very_wrong_df.DataFrame()

all_worse_very_wrong_df[pd.isnull(all_worse_very_wrong_df['prompt_variation_id'])]





# +
# query example responses
# but first, we need to read all result data...
# -

# FIXME: change ../output/results.parquet to correct archive path.
raw_data_fs = [
    '../output/results.parquet',  # for mc039
    '../output/archives/20240521/results.xlsx',
    '../output/archives/20240401/results.xlsx',
    '../output/archives/20240501/results.xlsx',
    '../output/archives/20240516/results.xlsx',
    '../output/archives/20240601/results.xlsx',
    '../output/archives/20240910/results.xlsx'
]

pd.read_parquet(raw_data_fs[0]).columns

# +
cols = ['experiment_date', 'question_id', 'model_id', 'prompt_template', 'question', 'raw_output']

raw_data_lst = list()

for x in raw_data_fs:
    if 'parquet' in x:
        raw_data_lst.append(pd.read_parquet(x)[cols])
    else:
        raw_data_lst.append(pd.read_excel(x)[cols])
# -

raw_data = pd.concat(raw_data_lst, ignore_index=True)

raw_data

# fix a few experiment model id
raw_data.loc[raw_data['model_id'] == 'gpt-4', 'model_id'] = 'gpt-4-0613' 
raw_data.loc[raw_data['model_id'] == 'gpt-4o', 'model_id'] = 'gpt-4o-2024-05-13' 





# +
# now we should make all columns we needed
# 1. question and answers
# 2. prompt template
# 3. model configuration id
# -

# first do prompt template
# load all configuration files and get a mapping.
import yaml

sorted([str(x) for x in raw_data['experiment_date'].unique()])

configuration_list = [
    '../experiment_configurations/experiment_202403291214_gpt-4-0125-preview_en-US.yaml',
    '../experiment_configurations/experiment_202403291248_gemini_gemini-1-0-pro_en-US.yaml',
    '../experiment_configurations/experiment_202403291536_gemini_gemini-1-0-pro_en-US.yaml',
    '../experiment_configurations/experiment_202404011622_qwen-max-1201_zh-CN.yaml',
    '../experiment_configurations/experiment_202404051719_gpt-4-0125-preview_en-US.yaml',
    '../experiment_configurations/experiment_202404102325_qwen-max-1201_zh-CN.yaml',
    '../experiment_configurations/experiment_202404201136_vertex_ai_gemini-1-5-pro_en-US.yaml',
    '../experiment_configurations/experiment_202404201344_vertex_ai_gemini-1-5-pro-preview-0409_en-US.yaml',
    '../experiment_configurations/experiment_202405012311_qwen-max-0403_zh-CN.yaml',
    '../experiment_configurations/experiment_202405162215_vertex_ai_gemini-1-5-pro-preview-0409_en-US.yaml',
    '../experiment_configurations/experiment_202405162248_qwen-max-0403_zh-CN.yaml',
    '../experiment_configurations/experiment_202405162244_qwen-max-0403_zh-CN.yaml',
    '../experiment_configurations/experiment_202405242125_gpt-4o-2024-05-13_en-US.yaml',
    '../experiment_configurations/experiment_202405281300_replicate_meta_meta-llama-3-70b-instruct_en-US.yaml',
    '../experiment_configurations/experiment_202405291053_vertex_ai_claude-3-opus@20240229_en-US.yaml',
    '../experiment_configurations/experiment_202406040141_qwen-max-0428_en-US.yaml',
    '../experiment_configurations/experiment_202408291204_gpt-4o-2024-08-06_en-US.yaml',
    '../experiment_configurations/experiment_202408310828_vertex_ai_claude-3-5-sonnet@20240620_en-US.yaml',
    '../experiment_configurations/experiment_202409102304_fireworks_ai_accounts_fireworks_models_llama-v3p1-405b-instruct_en-US.yaml',
    '../experiment_configurations/experiment_202409211350_qwen-max-2024-09-19_en-US.yaml',
]

# +
prompt_template_list = list()

for x in configuration_list:
    c = yaml.safe_load(open(x, 'r'))
    p = pd.DataFrame.from_records(c['variations'][1]['variations'])
    prompt_template_list.append(p)
# -

all_prompt_templates = pd.concat(prompt_template_list, ignore_index=True)

all_prompt_templates = all_prompt_templates.drop_duplicates(subset=['value'])

all_prompt_templates_mapping = all_prompt_templates.set_index('value')['variation_id'].to_dict()

for k, v in all_prompt_templates_mapping.items():
    print(k)
    print(v)
    break



raw_data['prompt_template'].map(all_prompt_templates_mapping).hasnans  # should be False

raw_data['prompt_variation_id'] = raw_data['prompt_template'].map(all_prompt_templates_mapping)



# +
# next add model_configuration_id
# -

# all_models_ = %sql select * from all_models where repeat_times = 1

all_models_ = all_models_.DataFrame()

all_models_mapping = all_models_.set_index('model_id')['model_config_id'].to_dict()

raw_data['model_id'].map(all_models_mapping).hasnans

raw_data['model_configuration_id'] = raw_data['model_id'].map(all_models_mapping)

raw_data



# + language="sql"
# select
#     DISTINCT model_id 
# from 
#     raw_data
# where
#     prompt_variation_id like '%zh%'
# -









# +
# questions and answers mapping
# -

all_questions.columns

qs = ai_eval_sheet.questions.data.df.copy()
qs = qs[['question_id', 'language', 'published_version_of_question']]

qs

q_dict = qs.set_index(["question_id", "language"])["published_version_of_question"].to_dict()

# +
ans = ai_eval_sheet.question_options.data.df.copy()
ans_dict = dict()

for qid, adf in ans.groupby(["question_id", "language"]):
    adict = adf.set_index('letter')['question_option'].to_dict()
    ans_dict[qid] = adict
# -

ans_dict[("1", "en-US")]

q_dict[("1", "en-US")]



# +
# create final output
# -

all_worse_very_wrong_df

raw_data.dtypes

raw_data['experiment_date'] = raw_data['experiment_date'].map(lambda x: str(x))
raw_data['question_id'] = raw_data['question_id'].map(lambda x: str(x))
raw_data['model_id'] = raw_data['model_id'].map(lambda x: str(x))

raw_data_pl = pl.from_pandas(raw_data)

# +
raw_output_lst = list()
prompt_lst = list()


for _, row in all_worse_very_wrong_df.iterrows():
    question_id = row['question_id']
    model_configuration_id = row['model_configuration_id']
    prompt_variation_id = row['prompt_variation_id']
    # print(question_id, model_configuration_id, prompt_variation_id)

    raw_data_row = raw_data_pl.filter(
        (pl.col('question_id') == question_id) & (pl.col('model_configuration_id') == model_configuration_id) & (pl.col('prompt_variation_id') == prompt_variation_id)
    )

    if raw_data_row.is_empty():
        raw_output_lst.append(None)
        prompt_lst.append(None)
    else:
        question_text = raw_data_row['question'].item()
        question_id = raw_data_row['question_id'].item()
        language = 'zh-CN' if '_zh' in prompt_variation_id else 'en-US'
        answers = ans_dict[(question_id, language)]
        option_a = answers['A']
        option_b = answers['B']
        option_c = answers['C']

        prompt_template = raw_data_row['prompt_template'].item()
        prompt = prompt_template.format(question_text=question_text, option_a=option_a, option_b=option_b, option_c=option_c)
        # print(prompt)

        prompt_lst.append(prompt)
        raw_output_lst.append(raw_data_row['raw_output'].item())
    
# -
raw_data_row

all_worse_very_wrong_df['prompt'] = prompt_lst
all_worse_very_wrong_df['model_output'] = raw_output_lst

all_worse_very_wrong_df

all_worse_very_wrong_df.to_csv('./data/outputs/new_ai_worse_sample.csv', index=False)







# ## Examples for high variance questions

high_variance_questions_df

# + language="sql"
# select * from result_to_analyze
# -



question_id = '1792'
model_configuration_id = 'mc039'
grade = 'very_wrong'


# + magic_args="--save grade_example" language="sql"
#
# select * from
#     (
#     select * from result_to_analyze
#     where
#         question_id = '{{question_id}}' 
#         and model_configuration_id = '{{model_configuration_id}}' 
#         and result = '{{grade}}'
#     )
# using sample 1
# -

def filter_grade(question_id, model_configuration_id, grade):
    # res = %sql select * from (select * from result_to_analyze where question_id = '{{question_id}}' and model_configuration_id = '{{model_configuration_id}}' and result = '{{grade}}') using sample 1
    return res


filter_grade(question_id, model_configuration_id, grade)





# +
correct_lst = list()
wrong_lst = list()
very_wrong_lst = list()
correct_prompt_lst = list()
wrong_prompt_lst = list()
very_wrong_prompt_lst = list()

output_lists = [correct_lst, wrong_lst, very_wrong_lst]
prompt_lists = [correct_prompt_lst, wrong_prompt_lst, very_wrong_prompt_lst]

for _, row in high_variance_questions_df.iterrows():
    question_id = row['question_id']
    model_configuration_id = row['model_configuration_id']
    # prompt_variation_id = row['prompt_variation_id']
    # print(question_id, model_configuration_id)

    examples = list()
    for g in ['correct', 'wrong', 'very_wrong']:
        grade = g
        example = filter_grade(question_id, model_configuration_id, grade)
        # print(example)
        if len(example) > 0:
            e = next(example.dicts())
            assert e['result'] == grade
            examples.append(e)
        else:
            examples.append(None)

    for i, e in enumerate(examples):
        if e:
            prompt_variation_id = e['prompt_variation_id']
            raw_data_row = raw_data_pl.filter(
                (pl.col('question_id') == question_id) 
                & (pl.col('model_configuration_id') == model_configuration_id) 
                & (pl.col('prompt_variation_id') == prompt_variation_id)
            )
            if raw_data_row.is_empty():
                print(question_id, model_configuration_id, prompt_variation_id)
                output_lists[i].append(None)
                prompt_lists[i].append(None)
                continue
            question_text = raw_data_row['question'].item()
            language = 'zh-CN' if '_zh' in prompt_variation_id else 'en-US'
            answers = ans_dict[(question_id, language)]
            option_a = answers['A']
            option_b = answers['B']
            option_c = answers['C']
            prompt_template = raw_data_row['prompt_template'].item()
            prompt = prompt_template.format(question_text=question_text, option_a=option_a, option_b=option_b, option_c=option_c)
            output_lists[i].append(raw_data_row['raw_output'].item())
            prompt_lists[i].append(prompt)
        else:
            output_lists[i].append(None)
            prompt_lists[i].append(None)

# -
prompt_lists[0][0]

prompt_lists[1][0]







high_variance_questions_df['correct_prompt_example'] = prompt_lists[0]
high_variance_questions_df['correct_answer_example'] = output_lists[0]
high_variance_questions_df['wrong_prompt_example'] = prompt_lists[1]
high_variance_questions_df['wrong_answer_example'] = output_lists[1]
high_variance_questions_df['very_wrong_prompt_example'] = prompt_lists[2]
high_variance_questions_df['very_wrong_answer_example'] = output_lists[2]

high_variance_questions_df

high_variance_questions_df.to_csv('./data/outputs/new_high_variance_questions_sample.csv', index=False)





# ## Questions where AI scores best

# + magic_args="ai_best_questions <<" language="sql"
# select 
#     question_id,
#     mean(correct_rate) as avg_correct_rate,
#     mean(indecisive_rate) as avg_inde_rate,
#     mean(variance) as avg_variance,
# from model_topic_stat
# group by question_id
# order by avg_correct_rate desc, avg_inde_rate
# ;
# -

ai_best_questions_df = ai_best_questions.DataFrame()

ai_best_questions_df.head(15)





# # for double checking the evaluators
# check the top 10, bottom 10 questions per model

# + magic_args="--save double_check_results" language="sql"
# select
#   question_id,
#   model_configuration_id,
#     (100 - correct_rate) as ai_wrong_percentage,
#     human_wrong_percentage,
#   ai_wrong_percentage - human_wrong_percentage as diff,
#     sdg_topic,
#     other_topics
# from model_topic_stat
# -- where diff > 0
# order by
#     "sdg_topic",
#     cast(other_topics as varchar),
#     "model_configuration_id"

# + language="sql"
# select * 
# from double_check_results 
# where model_configuration_id = 'mc026' AND ai_wrong_percentage = 0
# order by question_id

# + magic_args="--save double_check_results_1" language="sql"
# select
#     model_configuration_id,
#     question_id,
#     ai_wrong_percentage,
#     rank() over (partition by model_configuration_id order by ai_wrong_percentage) as rank
# from double_check_results
# order by model_configuration_id, rank, question_id

# + magic_args="to_check <<" language="sql"
#
# select * from double_check_results_1 where rank <= 10 OR rank >= 275
# -

to_check_df = to_check.DataFrame()

to_check_df[to_check_df['model_configuration_id'] == 'mc026']







# # for climate study questions

climate_questions = ["5", "59", "85", "86", "1524", "1672", "1691", "1706", "1717", "1730", "1731", "1737", "1738", "1741", "1761"]

# + magic_args="--save result_climate_questions" language="sql"
# select
#     *
# from result_to_analyze
# where list_contains({{climate_questions}}, question_id) AND model_configuration_id != 'mc028';
# -

# climate_raw_result = %sql select * from result_climate_questions

climate_raw_result.DataFrame().to_csv('./data/outputs/climate_raw.csv', index=False)

# + magic_args="--save correct_by_prompt climate_res << " language="sql"
# select
#     model_configuration_id,
#     prompt_variation_id,
#     count(*),
#
# from result_climate_questions
# where result = 'correct'
# group by model_configuration_id, prompt_variation_id
# -

climate_res.DataFrame().to_csv("./data/outputs/climate_study.csv")

# +
# another way to calculate correctness

# + magic_args="--save climate_question_correctness" language="sql"
# select
#     model_configuration_id,
#     count(*) filter (result != 'fail') as total_count,
#     count(*) filter (result = 'correct') as correct_count,
#     correct_count / total_count * 100 as correct_rate,
#     correct_rate * 15 / 100 as correct_num_average
# from result_climate_questions
# group by model_configuration_id

# + language="sql"
# select mean(correct_num_average) from climate_question_correctness;
# -



# + magic_args="--save climate_question_correctness" language="sql"
# select
#     count(*) filter (result != 'fail') as total_count,
#     count(*) filter (result = 'correct') as correct_count,
#     correct_count / total_count * 100 as correct_rate,
#     correct_rate * 15 / 100 as correct_num_average
# from result_climate_questions
# -

34/3







# # Check raw outputs

outputs1 = pd.read_excel('../output/archives/20240401/results.xlsx')
outputs2 = pd.read_excel('../output/results.xlsx')

outputs = pd.concat([outputs1, outputs2], ignore_index=True)

outputs



outputs.to_parquet("./data/outputs/latest_results.parquet")



# alibaba = %sql select * from outputs where model_id = 'qwen-max-0403'
# err = %sql select * from outputs where model_id = 'qwen-max-0403' and raw_output like '%Error%'

err.DataFrame().head(10)

# +
# Issue: Seems the gpt 4 evaluator grades some Error and indecisive answers as "correct"..
# -



err.DataFrame().shape

alibaba.DataFrame().shape

60 / 30348  # still have 0.1% of API Error

# + magic_args="err2 <<" language="sql"
# select * from outputs where model_id = 'qwen-max-0403' and
#  (raw_output like '%抱歉%'
#     OR raw_output like '%遗憾%'
#     OR raw_output like '%对不起%'
#     OR raw_output like '%无法%')  -- these are answers including the word "Sorry" or "I can't"
# -

err2.DataFrame()

err2.DataFrame().shape
