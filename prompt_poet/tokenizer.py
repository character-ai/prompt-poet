"""Tokenizer helper module for Prompt Poet."""

from abc import ABC, abstractmethod
from importlib.metadata import PackageNotFoundError, version
from threading import Lock

_tokenizer_lock = Lock()
_TOKENIZER = None


class AbstractTokenizer(ABC):
    """Abstract class for a tokenizer instance used by Prompt Poet (PP)."""

    def __init__(self, name):
        """Initialize the tokenizer."""
        self.name = name
        super().__init__()

    @property
    @abstractmethod
    def vocab_size(self) -> int:
        """Size of the vocabulary."""
        pass

    @property
    @abstractmethod
    def vocab(self) -> dict[str, int]:
        """Dictionary from vocab text token to id token."""
        pass

    @property
    @abstractmethod
    def inv_vocab(self) -> dict[int, str]:
        """Dictionary from vocab id token to text token."""
        pass

    @abstractmethod
    def tokenize(self, text: str) -> list[int]:
        """Tokenize the provided unicode string into a list of token ids."""
        pass

    def detokenize(self, token_ids: list[int]) -> str:
        """Detokenize the provided token ids into a unicode string."""
        raise NotImplementedError(
            "detokenizer is not implemented for {} " "tokenizer".format(self.name)
        )

    @property
    def cls(self):
        """The cls object."""
        raise NotImplementedError(
            "CLS is not provided for {} " "tokenizer".format(self.name)
        )

    @property
    def sep(self):
        """The sep object."""
        raise NotImplementedError(
            "SEP is not provided for {} " "tokenizer".format(self.name)
        )

    @property
    def pad(self):
        """The pad object."""
        raise NotImplementedError(
            "PAD is not provided for {} " "tokenizer".format(self.name)
        )

    @property
    def eod(self):
        """The end-of-dialogue (eod) object."""
        raise NotImplementedError(
            "EOD is not provided for {} " "tokenizer".format(self.name)
        )

    @property
    def mask(self):
        """The mask object."""
        raise NotImplementedError(
            "MASK is not provided for {} " "tokenizer".format(self.name)
        )


def _check_chartok_version():
    install_cmd = "python -m pip install chartok@https://characterai.io/py_wheels/chartok/chartok-0.4.3-py3-none-any.whl"
    try:
        installed_version = version("chartok")
    except PackageNotFoundError:
        raise ImportError(
            f"The 'chartok' package not found. Consider installing it with `{install_cmd}`."
        )
    if installed_version != "0.4.3":
        raise ImportError(
            f"Prompt Poet requires chartok==0.4.3, but found {installed_version}. Consider installing it with `{install_cmd}`."
        )


def get_default_tokenizer():
    """Get the default Prompt Poet (PP) tokenizer."""
    # Only build tokenizer if necessary.
    _check_chartok_version()

    # pylint: disable=import-outside-toplevel
    from chartok import heather

    global _TOKENIZER
    with _tokenizer_lock:
        if _TOKENIZER is None:
            _TOKENIZER = heather()
    return _TOKENIZER
