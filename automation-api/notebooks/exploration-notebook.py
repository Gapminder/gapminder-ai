# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.7
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


