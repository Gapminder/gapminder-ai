from __future__ import annotations

import os

from dotenv import load_dotenv


def read_config() -> dict[str, str]:
    load_dotenv()

    config = {}
    # Mandatory configuration
    for key in [
        "OPENAI_API_KEY",
        "OPENAI_ORG_ID",
    ]:
        config[key] = os.getenv(key=key, default="")
        if config[key] == "":
            raise Exception(f"The mandatory environment variable {key} is empty")
    # Optional configuration
    for key in [
        "OPENAI_API_DEV_KEY",
        "SERVICE_ACCOUNT_CREDENTIALS",
        "AI_EVAL_SPREADSHEET_ID",
        "AI_EVAL_DEV_SPREADSHEET_ID",
        "HUGGINGFACEHUB_API_TOKEN",
        "PALM_API_KEY",
        "IFLYTEK_APPID",
        "IFLYTEK_API_KEY",
        "IFLYTEK_API_SECRET",
        "DASHSCOPE_API_KEY",
        "REPLICATE_API_KEY",
    ]:
        config[key] = os.getenv(key=key, default="")
    return config
