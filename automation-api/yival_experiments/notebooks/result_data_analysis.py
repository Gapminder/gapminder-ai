# # Result Data Analysis
#
# This notebook is for producing tables listed in https://docs.google.com/spreadsheets/d/1ln5ui3f13AfAQkBuEMbNomBXlZLhkQPYVEpBlZjUtu0/edit?pli=1#gid=0
#
# Results are from the experiments in Apr and May 2023

# going to use duckdb
# %load_ext sql

# %sql duckdb://

import pandas as pd
from lib.pilot.helpers import read_ai_eval_spreadsheet, get_questions, get_model_configs, get_prompt_variants
from lib.config import read_config
import matplotlib.pyplot as plt
import seaborn as sns

# load env
config = read_config()



# ## prepare data

# results to be analyzed
# manually download from AI eval spreadsheet.
result = pd.read_csv('./data/Gapminder AI evaluations - Master Output.csv')

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
# from result where model_configuration_id not like 'mc026'

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
#   filter (topic_list, (x -> contains (x, 'sdg'))) [1] AS sdg_topic,
#   filter (
#     topic_list,
#     (
#       x -> list_contains (
#         main.list_value (
#           'refugees',
#           'population',
#           'sustainable-development-misconception-study-2020',
#           '2017_gapminder_test',
#           'climate-misconception-study-2024'
#         ),
#         x
#       )
#     )
#   ) AS other_topics
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

# + magic_args="--save q_and_t" language="sql"
# -- only keep question id and topic list.
# select
#     question_id,
#     first(human_wrong_percentage) as human_wrong_percentage,
#     first(topic_list) as topic_list,
#     first(sdg_topic) as sdg_topic,
#     first(other_topics) as other_topics
# from questions_and_topics
# group by question_id
# -









# ## Experiment Total

# + language="sql"
# select
#     'AI' as name,
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from result_to_analyze
# -



# ## Break down by Model

# + language="sql"
# select
#     m.model_id as model_id,
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from result_to_analyze r left join all_models m on r.model_configuration_id = m.model_config_id
# GROUP BY m.model_id
# -



# ## break down by prompt and prompt family

# + magic_args="by_prompt_family <<" language="sql"
# select
#     p.prompt_family as prompt_family,
#     count(DISTINCT p.variation_id) / 2 as number_of_prompts,  -- treat chinese prompt and english prompt the same.
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from result_to_analyze r left join all_prompts p on r.prompt_variation_id = p.variation_id
# GROUP BY p.prompt_family
# ORDER BY correct_rate desc
# -

by_prompt_family.DataFrame().set_index('prompt_family')

# + magic_args="by_prompt <<" language="sql"
# select
#     any_value(p.prompt_family) as prompt_family,
#     prompt_variation_id,
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from result_chn_prompt_renamed r left join all_prompts p on r.prompt_variation_id = p.variation_id
# GROUP BY r.prompt_variation_id
# ORDER BY correct_rate desc
# -

by_prompt.DataFrame().to_csv('./data/outputs/new_total_by_prompts.csv', index=False)





# ## break down by topics

# + magic_args="by_topics_1 <<" language="sql"
# select
#     q.sdg_topic as sdg_topic,
#     count(DISTINCT q.question_id) as number_of_questions,  -- treat chinese prompt and english prompt the same.
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from result_to_analyze r left join q_and_t q on r.question_id = q.question_id
# GROUP BY q.sdg_topic
# ORDER BY sdg_topic
# -

by_topics_1.DataFrame().set_index('sdg_topic')

# +
# other topics

# + magic_args="--save res_with_other_topics" language="sql"
# select
#     r.*,
#     unnest(q.other_topics) as topic
# from result_to_analyze r left join q_and_t q on r.question_id = q.question_id
# -



