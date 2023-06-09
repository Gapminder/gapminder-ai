"""utilities to create language models and send queries to model APIs
"""

from typing import Any, Dict, Union

from langchain.base_language import BaseLanguageModel
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.llms import HuggingFaceHub, OpenAI
from langchain.prompts import PromptTemplate

from lib.config import read_config

from .fake import RandomAnswerLLM


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


def get_dummy_model(model_name: str, **kwargs: Any) -> RandomAnswerLLM:
    if model_name == "fakellm":
        answer_list = kwargs.get("answer_list", None)
        if answer_list is None:
            return RandomAnswerLLM(answer_list=["A", "B", "C"])
        else:
            return RandomAnswerLLM(answer_list=answer_list)
    else:
        raise NotImplementedError(f"llm f{model_name} not defined.")


def get_huggingface_model(model_name: str, **kwargs: Any) -> HuggingFaceHub:
    config: Dict[str, str] = read_config()
    huggingfacehub_api_token = config["HUGGINGFACEHUB_API_TOKEN"]
    return HuggingFaceHub(
        huggingfacehub_api_token=huggingfacehub_api_token,
        repo_id=model_name,
        model_kwargs=kwargs,
    )


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
