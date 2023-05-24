# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
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

# ## OpenAI access via LangChain

# +
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

from lib.config import read_config

config = read_config()
openai_api_key = config["OPENAI_API_KEY"]

template = "What are the top {k} resources to learn {this} in 2023?"
prompt = PromptTemplate(template=template, input_variables=["k", "this"])

llm = OpenAI(model_name="text-davinci-003", openai_api_key=config["OPENAI_API_KEY"])
chain = LLMChain(llm=llm, prompt=prompt)

print(chain.run({"k": 3, "this": "Rust"}))
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


