import inspect
import os
import pytest

from examples.cai_helpers import CAIMessage

import jinja2 as j2
from pp_exceptions import TruncationError
from prompt import Prompt
from tiktoken import get_encoding

from template_loaders import LocalFSTemplateLoader, LocalPackageTemplateLoader
from examples import cai_helpers

CWD = os.path.dirname(__file__)
TIKTOKEN_ENCODING_NAME = "o200k_base"
ENCODE_FUNC = get_encoding(TIKTOKEN_ENCODING_NAME).encode


def test_simple_prompt_sad():
    with pytest.raises(
        ValueError, match="`token_limit` is a reserved key in the template data."
    ):
        _ = Prompt(
            template_data={"var1": "foobar", "token_limit": 10},
            template_path=os.path.abspath(
                os.path.join(CWD, "templates", "simple_prompt.yml.j2")
            ),
        )

    with pytest.raises(
        ValueError,
        match="`escape_special_characters` is a reserved key in the template data.",
    ):
        _ = Prompt(
            template_data={"var1": "foobar", "escape_special_characters": lambda x: x},
            template_path=os.path.abspath(
                os.path.join(CWD, "templates", "simple_prompt.yml.j2")
            ),
        )


def test_simple_prompt_happy():
    prompt = Prompt(
        template_data={"var1": "foobar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "simple_prompt.yml.j2")
        ),
    )
    assert prompt.string == "Raw string of the first part foobar"

    prompt = Prompt(
        template_data={"var1": "foobar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "simple_prompt.yml.j2"),
        ),
    )
    assert prompt.string == "Raw string of the first part foobar"


def test_section_prompt_happy():
    prompt = Prompt(
        template_data={"var1": "foobar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "section_prompt.yml.j2"),
        ),
    )
    assert prompt.string == "Raw string of section_aRaw string of section_b"


def test_macros_prompt_happy():
    prompt = Prompt(
        template_data={"var1": "foobar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "macros_prompt.yml.j2"),
        ),
    )
    assert (
        prompt.string
        == "<|beginningofdialog|>Raw string of first part<|endofmessage|><|beginningofmessage|>Raw string of second part<|endofmessage|>"
    )


def test_function_prompt_happy():
    prompt = Prompt(
        template_data={
            "var1": "foo",
            "var2": "bar",
            "concat_strings": lambda x, y: x + y,
        },
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "function_prompt.yml.j2"),
        ),
    )
    assert prompt.string == "foobar"


def test_template_not_found():
    with pytest.raises(j2.TemplateNotFound):
        _ = Prompt(
            template_data={"var1": "foobar"},
            template_path=os.path.abspath(
                os.path.join(CWD, "templates", "non_existent_template.yml.j2")
            ),
        )


def test_control_flow_happy():
    prompt = Prompt(
        template_data={"conditional": True},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "control_flow_prompt.yml.j2"),
        ),
    )
    assert "Raw string of conditional" in prompt.string
    assert "Raw string of item" not in prompt.string

    prompt = Prompt(
        template_data={"conditional": False, "items": ["item1", "item2", "item3"]},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "control_flow_prompt.yml.j2"),
        ),
    )
    assert "Raw string of conditional" not in prompt.string
    assert "Raw string of item item1" in prompt.string
    assert "Raw string of item item2" in prompt.string
    assert "Raw string of item item3" in prompt.string

    prompt = Prompt(
        template_data={"conditional": True, "items": ["item1", "item2", "item3"]},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "control_flow_prompt.yml.j2"),
        ),
    )
    assert "Raw string of conditional" in prompt.string
    assert "Raw string of item item1" in prompt.string
    assert "Raw string of item item2" in prompt.string
    assert "Raw string of item item3" in prompt.string


