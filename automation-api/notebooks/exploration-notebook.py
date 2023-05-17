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


