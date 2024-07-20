"""Tokenizer helper module for Prompt Poet."""

from threading import Lock
from tiktoken import get_encoding, Encoding
from typing import Callable

_tokenizer_lock = Lock()
_DEFAULT_ENCODE_FUNC = None
_DEFAULT_TIKTOKEN_ENCODING_NAME = "o200k_base"


def get_encode_func(encoding_name: str = None) -> Callable[[str], list[int]]:
    """Get the encode function for the appropriate tiktoken encoding name."""
    if encoding_name is None:
        encoding_name = _DEFAULT_TIKTOKEN_ENCODING_NAME

    global _DEFAULT_ENCODE_FUNC
    with _tokenizer_lock:
        if _DEFAULT_ENCODE_FUNC is None:
            enc: Encoding = get_encoding(encoding_name) 
            _DEFAULT_ENCODE_FUNC = enc.encode
    return _DEFAULT_ENCODE_FUNC
