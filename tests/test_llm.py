"""Tests for the Bedrock client, with a fake boto3 client instead of AWS."""

import json

from src.assistant.llm import MAX_TOOL_ROUNDS, BedrockClient


def text_reply(text, tokens=(10, 5)):
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "usage": {"inputTokens": tokens[0], "outputTokens": tokens[1]},
        "stopReason": "end_turn",
    }


def tool_reply(name, arguments, tool_use_id="t1", tokens=(20, 8)):
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"toolUse": {"toolUseId": tool_use_id, "name": name, "input": arguments}}],
            }
        },
        "usage": {"inputTokens": tokens[0], "outputTokens": tokens[1]},
        "stopReason": "tool_use",
    }


class FakeBedrock:
    """Returns prepared Converse responses one by one and remembers the requests."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def converse(self, **request):
        self.requests.append(json.loads(json.dumps(request)))  # a snapshot: the client keeps appending to it
        return self.responses.pop(0)


def test_plain_chat_builds_converse_request():
    fake = FakeBedrock(text_reply("Hi there"))
    reply = BedrockClient(client=fake).chat([{"role": "user", "content": "hello"}], system="be nice")

    request = fake.requests[0]
    assert request["messages"] == [{"role": "user", "content": [{"text": "hello"}]}]
    assert request["system"] == [{"text": "be nice"}]
    assert "toolConfig" not in request
    assert reply.text == "Hi there"
    assert (reply.input_tokens, reply.output_tokens) == (10, 5)


def test_tool_loop_runs_the_tool_and_returns_the_final_answer():
    fake = FakeBedrock(tool_reply("check_country", {"country": "Poland"}), text_reply("Yes, you can.", (30, 6)))
    seen = []

    def run_tool(name, arguments):
        seen.append((name, arguments))
        return {"country": "Poland", "listed": True}

    reply = BedrockClient(client=fake).chat(
        [{"role": "user", "content": "Poland?"}], tool_config={"tools": []}, run_tool=run_tool
    )

    assert seen == [("check_country", {"country": "Poland"})]
    assert reply.text == "Yes, you can."
    assert reply.tool_calls == [
        {"name": "check_country", "input": {"country": "Poland"}, "output": {"country": "Poland", "listed": True}}
    ]
    assert (reply.input_tokens, reply.output_tokens) == (20 + 30, 8 + 6)  # tokens of both calls

    # The second request carries the model's tool request and our tool result, linked by toolUseId.
    second = fake.requests[1]["messages"]
    assert second[1]["content"][0]["toolUse"]["toolUseId"] == "t1"
    tool_result = second[2]["content"][0]["toolResult"]
    assert tool_result["toolUseId"] == "t1"
    assert json.loads(tool_result["content"][0]["text"]) == {"country": "Poland", "listed": True}


def test_tool_loop_stops_after_max_rounds():
    replies = [tool_reply("list_plans", {}, tool_use_id=f"t{i}") for i in range(MAX_TOOL_ROUNDS + 1)]
    fake = FakeBedrock(*replies)

    reply = BedrockClient(client=fake).chat(
        [{"role": "user", "content": "loop"}], tool_config={"tools": []}, run_tool=lambda name, args: {"plans": []}
    )

    assert reply.stop_reason == "max_tool_rounds"
    assert reply.text == ""
    assert len(fake.requests) == MAX_TOOL_ROUNDS + 1

def test_thinking_is_removed_from_the_answer():
    reply_text = "<thinking>Poland is supported. I will now tell the user.</thinking>\n\nYes, you can open an account."
    fake = FakeBedrock(text_reply(reply_text))

    reply = BedrockClient(client=fake).chat([{"role": "user", "content": "Poland?"}])

    assert reply.text == "Yes, you can open an account."
    assert "Poland is supported" in reply.reasoning
