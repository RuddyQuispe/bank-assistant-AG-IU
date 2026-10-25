from functools import lru_cache
from typing import overload

from langchain_core.language_models import LanguageModelInput
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import BaseModel

from digital_wallet_rqm.config.settings import settings


@lru_cache(maxsize=8)
def _get_chat_model(temperature: float = settings.DEFAULT_TEMPERATURE) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.CHAT_MODEL,
        temperature=temperature,
        max_retries=settings.MAX_RETRIES,
        include_thoughts=False
    )


@overload
def get_llm(temperature: float = settings.DEFAULT_TEMPERATURE,
            response_format: None = None) -> ChatGoogleGenerativeAI: ...


@overload
def get_llm(temperature: float = settings.DEFAULT_TEMPERATURE, *, response_format: type[str]) -> Runnable[
    LanguageModelInput, str]: ...


@overload
def get_llm[T: BaseModel](temperature: float = settings.DEFAULT_TEMPERATURE, *, response_format: type[T]) -> Runnable[
    LanguageModelInput, T]: ...


def get_llm(temperature: float = settings.DEFAULT_TEMPERATURE,
            response_format: type[str] | type[BaseModel] | None = None):
    llm = _get_chat_model(temperature)
    if response_format is None:
        return llm
    if response_format is str:
        return llm | StrOutputParser()
    return llm.with_structured_output(response_format)


@lru_cache(maxsize=1)
def get_llm_embedding() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL
    )
