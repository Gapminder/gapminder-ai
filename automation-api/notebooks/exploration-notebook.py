# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: gapminder-ai-automation-api
#     language: python
#     name: gapminder-ai-automation-api
# ---

# Makes edits in the included files available without restarting the kernel
# %reload_ext autoreload
# %autoreload 2

# +
# Required to see logging messages when executing the notebook
import logging
from lib.app_singleton import AppSingleton

app_logger = AppSingleton().get_logger()
app_logger.setLevel(logging.DEBUG)
app_logger.debug("test")
# -

import pandas as pd
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_colwidth', 1000)

# ## Authorize using service account

from lib.authorized_clients import get_service_account_authorized_clients
authorized_clients = get_service_account_authorized_clients()

from lib.config import read_config
config = read_config()

# ## Run models via LangChain

# Test openai model
from lib.llms.utils import get_openai_model, run_model

# +
# If you have set the openai api key and org in .env, then the function will read the them from the .env file
llm = get_openai_model('gpt-3.5-turbo', temperature=0.1)
# you can also provide the api key and org in the function. as shown below:
# llm = get_openai_model('gpt-3.5-turbo', openai_api_key="sk-your_key", openai_organization="your-org", tempernature=0.1)

# then you can run the model:
template = "What are the top {k} resources to learn {this} in 2023?"
print(run_model(llm, template, verbose=True, k=3, this="python"))
# -

# There are more vendors supported in this lib. For example Google PaLM.
from lib.llms.utils import get_google_palm_model, run_model

# +
# Again, if you have set the google api key in .env, then the function will read the them from the .env file
llm = get_google_palm_model('text-bison', temperature=0.1)
# you can also provide the api key in the function. as shown below:
# llm = get_google_palm_model('text-bison', google_api_key="your_key", tempernature=0.1)

# then you can run the model:
template = "Please search Google and summarize: What are the top {k} resources to learn {this} in 2023?"
print(run_model(llm, template, verbose=True, k=3, this="python"))

# +
# more functions to explore:
# - get_huggingface_model  # get model from Huggingface
# - get_dummy_model  # Just a Fake LLM
# - get_iflytek_model  # iFlyTek Spark
# -


# ## Read from AI Eval spreadsheet


# +
from lib.ai_eval_spreadsheet.wrapper import (
    get_ai_eval_spreadsheet,
    read_ai_eval_data,
)
from pandera.errors import SchemaErrors, SchemaError

ai_eval_spreadsheet_id = config["AI_EVAL_DEV_SPREADSHEET_ID"]
ai_eval_spreadsheet = get_ai_eval_spreadsheet(
    authorized_clients, ai_eval_spreadsheet_id
)

try:
    ai_eval_data = read_ai_eval_data(ai_eval_spreadsheet)
    display(ai_eval_data)
except SchemaError as err:
    print("DataFrame validation failed. Errors:", err.check)
    print("Schema:")
    display(err.schema)
    print("Failure cases:")
    display(err.failure_cases)  # dataframe of schema errors
    print("Original data:")
    display(err.data)  # invalid dataframe
# -

ai_eval_data.questions.data.df

ai_eval_data.question_options.data.df

ai_eval_data.prompt_variations.data.df

ai_eval_data.gen_ai_models.data.df


# ## Test individual question and prompt
# Here is how you can ask one question to llm

# read the ai eval spreadsheet
ai_eval_data = read_ai_eval_data(ai_eval_spreadsheet)

# there are some helper functions to parse the spreadsheet
from lib.pilot.helpers import get_questions, get_prompt_variants, create_question_data_for_test

# load all questions and filter by language
qs = get_questions(ai_eval_data, include_all=True, language='en-US')

# define a function to load one question
def get_question(qid, qs):
    if isinstance(qid, int):
        qid = str(qid)
    for q, opts in qs:
        if q.question_id == qid:
            return (q, opts)


q = get_question("10", qs)

q

# load all prompt variants
prompts = get_prompt_variants(ai_eval_data, include_all=True)
prompts

# define a function to load one prompt
def get_prompt_variant(pid, ps):
    for p in ps:
        if pid == p.variation_id:
            return p


pv = get_prompt_variant("simple", prompts)
pv

# There are many fields in PromptVariant objects
# - pv.question_template: how to format the question.
#   Expect `question`, `option_a`, `option_b`, `option_c` as input.
# - pv.question_prompt_template: how to format the prompt to input into LLM.
#   Expect `question` as input (which formatted according to the above template)
# - pv.ai_prefix and pv.question_prefix are for memory, which will be the prefixes
#   for question messages and llm response prefix.
# - pv.follow_up_answer_correctness_evaluation_prompt_template: the template to
#   format a followup question to double check the answer.
#   Expect `question`, `option_a`, `option_b`, `option_c`, `text` as input.

# to run a model with given prompt and question:

# format the question with question template
qd = create_question_data_for_test(pv.question_template, q)  # return a dict
print(qd['question'])

# get llm and run model
llm = get_openai_model('gpt-3.5-turbo', temperature=0.1)
answer = run_model(llm, pv.question_prompt_template, verbose=True, **qd)
print(answer)

# if the llm is good at following instructions and produce answers in the format we want
# we can check the answer with this function
from lib.pilot.helpers import simple_evaluation

simple_evaluation(q, answer)

# +
# otherwise, we can use another LLM to check if the answer is correct.
