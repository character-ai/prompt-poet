"""Construct a Prompt Poet (PP) prompt given data and a template."""

import copy
import inspect
import logging
import math
from dataclasses import dataclass
from functools import reduce

import yaml
from examples import cai_helpers
from pp_exceptions import TruncationError
from template import Template
from tokenizer import AbstractTokenizer, get_default_tokenizer

SPACE_MARKER = "<|space|>"
DEFAULT_TRUNCATION_STEP = 1000


@dataclass
class PromptPart:
    """Container representing repeated prompt parts from the template."""

    name: str
    """A unique name given to the prompt part used for readability and sometimes used functionally such as for truncation."""
    
    content: str
    """The string payload representing the content to be tokenized for this prompt part."""
    
    role: str = "user"
    """The role of the author of this message."""
    
    tokens: list[int] = None
    """The tokenized representation of the content."""
    
    truncation_priority: int = 0
    """The priority of this part for truncation. Higher values are truncated first."""


@dataclass
class TruncationBlock:
    """Container representing a block of prompt parts to consider for truncatation."""

    left: int
    right: int
    truncation_priority: int
    total_tokens: int


class Prompt:
    """Construct a Prompt Poet (PP) prompt given data and a template.

    :param template_data: The data that will be used to render the Jinja2
        syntax in the template.
    :param template_path: An optional filepath to the template file on disk.
    :param package_name: An optional package name containing the template file.
    :param raw_template: An optional raw template string used instead of a template
        file.
    :param logger: An optional logger to be used by this module and passed to
        downstream modules.
    :param tokenizer: An optional tokenizer to be used by this module. If not provided,
        the default tokenizer will be used if the caller attempts to tokenize the
        prompt.
    :param token_limit: An optional maximum number of tokens used by this prompt
        _after_ truncation via `truncate`. A value of -1 means no truncation will
        take place.
    :param truncation_step: Controls how aggressively to truncate with additional buffer.
        Set to 1 to avoid truncating more than you strictly need to to meet the
        `token_limit`.
    :param from_cache: A boolean indicating whether to load a cached value of the
        template, if present.
    :param from_examples: A boolean indicating whether to load the template from the
        provided example templates.
    :param space_marker: A string used to represent a space in the template. Trailing
        whitespace will be stripped.
    :newline: The representation of a newline in the template.
    :escaped_newline: The escaped representation of a newline in the template.
    :carriage_return: The representation of a carriage return in the template.
    :escaped_carriage_return: The escaped representation of a carriage return in the
        template.
    :single_quote: The representation of a single quote in the template.
    :escaped_single_quote: The escaped representation of a single quote in the template.
    """

    def __init__(
        self,
        template_data: dict,
        template_path: str = None,
        package_name: str = None,
        raw_template: str = None,
        logger: logging.LoggerAdapter = None,
        tokenizer: AbstractTokenizer = None,
        token_limit: int = -1,
        truncation_step: int = None,
        from_cache: bool = False,
        from_examples: bool = False,
        space_marker: str = SPACE_MARKER,
        newline: str = "\n",
        escaped_newline: str = "\\n",
        carriage_return: str = "\r",
        escaped_carriage_return: str = "\\r",
        single_quote: str = "'",
        escaped_single_quote: str = "'",
    ):
        """Initialize the prompt object."""
        self._template = Template(
            template_path=template_path,
            package_name=package_name,
            raw_template=raw_template,
            logger=logger,
            from_cache=from_cache,
            from_examples=from_examples,
        )
        self._template_data = copy.deepcopy(template_data)
        self._provided_logger = logger
        self._token_limit = token_limit
        self._truncation_step = (
            DEFAULT_TRUNCATION_STEP if truncation_step is None else truncation_step
        )
        self._from_cache = from_cache
        self._from_examples = from_examples
        self._space_marker = space_marker
        self._newline = newline
        self._escaped_newline = escaped_newline
        self._carriage_return = carriage_return
        self._escaped_carriage_return = escaped_carriage_return
        self._single_quote = single_quote
        self._escaped_single_quote = escaped_single_quote
        self._tokenizer = tokenizer

        self._rendered_template = None
        self._parts = None
        self._parts_bak = None
        self._total_tokens = 0
        self._cached_tokens = None
        self._cached_pretruncation_tokens = None

        self._load_special_template_data()
        self._render_parts()

    def tokenize(self, force_retokenize: bool = False):
        """Tokenize the prompt parts."""
        if not self._parts:
            raise ValueError(f"Nothing to tokenize: {self._parts=}.")

        for part in self._parts:
            self._tokenize_part(part, force_retokenize=force_retokenize)

        # Create a backup; used for idempotency during truncation.
        if self._parts_bak is None:
            self._parts_bak = copy.deepcopy(self._parts)

    def lreplace_at(self, old: str, new: str, index: int):
        """Performs a left replace on the raw string of the part at specified index.

        WARNING: this violates clear separation between templating and logical layers
        by modifying the rendered data directly and is NOT recommended for production
        use.
        """
        if len(self._parts) > index:
            part = self._parts[index]
            if part.content.startswith(old):
                self._parts[index].content = f"{new}{part.content.lstrip(old)}"
                self._tokenize_part(part, force_retokenize=True)
        else:
            raise IndexError(f"Index out of bounds: {index=} {len(self._parts)=}.")

    def truncate(self, token_limit: int = None, truncation_step: int = None):
        """An idempotent operation which truncates the rendered template according to the token limit."""
        if token_limit is not None:
            self.logger.info(f"Overriding {self._token_limit=} with {token_limit=}")
        else:
            token_limit = self._token_limit

        if truncation_step is not None:
            self.logger.info(
                f"Overriding {self._truncation_step=} with {truncation_step=}"
            )
        else:
            truncation_step = self._truncation_step

        if token_limit == -1:
            self.logger.info(f"No truncation necessary: {token_limit=}")
            return

        # Ensure we have valid values for truncation.
        if token_limit <= 0:
            raise ValueError(f"Invalid token limit: {token_limit=}")
        if truncation_step <= 0:
            raise ValueError(f"Invalid truncation step: {truncation_step=}")

        # Ensure all parts have been tokenized.
        if any(part.tokens is None for part in self._parts):
            raise ValueError(f"Not all parts have been tokenized. Please tokenize first. {self._parts=}")

        self._reset_parts()

        num_tokens_to_truncate = self._calculate_num_tokens_to_truncate(
            token_limit=token_limit, truncation_step=truncation_step
        )
        truncation_blocks = self._build_truncation_blocks()

        self._truncate(
            truncation_blocks=truncation_blocks,
            num_tokens_to_truncate=num_tokens_to_truncate,
        )

        if len(self.tokens) > token_limit:
            num_tokens = len(self.tokens)
            # Reset the parts to the pretruncation state.
            self._reset_parts()
            raise TruncationError(
                f"Failed to successfully truncate the prompt to below token limit: {num_tokens=} {token_limit=}. Resetting to pre-truncation state."
            )

    @property
    def parts(self) -> list[PromptPart]:
        """The parts of the prompt."""
        return self._parts

    @property
    def pretruncation_parts(self) -> list[PromptPart]:
        """The parts of the prompt prior to truncation."""
        return self._parts_bak if self._parts_bak else self._parts

    @property
    def token_limit(self) -> int:
        """The maximum number of tokens used by this prompt."""
        return self._token_limit

    @property
    def template_name(self) -> str:
        """The metadata associated with the template."""
        return self._template.template_name

    @property
    def template_dir(self) -> str:
        """The metadata associated with the template."""
        return self._template.template_dir

    @property
    def template_package_name(self) -> str:
        """The metadata associated with the template."""
        return self._template.template_package_name

    @property
    def pretruncation_string(self) -> str:
        """The direct string representation of the prompt prior to truncation."""
        return reduce(
            lambda acc, part: acc + part.content, self.pretruncation_parts, ""
        )

    @property
    def string(self) -> str:
        """The direct string representation of the final (truncated) prompt."""
        return reduce(lambda acc, part: acc + part.content, self._parts, "")

    @property
    def pretruncation_tokens(self) -> str:
        """The direct token representation of the prompt prior to truncation."""
        if not self._cached_pretruncation_tokens:
            try:
                self._cached_pretruncation_tokens = reduce(
                    lambda acc, part: acc + part.tokens, self.pretruncation_parts, []
                )
            except TypeError as ex:
                raise TypeError(
                    f"Error constructing tokens: {ex=}. You may need to .tokenize() first."
                )

        return self._cached_pretruncation_tokens

    @property
    def tokens(self) -> str:
        """The direct token representation of the prompt."""
        if not self._cached_tokens:
            try:
                self._cached_tokens = reduce(
                    lambda acc, part: acc + part.tokens, self._parts, []
                )
            except TypeError as ex:
                raise TypeError(
                    f"Error constructing tokens: {ex=}. You may need to .tokenize() first."
                )

        return self._cached_tokens

    @property
    def tokenizer(self) -> AbstractTokenizer:
        """The tokenizer used to tokenize the prompt."""
        if not self._tokenizer:
            self._tokenizer = get_default_tokenizer()

        return self._tokenizer

    @property
    def openai_messages(self) -> list[dict]:
        """OpenAI API compatible messages representing the prompt."""
        return [{"role": part.role, "content": part.content} for part in self._parts]

    @property
    def logger(self) -> str:
        """The logger to be used by this module."""
        if self._provided_logger:
            return self._provided_logger

        return logging.getLogger(__name__)

    def _truncate(
        self, truncation_blocks: list[TruncationBlock], num_tokens_to_truncate: int
    ):
        """Truncate the prompt based on the truncation blocks."""
        # Exit early, nothing to truncate.
        if not num_tokens_to_truncate or not truncation_blocks:
            return

        to_remove = [False] * len(self._parts)
        tokens_removed = 0
        for block in truncation_blocks:
            # Remove the entire block if it fits within the number of tokens to remove.
            if tokens_removed + block.total_tokens <= num_tokens_to_truncate:
                to_remove[block.left : block.right + 1] = [True] * (
                    block.right - block.left + 1
                )
                tokens_removed += block.total_tokens
            # Else, remove one part at a time to ensure we do not over truncate.
            else:
                for i in range(block.left, block.right + 1):
                    tokens_removed += len(self._parts[i].tokens)
                    to_remove[i] = True
                    if tokens_removed >= num_tokens_to_truncate:
                        break

            if tokens_removed >= num_tokens_to_truncate:
                break

        self._parts = [part for i, part in enumerate(self._parts) if not to_remove[i]]

    def _build_truncation_blocks(self) -> list[TruncationBlock]:
        """Builds a list of tuples representing the truncation steps."""
        if not self._parts:
            return []

        truncation_blocks: list[TruncationBlock] = []
        start = 0
        first_part: PromptPart = self._parts[start]
        current_truncation_priority = first_part.truncation_priority
        total_block_tokens = len(first_part.tokens)
        for idx in range(1, len(self._parts)):
            current_part = self._parts[idx]
            if current_part.tokens is None:
                raise ValueError(f"Part has not been tokenized: {current_part=}")

            # Accumulate tokens or mint a new truncation block.
            if current_part.truncation_priority == current_truncation_priority:
                total_block_tokens += len(current_part.tokens)
            else:
                truncation_block = TruncationBlock(
                    left=start,
                    right=idx - 1,
                    truncation_priority=current_truncation_priority,
                    total_tokens=total_block_tokens,
                )
                truncation_blocks.append(truncation_block)

                # Reset tracking parameters.
                start = idx
                current_truncation_priority = current_part.truncation_priority
                total_block_tokens = len(current_part.tokens)

        # Append the last block.
        truncation_blocks.append(
            TruncationBlock(
                left=start,
                right=len(self._parts) - 1,
                truncation_priority=current_truncation_priority,
                total_tokens=total_block_tokens,
            )
        )

        # Only truncate parts with non-zero and positive truncation priority.
        truncation_blocks = [
            block for block in truncation_blocks if block.truncation_priority > 0
        ]
        truncation_blocks.sort(
            key=lambda marker: marker.truncation_priority, reverse=True
        )
        if not truncation_blocks:
            self.logger.warning(
                "No parts with non-zero and positive truncation_priority set; no truncation blocks created; skipping truncation."
            )
        return truncation_blocks

    def _calculate_num_tokens_to_truncate(
        self, token_limit: int, truncation_step: int
    ) -> int:
        """Calculates the number of messages to truncate."""
        num_surplus_tokens = max(0, self._total_tokens - token_limit)
        return math.ceil(num_surplus_tokens / truncation_step) * truncation_step

    def _tokenize_part(self, part: PromptPart, force_retokenize: bool = False):
        # Invalidate the cached tokens.
        self._cached_tokens = None

        # Lazy load the tokenizer.
        if self._tokenizer is None:
            try:
                self._tokenizer = get_default_tokenizer()
            except ImportError as ex:
                raise ImportError(
                    f"Error loading default tokenizer. Consider providing your own tokenizer Prompt(tokenizer=your_tokenizer). {ex=}."
                )

        # Avoid retokenizing the part if it has already been tokenized.
        if part.tokens and force_retokenize:
            self._total_tokens -= len(part.tokens)
        elif part.tokens and not force_retokenize:
            self.logger.warning("Part already tokenized... skipping tokenization.")
            return

        part.tokens = self._tokenizer.tokenize(part.content)
        self._total_tokens += len(part.tokens)

    def _load_special_template_data(self):
        """Load special data into the template context."""
        if "token_limit" in self._template_data:
            raise ValueError("`token_limit` is a reserved key in the template data.")

        if "escape_special_characters" in self._template_data:
            raise ValueError(
                "`escape_special_characters` is a reserved key in the template data."
            )

        self._template_data["token_limit"] = self._token_limit
        self._template_data[
            "escape_special_characters"
        ] = self._escape_special_characters

        if self._from_examples:
            cai_functions = {}
            for name, obj in inspect.getmembers(cai_helpers):
                if inspect.isfunction(obj):
                    cai_functions[name] = obj
            self._template_data.update(cai_functions)

    def _render_parts(self):
        self._rendered_template = self._template.render_template(self._template_data)
        loaded_yaml = yaml.load(self._rendered_template, Loader=yaml.CSafeLoader)

        # TODO: Process parts in parallel with concurrent.futures.
        self._parts = [None] * len(loaded_yaml)
        for idx, yaml_part in enumerate(loaded_yaml):
            part = PromptPart(**yaml_part)
            self._cleanup_content(part)
            self._parts[idx] = part

            # Tokens were passed in the yaml; ensure we track them.
            if part.tokens is not None:
                self.logger.warning(
                    "Tokens were provided in template. Regular tokenization will be skipped."
                )
                self._total_tokens += len(part.tokens)

    def _cleanup_content(self, part: PromptPart):
        """Remove whitespace and unescape special characters, if present."""
        content = part.content.strip().replace(self._space_marker, " ")
        part.content = self._unescape_special_characters(content)

    def _escape_special_characters(self, string: str) -> str:
        """Escape sequences that will break yaml parsing."""
        return (
            string.replace(self._newline, self._escaped_newline)
            .replace(self._carriage_return, self._escaped_carriage_return)
            .replace(self._single_quote, self._escaped_single_quote)
        )

    def _unescape_special_characters(self, string: str) -> str:
        """Unescape special characters."""
        return (
            string.replace(self._escaped_newline, self._newline)
            .replace(self._escaped_carriage_return, self._carriage_return)
            .replace(self._escaped_single_quote, self._single_quote)
        )

    def _reset_parts(self):
        """Reset the parts to the pretruncation state."""
        # Reset the parts to the pretruncation state, if necessary. Ensures idempotency.
        self._cached_tokens = None
        if self._parts_bak:
            self._parts = copy.deepcopy(self._parts_bak)
        else:
            self.logger.warning(
                f"No parts backup. Skipping reset: {self._parts_bak=} {self._parts=}"
            )
            return

        if not self._parts:
            raise ValueError("No parts exist after attempting to reset.")