# + magic_args="--with res_with_other_topics by_topics_2 <<" language="sql"
# select
#     topic,
#     count(DISTINCT question_id) as number_of_questions,  -- treat chinese prompt and english prompt the same.
#     count(*) as total_count,
#     count(*) filter (result != 'fail') as total_count_exclude_indecisive,
#     count(*) filter (result = 'correct') / total_count_exclude_indecisive * 100 as correct_rate,
#     100 - correct_rate as wrong_rate,
#     count(*) filter (result = 'fail') / total_count * 100 as indecisive_rate
# from res_with_other_topics
# GROUP BY topic
# ORDER BY topic
# -

by_topics_2.DataFrame().set_index('topic')





# ## Model vs Prompt Family

# +
# I need to check the variance cause by Prompt Family for each Model.
# So I will first check the answer variance of each question, then get the average variance of all questions.

# + magic_args="--save res_with_prompt_family" language="sql"
# select
#     r.*,
#     p.prompt_family
# from result_to_analyze r left join all_prompts p on r.prompt_variation_id = p.variation_id

# + magic_args="--save res_with_prompt_family_exclude_ind" language="sql"
# select * from res_with_prompt_family where score != 0

# + magic_args="--save model_prompt_stat1" language="sql"
# select
#       prompt_family,
#       model_configuration_id,
#       question_id,
#       count(*) as total_amount,
#       count(*) filter (score = 3) / total_amount * 100 as correct_rate,
#       -- stddev_pop(score) / mean (score) * 100 as variance
#       count(DISTINCT score) as variance
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
#   r2.prompt_family,
#   r2.model_configuration_id,
#   mean (correct_rate) as cr,
#   mean (indecisive_rate) as ir,
#   mode (variance) as variance
# from
#   model_prompt_stat1 r2
#   left join model_prompt_stat2 r3 on r2.prompt_family = r3.prompt_family
#   and r2.model_configuration_id = r3.model_configuration_id
#   and r2.question_id = r3.question_id
# group by
#   r2.prompt_family,
#   r2.model_configuration_id
# order by
#   r2.model_configuration_id,
#   r2.prompt_family
#
# -

tmp_df1 = model_prompt_stats.DataFrame().set_index(['prompt_family', 'model_configuration_id'])

tmp_df1

tmp_df1.describe()



# ## Model vs Topic
# Same as above, need to calculate variance per question first and get the average.

# + magic_args="--save model_question_stat1" language="sql"
# select
#     question_id,
#     model_configuration_id,
#     count(*) filter (
#       score = 3
#     ) / count(*) * 100 as correct_rate,
#     -- stddev_pop(score) / mean(score) * 100 as variance
#     count(DISTINCT score) as variance
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





# ## Topic vs Prompt Family

# +
# we will reuse the res_with_prompt_family_exclude_ind and res_with_prompt_family queries defined above.

# + magic_args="--save question_prompt_family_stat1" language="sql"
#     select
#       question_id,
#       prompt_family,
#       count(*) filter (score = 3) / count(*) * 100 as correct_rate,
#       -- stddev_pop(score) / mean (score) * 100 as variance
#       count(DISTINCT score) as variance
#     from
#       res_with_prompt_family_exclude_ind
#     group by
#       question_id,
#       prompt_family

# + magic_args="--save question_prompt_family_stat2" language="sql"
#     select
#       question_id,
#       prompt_family,
#       count(*) filter (score = 1) / count(*) * 100 as indecisive_rate
#     from
#       res_with_prompt_family
#     group by
#       question_id,
#       prompt_family
# -



# + magic_args="--save question_prompt_family_stat_all" language="sql"
#     select
#       r1.question_id,
#       r1.prompt_family,
#       mean (correct_rate) as correct_rate,
#       mean (indecisive_rate) as indecisive_rate,
#       mode (variance) as variance
#     from
#       question_prompt_family_stat1 r1
#       left join question_prompt_family_stat2 r2 on r1.question_id = r2.question_id
#       and r1.prompt_family = r2.prompt_family
#     group by
#       r1.question_id,
#       r1.prompt_family

