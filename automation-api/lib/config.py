from __future__ import annotations

import base64
import json
import os
import tempfile

from dotenv import load_dotenv


def make_tmp_file_google_application_credentials(base64encoded_credentials):
    """set up GOOGLE_APPLICATION_CREDENTIALS enviornment variable

    GOOGLE_APPLICATION_CREDENTIALS is expected to be a file path, but we stored the
    file contents as a base64 encoded string.

    This function will create a temp file with the oridinary contents of the credentials
    """
    service_account_credentials = base64.b64decode(base64encoded_credentials).decode(
        "utf-8"
    )
    json_acct_info = json.loads(service_account_credentials)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        # TODO: this doesn't delete the temp file. is this safe to do in production?
        json.dump(json_acct_info, temp_file, indent=2)

    return os.path.abspath(temp_file.name)


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
        "GEMINI_API_KEY",
        "VERTEXAI_PROJECT",
        "VERTEXAI_LOCATIONS",
        "VERTEX_SERVICE_ACCOUNT_CREDENTIALS",
        "XAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "MISTRAL_API_KEY",
        "REDIS_HOST",
        "REDIS_PORT",
    ]:
        config[key] = os.getenv(key=key, default="")

    # create a tempfile for GOOGLE_APPLICATION_CREDENTIALS
    if config["VERTEX_SERVICE_ACCOUNT_CREDENTIALS"]:
        tmp_file = make_tmp_file_google_application_credentials(
            config["VERTEX_SERVICE_ACCOUNT_CREDENTIALS"]
        )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_file
        config["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_file

    return config
