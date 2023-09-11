"""utilities to create language models and send queries to model APIs
"""

from typing import Any, Dict, Union

from langchain.base_language import BaseLanguageModel
from langchain.chains import LLMChain
from langchain.chat_models import ChatGooglePalm, ChatOpenAI
from langchain.llms import GooglePalm, HuggingFaceHub, OpenAI
from langchain.prompts import PromptTemplate

from lib.config import read_config

from .alibaba import Alibaba
from .fake import RandomAnswerLLM
from .spark import Spark


def get_openai_model(model_name: str, **kwargs: Any) -> Union[ChatOpenAI, OpenAI]:
    """get OpenAI modle from langchain

    api key and organization will be set automatically.

    All keywork arguments will be passed to the langchain model as
    initization parameters.

    example:

    >>> model = get_openai_model('text-ada-001')

    """
    config: Dict[str, str] = read_config()
    api_key: str = (
        kwargs.pop("openai_api_key")
        if "openai_api_key" in kwargs
        else config["OPENAI_API_KEY"]
    )
    org_id: str = (
        kwargs.pop("openai_organization")
        if "openai_organization" in kwargs
        else config["OPENAI_ORG_ID"]
    )
    if model_name.startswith("gpt-3.5-turbo") or model_name.startswith("gpt-4"):
        return ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_organization=org_id,
            **kwargs,
        )
    else:
        return OpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_organization=org_id,
            **kwargs,
        )


def get_google_palm_model(
    model_name: str, **kwargs: Any
) -> Union[GooglePalm, ChatGooglePalm]:
    config: Dict[str, str] = read_config()
    api_key: str = (
        kwargs.pop("google_api_key")
        if "google_api_key" in kwargs
        else config["GOOGLE_API_KEY"]
    )
    if model_name == "text-bison":
        return GooglePalm(google_api_key=api_key, **kwargs)
    elif model_name == "chat-bison":
        return ChatGooglePalm(google_api_key=api_key, **kwargs)
    else:
        raise NotImplementedError(f"llm {model_name} not defined")


def get_dummy_model(model_name: str, **kwargs: Any) -> RandomAnswerLLM:
    if model_name == "fakellm":
        answer_list = kwargs.get("answer_list", None)
        if answer_list is None:
            return RandomAnswerLLM(answer_list=["A", "B", "C"])
        else:
            return RandomAnswerLLM(answer_list=answer_list)
    else:
        raise NotImplementedError(f"llm {model_name} not defined.")


def get_huggingface_model(model_name: str, **kwargs: Any) -> HuggingFaceHub:
    config: Dict[str, str] = read_config()
    huggingfacehub_api_token = config["HUGGINGFACEHUB_API_TOKEN"]
    return HuggingFaceHub(
        huggingfacehub_api_token=huggingfacehub_api_token,
        repo_id=model_name,
        model_kwargs=kwargs,
    )


def get_iflytek_model(**kwargs: Any) -> Spark:
    config: Dict[str, str] = read_config()
    iflytek_appid = config["IFLYTEK_APPID"]
    iflytek_api_key = config["IFLYTEK_API_KEY"]
    iflytek_api_secret = config["IFLYTEK_API_SECRET"]
    return Spark(
        iflytek_appid=iflytek_appid,
        iflytek_api_key=iflytek_api_key,
        iflytek_api_secret=iflytek_api_secret,
        **kwargs,
    )


def get_alibaba_model(model_name, **kwargs: Any) -> Alibaba:
    config: Dict[str, str] = read_config()
    dashscope_api_key = config["DASHSCOPE_API_KEY"]
    return Alibaba(model_name=model_name, dashscope_api_key=dashscope_api_key, **kwargs)


def run_model(
    llm: BaseLanguageModel, prompt_template: str, verbose: bool, **kwargs: Any
) -> str:
    """run a language model with prompt.

    prompt_template will be formatted with all keyword arguments.
    """
    prompt = PromptTemplate(
        template=prompt_template, input_variables=list(kwargs.keys())
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(kwargs)


def ask_question(
    prompt_template: str, question: str, llm: BaseLanguageModel, verbose: bool = False
) -> str:
    return run_model(llm, prompt_template, verbose, question=question)