# + magic_args="--save topic_prompt_family_stat" language="sql"
#     select
#       r.*,
#       q.sdg_topic,
#       q.other_topics,
#       case
#         when q.sdg_topic is null then other_topics
#         else list_append (q.other_topics, q.sdg_topic)
#       end as all_topics
#     from
#       question_prompt_family_stat_all r
#       left join q_and_t q on r.question_id = q.question_id

# + magic_args="--with topic_prompt_family_stat topic_prompt_family_res <<" language="sql"
# select
#   topic,
#   -- count(*) as "number of qs",
#   prompt_family,
#   mean (correct_rate) as correct_rate,
#   mean (indecisive_rate) as indecisive_rate,
#   median (variance) as variance
# from
#   (select
#     * exclude (all_topics, sdg_topic, other_topics),
#     unnest(all_topics) as topic
#    from topic_prompt_family_stat)
# group by
#   topic,
#   prompt_family
# order by
#   topic,
#   prompt_family
# -

topic_prompt_family_df = topic_prompt_family_res.DataFrame().set_index(['topic', 'prompt_family'])

topic_prompt_family_df.to_csv('./data/outputs/new_topic_vs_prompt.csv')

topic_prompt_family_df.describe()



# ## Questions where AI worse than human and monkey

# + language="sql"
# select * from model_topic_stat;

# + magic_args="model_topic_human_diff <<" language="sql"
# select
#   question_id,
#   model_configuration_id,
#     (100 - correct_rate) as ai_wrong_percentage,
#     human_wrong_percentage,
#   ai_wrong_percentage - human_wrong_percentage as diff,
#     sdg_topic,
#     other_topics
# from model_topic_stat
# where diff > 0
# order by
#     "sdg_topic",
#     cast(other_topics as varchar),
#     "model_configuration_id"
# -

model_topic_human_diff_df = model_topic_human_diff.DataFrame()

model_topic_human_diff_df.to_csv('./data/outputs/new_ai_worse_human.csv', index=False)





# + magic_args="model_topic_monkey_diff <<" language="sql"
# select
#   question_id,
#   model_configuration_id,
#     (100 - correct_rate) as ai_wrong_percentage,
#     100 * (2/3) as monkey_wrong_percentage,
#   ai_wrong_percentage - monkey_wrong_percentage as diff,
#     sdg_topic,
#     other_topics
# from model_topic_stat
# where diff > 0
# order by
#     "sdg_topic",
#     cast(other_topics as varchar),
#     "model_configuration_id"
# -

model_topic_monkey_diff_df = model_topic_monkey_diff.DataFrame()

model_topic_monkey_diff_df.to_csv('./data/outputs/new_ai_worse_monkey.csv', index=False)





# +
# summary stats for human and monkey vs ai

# + magic_args="summary_human_ai <<" language="sql"
# select
#     question_id,
#     count(*) as num_of_models,
#     mean(diff) as average_diff,
# from
#     model_topic_human_diff_df
# group by
#     question_id
# ORDER BY
#     num_of_models desc,
#     average_diff desc
# -

summary_human_ai.DataFrame()

summary_human_ai.DataFrame().to_csv('./data/outputs/new_summary_human_ai.csv')



# + magic_args="summary_monkey_ai <<" language="sql"
# select
#     question_id,
#     count(*) as num_of_models,
#     mean(diff) as average_diff,
# from
#     model_topic_monkey_diff_df
# group by
#     question_id
# ORDER BY
#     num_of_models desc,
#     average_diff desc
# -

summary_monkey_ai.DataFrame().to_csv('./data/outputs/new_summary_monkey_ai.csv')





# ## Question vs Prompt Family

# + magic_args="question_prompt_family_stat << " language="sql"
# select * from question_prompt_family_stat_all
# -

question_prompt_family_stat_df = question_prompt_family_stat.DataFrame()

question_prompt_family_stat_df.to_csv('./data/outputs/new_question_prompt_family_stat.csv')





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
