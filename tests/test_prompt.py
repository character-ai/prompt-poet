import os
import pytest
import jinja2 as j2
from prompt import Prompt
from examples.cai_helpers import CAIMessage
from pp_exceptions import TruncationError

CWD = os.path.dirname(__file__)

def test_simple_prompt_sad():
    with pytest.raises(ValueError, match="`token_limit` is a reserved key in the template data."):
        _ = Prompt(
            template_data={"var1": "foobar", "token_limit": 10},
            template_path=os.path.abspath(
                os.path.join(CWD, "templates", "simple_prompt.yml.j2")
            ),
        )

    with pytest.raises(ValueError, match="`escape_special_characters` is a reserved key in the template data."):
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
    assert prompt.string == "<|beginningofdialog|>Raw string of first part<|endofmessage|><|beginningofmessage|>Raw string of second part<|endofmessage|>"

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
            "reply_prompt": "Alice:"
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )
    assert prompt.string == "<|beginningofdialog|>2024 06 24 Alice: The title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first message<|endofmessage|><|beginningofmessage|>Jeff: The second message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth message<|endofmessage|><|beginningofmessage|>Alice:"

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
            "reply_prompt": "Alice:"
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )
    assert prompt.string == "<|beginningofdialog|>2024 06 24 Alice: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"

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
            "reply_prompt": "Alice:"
        },
        template_path="cai.yml.j2",
        from_examples=True,
        token_limit=100,
    )
    prompt.lreplace_at(old=" Alice", new=" Bob", index=1)
    assert prompt.string == "<|beginningofdialog|>2024 06 24 Bob: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    prompt.lreplace_at(old=" ", new="<|beginningofmessage|>", index=1)
    assert prompt.string == "<|beginningofdialog|>2024 06 24<|beginningofmessage|>Bob: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    prompt.lreplace_at(old="<|beginningofmessage|>", new=" ", index=1)
    assert prompt.string == "<|beginningofdialog|>2024 06 24 Bob: The \r title - The description<|endofmessage|><|beginningofmessage|>narrator: The definition<|endofmessage|><|beginningofmessage|>narrator: With multiple lines<|endofmessage|><|beginningofmessage|>narrator: In the definition<|endofmessage|><|beginningofmessage|>Jeff: The persona \r definition<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Alice: The first \n \n message<|endofmessage|><|beginningofmessage|>Jeff: The second \r message<|endofmessage|><|beginningofmessage|>Alice: The third message<|endofmessage|><|beginningofmessage|>Jeff: The fourth ' message<|endofmessage|><|beginningofmessage|>Alice:"
    with pytest.raises(IndexError, match="Index out of bounds:"):
        prompt.lreplace_at(old="<|beginningofmessage|>", new=" ", index=999)


def test_truncation_template_happy():
    prompt = Prompt(
        template_data={
            "num_hundred_sections": 9, 
            "num_ten_sections": 0,
            "truncation_elements": [
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10}
            ]
        },
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "truncation_prompt.yml.j2"),
        ),
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
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*10},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*100},
                {"tokens": [1]*10},
            ]
        },
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "truncation_prompt.yml.j2"),
        ),
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
                {"tokens": [1]*10},
            ]
        },
        template_path=os.path.abspath(
            os.path.join(CWD, "templates", "truncation_prompt.yml.j2"),
        ),
    )
    prompt.tokenize()
    assert len(prompt.tokens) == 920
    with pytest.raises(TruncationError, match=r"Failed to successfully truncate the prompt to below token limit:.*"):
        prompt.truncate(token_limit=900, truncation_step=100)
    # Ensure prompt state has been reverted.
    assert len(prompt.tokens) == 920

def test_openai_spec():
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
            "reply_prompt": "Alice:"
        },
        template_path="cai.yml.j2",
        from_examples=True,
    )    
    assert len(prompt.openai_messages) == 12
    assert "content" in prompt.openai_messages[0]
    assert "role" in prompt.openai_messages[0]

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
            "reply_prompt": "Alice:"
        },
        template_path="cai.yml.j2",
        from_examples=True,
    )
    with pytest.raises(ValueError, match=r"Not all parts have been tokenized. Please tokenize first.*"):
        prompt.truncate(token_limit=1000, truncation_step=10)    