def test_scanner_error():
    prompt = Prompt(
        template_data={"var1": "foo\u2028bar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "simple_prompt.yml.j2")
        ),
    )
    assert prompt.string == "Raw string of the first part foo\\u2028bar"

    prompt = Prompt(
        template_data={"var1": "foo\u2029bar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "simple_prompt.yml.j2")
        ),
    )
    assert prompt.string == "Raw string of the first part foo\\u2029bar"

    prompt = Prompt(
        template_data={"var1": "foo\u0085bar"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "simple_prompt.yml.j2")
        ),
    )
    assert prompt.string == "Raw string of the first part foo\\u0085bar"

def test_example_cai_template_happy():
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first message"),
                CAIMessage(author="Jeff", text="The second message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )
    assert (
        prompt.string
        == "<|beginningofdialog|>2024 06 24 Alice: The title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first message<|endofmessage|><|beginningofmessage|>Jeff: The second message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth message<|endofmessage|><|beginningofmessage|>Alice:"
    )

    # With escaped special characters.
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )
    assert (
        prompt.string
        == "<|beginningofdialog|>2024 06 24 Alice: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    )

    # Using .lreplace_at().
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )
    prompt.lreplace_at(old=" Alice", new=" Bob", index=1)
    assert (
        prompt.string
        == "<|beginningofdialog|>2024 06 24 Bob: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    )
    prompt.lreplace_at(old=" ", new="<|beginningofmessage|>", index=1)
    assert (
        prompt.string
        == "<|beginningofdialog|>2024 06 24<|beginningofmessage|>Bob: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    )
    prompt.lreplace_at(old="<|beginningofmessage|>", new=" ", index=1)
    assert (
        prompt.string
        == "<|beginningofdialog|>2024 06 24 Bob: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    )
    with pytest.raises(IndexError, match="Index out of bounds:"):
        prompt.lreplace_at(old="<|beginningofmessage|>", new=" ", index=999)


def test_truncation_template_happy():
    prompt = Prompt(
        template_data={
            "num_hundred_sections": 9,
            "num_ten_sections": 0,
            "truncation_elements": [
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
            ],
        },
        encode_func=ENCODE_FUNC,
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "truncation_prompt.yml.j2"),
        ),
        allow_token_overrides=True,
    )
    prompt.tokenize()
    assert len(prompt.tokens) == 1010
    prompt.truncate(token_limit=1000, truncation_step=10)
    assert len(prompt.tokens) == 1000
    prompt.truncate(token_limit=1000, truncation_step=20)
    assert len(prompt.tokens) == 990
    prompt.truncate(token_limit=1000, truncation_step=100)
    assert len(prompt.tokens) == 910
    prompt.truncate(token_limit=1000, truncation_step=1000)
    assert len(prompt.tokens) == 910

    prompt = Prompt(
        template_data={
            "num_hundred_sections": 9,
            "num_ten_sections": 0,
            "truncation_elements": [
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 10},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 100},
                {"tokens": [1] * 10},
            ],
        },
        encode_func=ENCODE_FUNC,
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "truncation_prompt.yml.j2"),
        ),
        allow_token_overrides=True,
    )
    prompt.tokenize()
    assert len(prompt.tokens) == 1970
    prompt.truncate(token_limit=1245, truncation_step=7)
    assert len(prompt.tokens) == 1220
    prompt.truncate(token_limit=1333, truncation_step=33)
    assert len(prompt.tokens) == 1220
    prompt.truncate(token_limit=1333, truncation_step=24)
    assert len(prompt.tokens) == 1320
    prompt.truncate(token_limit=1333, truncation_step=16)
    assert len(prompt.tokens) == 1320


def test_escape_characters():
    # Implicitly assert that no YAML parsing exception is raised.
    _ = Prompt(
        template_data={"var1": "foobar\nkey:value"},
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "simple_prompt.yml.j2")
        ),
    )


