# encoding: utf-8

from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_not_result,
    stop_after_attempt,
)
from http import HTTPStatus
import dashscope
from dashscope import Generation
from lib.config import read_config
import random


def response_is_ok(response):
    if response.status_code == HTTPStatus.OK:
        return True
    return False


def return_last_message(retry_state):
    last_val = retry_state.outcome.result()
    result = {"output": {"text": f"Error: {last_val.code}: {last_val.message}"}}
    return result


@retry(
    retry=(retry_if_exception_type() | retry_if_not_result(response_is_ok)),
    stop=stop_after_attempt(3),
    retry_error_callback=return_last_message,
)
def get_reply(**kwargs):
    return Generation.call(**kwargs)


""" Here we need to convert the reply from alibaba into openai's output format.

Alibaba:
```
{
    "status_code": 200,
    "request_id": "05dc83af-7185-9e14-9b0b-4466de159d6a",
    "code": "",
    "message": "",
    "output": {
        "text": null
        "finish_reason": null
        "choices": [
          {
            "finish_reason": "stop",
            "message": {
              "role": "assistant",
              "content": "对于有编程基础的人，..."
            }
          }
        ],
    },
    "usage": {
        "input_tokens": 12,
        "output_tokens": 98,
        "total_tokens": 110
    }
}
```

openai:
```
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-3.5-turbo-0613",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "\n\nHello there, how may I assist you today?",
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

The only thing need to translate is the `output` key in alibaba
"""


def llm_complete(
    model_name,
    prompt,
    top_p=0.8,
    top_k=100,
    enable_search=False,
    dashscope_api_key=None,
):
    seed = random.randint(0, 2**63)
    if not dashscope_api_key:
        config = read_config()
        if "DASHSCOPE_API_KEY" in config.keys():
            dashscope_api_key = config["DASHSCOPE_API_KEY"]
        else:
            raise ValueError(
                "please set DASHSCHPE_API_KEY in .env or \
                provide the dashschpe_api_key parameter."
            )
    dashscope.api_key = dashscope_api_key

    reply = get_reply(
        model=model_name,
        prompt=prompt,  # alternativly we can use the `messages` parameter. see doc.
        top_p=top_p,
        top_k=top_k,
        seed=seed,
        enable_search=enable_search,
        result_format="message",
    )
    # fixing the format
    output = reply.pop("output", None)
    if (
        output["text"] is not None
    ):  # API reported an error. see return_last_message() above.
        # let's just return the error message.
        reply["choices"] = [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": output["text"]},
            }
        ]
    else:
        reply["choices"] = output["choices"]
    return reply


if __name__ == "__main__":
    # NOTE: currently there is qwen-turbo and qwen-plus.
    # qwen-plus is stronger than qwen-turbo
    q = "世界人口从 60 亿增长到 70 亿用了 12 年。从 70 亿增加到 80 亿用了多长时间？"
    print(llm_complete("qwen-plus", q))
