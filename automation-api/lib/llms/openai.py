"""Wrapper around LangChain's openAI wrapper.
"""

from dataclasses import dataclass, field
from typing import Optional, Union

from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

from lib.config import read_config


@dataclass
class OpenAIModel:
    """get openAI model by name.

    example:

    >>> model_config = {'temperature': 0}
    >>> model = OpenAIModel('gpt-3.5-turbo', model_config=model_config)
    >>> template = "What are the top {k} resources to learn {this} in 2023?"
    >>> model.run(template, k=3, this='rust')

    By default the api key and organization defined in .env will be used.
    But you can specify a different api key or organization:

    >>> model = OpenAIModel('gpt-3.5-turbo', api_key='...', org_id='...')
    """

    model_name: str
    model_config: Optional[dict] = field(default_factory=dict)
    api_key: Optional[str] = field(default=None, repr=False)
    org_id: Optional[str] = field(default=None, repr=False)
    _model: Union[OpenAI, ChatOpenAI] = field(init=False, default=None, repr=False)

    def __post_init__(self):
        "docstring"
        config = read_config()
        if self.api_key is None:
            self.api_key = config["OPENAI_API_KEY"]
        if self.org_id is None:
            self.org_id = config["OPENAI_ORG_ID"]

        if self.model_name in ["gpt-3.5-turbo", "gpt-4"]:
            self._model = ChatOpenAI(
                model_name=self.model_name,
                openai_api_key=self.api_key,
                openai_organization=self.org_id,
                **self.model_config
            )
        else:
            self._model = OpenAI(
                model_name=self.model_name,
                openai_api_key=self.api_key,
                openai_organization=self.org_id,
                **self.model_config
            )

    @property
    def model(self):
        return self._model

    def run(self, prompt_text, **kwargs):
        """format prompt_text and run it with the model.

        All keyword args will be passed to format the prompt_text.
        """
        prompt = PromptTemplate(
            template=prompt_text, input_variables=list(kwargs.keys())
        )
        chain = LLMChain(llm=self.model, prompt=prompt)

        return chain.run(kwargs)
