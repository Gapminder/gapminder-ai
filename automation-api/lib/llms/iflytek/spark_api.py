"""
API for IFlyTek's Spark, and langchain class for it.
"""

import base64
import datetime
import hashlib
import hmac
import json
from time import mktime
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import websocket
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from pydantic import root_validator

from lib.config import read_config


class Ws_Param(object):
    # this class was taken from IFlyTek's doc
    def __init__(self, APPID, APIKey, APISecret, gpt_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(gpt_url).netloc
        self.path = urlparse(gpt_url).path
        self.gpt_url = gpt_url

    def create_url(self):
        # RFC1123 timestamp
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # origin
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        # use hmac-sha256 to create auth info
        signature_sha = hmac.new(
            self.APISecret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )

        # create dictionary
        v = {"authorization": authorization, "date": date, "host": self.host}
        # create URL
        url = self.gpt_url + "?" + urlencode(v)
        return url


def get_reply(url: str, data: Dict) -> Dict[str, Any]:
    ws = websocket.WebSocket()
    ws.connect(url)
    ws.send(json.dumps(data))

    res = []

    while True:
        reply = ws.recv()
        data = json.loads(reply)
        code = data["header"]["code"]
        message = data["header"]["message"]
        if code != 0:
            print(f"WS error: {code}, {message}")
            ws.close()

            if code in [
                10013,
                10014,
                10019,
            ]:  # these codes mean the input/output were blocked by content filter.
                return {"text": message}
            else:
                raise websocket.WebSocketException("Websocket Error.")
        else:
            choices = data["payload"]["choices"]
            status = choices["status"]
            content = choices["text"][0]["content"]
            res.append(content)
            if status == 2:
                usage = data["payload"]["usage"]
                ws.close()

                return {"text": "".join(res), "usage": usage}


class SparkClient:
    gpt_url: str = "wss://spark-api.xf-yun.com/v1.1/chat"

    def __init__(self, appid: str, api_key: str, api_secret: str) -> None:
        self.appid = appid
        self.ws_url = Ws_Param(appid, api_key, api_secret, self.gpt_url).create_url()

    def gen_parameters(
        self,
        uid: str = "0",
        chat_id: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2048,  # [1, 4096]
        top_k: int = 4,  # [1, 6]
    ) -> Dict:
        data: Dict[str, Any] = {
            "header": {"app_id": self.appid, "uid": uid},
            "parameter": {
                "chat": {
                    "domain": "general",
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_k": top_k,
                }
            },
        }
        if chat_id:
            data["parameter"]["chat"]["chat_id"] = chat_id

        return data

    def gen_payload(self, content):
        data = {
            "payload": {"message": {"text": [{"role": "user", "content": content}]}}
        }
        return data

    def generate_text(self, content, **kwargs) -> Dict[str, Any]:
        data = self.gen_parameters(**kwargs)
        data.update(self.gen_payload(content))
        res = get_reply(self.ws_url, data)
        return res

    def chat(self):
        # TODO: add chat function, which accepts some message history and generate new reply.
        raise NotImplementedError()


def get_from_dict_or_env(data, key, env_key):
    if key in data and data[key]:
        return data[key]
    else:
        config = read_config()
        if env_key in config and config[env_key]:
            return config[env_key]
        raise ValueError(
            f"Did not found {key} in provided dict and {env_key} in environment variables"
        )


class Spark(LLM):
    # TODO: maybe rewrite based on BaseLLM. Need to implement the more complex _generate method.
    client: Any
    iflytek_appid: str
    iflytek_api_key: str
    iflytek_api_secret: str
    temperature: Optional[float] = 0.5
    max_tokens: Optional[int] = 2048
    top_k: Optional[int] = 4

    @property
    def _llm_type(self) -> str:
        return "iflytek_spark"

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:  # noqa: N805
        """Validate api key, python package exists."""
        iflytek_appid = get_from_dict_or_env(values, "iflytek_appid", "IFLYTEK_APPID")
        iflytek_api_key = get_from_dict_or_env(
            values, "iflytek_api_key", "IFLYTEK_API_KEY"
        )
        iflytek_api_secret = get_from_dict_or_env(
            values, "iflytek_api_secret", "IFLYTEK_API_SECRET"
        )

        values["client"] = SparkClient(
            iflytek_appid, iflytek_api_key, iflytek_api_secret
        )

        if values["temperature"] is not None and not 0 <= values["temperature"] <= 1:
            raise ValueError("temperature must be in the range [0.0, 1.0]")

        if values["top_k"] is not None and not 1 <= values["top_k"] <= 6:
            raise ValueError("top_k must be between 1 and 6")

        if values["max_tokens"] is not None and not 1 <= values["max_tokens"] <= 4096:
            raise ValueError("max_output_tokens must be between 1 and 4096")

        return values

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")
        return self.client.generate_text(
            prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_k=self.top_k,
        )["text"]

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_k": self.top_k,
        }