def test_truncation_failure():
    prompt = Prompt(
        template_data={
            "num_hundred_sections": 9,
            "num_ten_sections": 0,
            "truncation_elements": [
                {"tokens": [1] * 10},
            ],
        },
        encode_func=ENCODE_FUNC,
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "truncation_prompt.yml.j2"),
        ),
        allow_token_overrides=True,
    )
    prompt.tokenize()
    assert len(prompt.tokens) == 920
    with pytest.raises(
        TruncationError,
        match=r"Failed to successfully truncate the prompt to below token limit:.*",
    ):
        prompt.truncate(token_limit=900, truncation_step=100)
    # Ensure prompt state has been reverted.
    assert len(prompt.tokens) == 920


def test_output_messages():
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
    )
    assert len(prompt.messages) == 12
    assert "content" in prompt.messages[0]
    assert "role" in prompt.messages[0]


def test_truncate_before_tokenize():
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
    )
    with pytest.raises(
        ValueError, match=r"Not all parts have been tokenized. Please tokenize first.*"
    ):
        prompt.truncate(token_limit=1000, truncation_step=10)


def test_truncation_step_zero():
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
        truncation_step=0,
        encode_func=ENCODE_FUNC,
    )
    prompt.tokenize()
    with pytest.raises(ValueError, match=r"truncation_step must be greater than 0.*"):
        prompt.truncate(token_limit=1000)


def test_tiktoken_encoding_name():
    prompt = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": "Alice:",
        },
        template_path="cai.yml.j2",
        from_examples=True,
        tiktoken_encoding_name="r50k_base",
    )
    prompt.tokenize()
    assert prompt.tokens


def test_reply_prompt():
    _ = Prompt(
        template_data={
            "timestamp": "2024 06 24",
            "username": "Jeff",
            "character": {
                "title": "The \r title",
                "description": "The description",
                "definition": "The definition\nWith multiple lines\nIn the definition",
                "participant__name": "Alice",
            },
            "persona_definition": "The persona \r definition",
            "cai_messages": [
                CAIMessage(author="Alice", text="The first \n \n message"),
                CAIMessage(author="Jeff", text="The second \r message"),
                CAIMessage(author="Alice", text="The third message", is_pinned=True),
                CAIMessage(author="Jeff", text="The fourth ' message"),
            ],
            "reply_prompt": 'Ada-H:  *he,, smiled*\n\n"Mm?..',
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )


def test_template_loader_with_prompt():
    template_data = {
        "timestamp": "2024 06 24",
        "username": "Jeff",
        "character": {
            "title": "The title",
            "description": "The description",
            "definition": "The definition\nWith multiple lines\nIn the definition",
            "participant__name": "Alice",
        },
        "persona_definition": "The persona definition",
        "cai_messages": [
            CAIMessage(author="Alice", text="The first message"),
            CAIMessage(author="Jeff", text="The second message"),
            CAIMessage(author="Alice", text="The third message", is_pinned=True),
            CAIMessage(author="Jeff", text="The fourth message"),
        ],
        "reply_prompt": "Alice:",
    }
    cai_functions = {}
    for name, obj in inspect.getmembers(cai_helpers):
        if inspect.isfunction(obj):
            cai_functions[name] = obj
    template_data.update(cai_functions)

    prompt_with_local_fs_template_loader = Prompt(
        template_data=template_data,
        token_limit=100,
        template_loader=LocalFSTemplateLoader("prompt_poet/examples/cai.yml.j2"),
    )
    assert len(prompt_with_local_fs_template_loader.messages) == 12

    # TODO: Tong to fix this or remove LocalPackageTemplateLoader.
    #prompt_with_local_package_template_loader = Prompt(
        #template_data=template_data,
        #token_limit=100,
        #template_loader=LocalPackageTemplateLoader("prompt_poet", "examples/cai.yml.j2"),
    #)
    #assert len(prompt_with_local_package_template_loader.messages) == 12

    prompt_with_template_path = Prompt(
        template_data=template_data,
        token_limit=100,
        template_path="prompt_poet/examples/cai.yml.j2"
    )
    assert len(prompt_with_template_path.messages) == 12
