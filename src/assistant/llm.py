"""LLM clients behind one interface: Bedrock now, Ollama can be added as another class.

Quick checks from the project root:
    python -m src.assistant.llm            plain chat
    python -m src.assistant.llm --tools    chat that may call the database tools
"""

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol
import re


import boto3

DEFAULT_MODEL = os.getenv("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0")
DEFAULT_REGION = os.getenv("AWS_REGION", "eu-north-1")
MAX_TOOL_ROUNDS = 3
# Nova writes its reasoning in <thinking> tags, mostly when it uses tools: never show it to the customer.
_THINKING = re.compile(r"<thinking>.*?</thinking>\s*", flags=re.DOTALL)

ToolRunner = Callable[[str, dict], dict]


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str
    stop_reason: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # [{"name", "input", "output"}, ...]
    reasoning: str = ""


class LLMClient(Protocol):
    name: str

    def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.2,
        tool_config: dict | None = None,
        run_tool: ToolRunner | None = None,
    ) -> LLMResponse: ...


class BedrockClient:
    """Amazon Bedrock through the Converse API.

    messages use a simple format: [{"role": "user", "content": "text"}, ...]

    With tool_config and run_tool the client runs the tool-use loop:
    the model asks for a tool -> run_tool executes it -> the result goes back to
    the model -> repeat until the model answers with text (at most MAX_TOOL_ROUNDS).
    """

    name = "bedrock"

    def __init__(self, model_id: str = DEFAULT_MODEL, region: str = DEFAULT_REGION, client=None):
        self.model_id = model_id
        # `client` can be passed directly (a fake one in tests); otherwise a real boto3 client is created.
        self.client = client if client is not None else boto3.client("bedrock-runtime", region_name=region)

    def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.2,
        tool_config: dict | None = None,
        run_tool: ToolRunner | None = None,
        reasoning: str = ""  # the model's <thinking> text, kept for logs and debugging only
    ) -> LLMResponse:
        conversation = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages]
        request = {
            "modelId": self.model_id,
            "messages": conversation,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            request["system"] = [{"text": system}]
        if tool_config:
            request["toolConfig"] = tool_config

        tool_calls: list[dict] = []
        input_tokens = output_tokens = 0
        start = time.perf_counter()

        for _ in range(MAX_TOOL_ROUNDS + 1):
            response = self.client.converse(**request)
            usage = response.get("usage", {})
            input_tokens += usage.get("inputTokens", 0)
            output_tokens += usage.get("outputTokens", 0)
            message = response["output"]["message"]
            stop_reason = response.get("stopReason", "")

            if stop_reason != "tool_use" or run_tool is None:
                break

            # The model asked for one or more tools: run them and send the results back.
            conversation.append(message)
            results = []
            for block in message["content"]:
                if "toolUse" not in block:
                    continue
                use = block["toolUse"]
                output = run_tool(use["name"], use.get("input") or {})
                tool_calls.append({"name": use["name"], "input": use.get("input") or {}, "output": output})
                results.append(
                    {"toolResult": {"toolUseId": use["toolUseId"], "content": [{"text": json.dumps(output)}]}}
                )
            conversation.append({"role": "user", "content": results})
        else:
            stop_reason = "max_tool_rounds"  # the model kept asking for tools: give up without an answer

        text = "" if stop_reason == "max_tool_rounds" else "".join(b.get("text", "") for b in message["content"])
        raw = "" if stop_reason == "max_tool_rounds" else "".join(b.get("text", "") for b in message["content"])
        reasoning = " ".join(m.group(0) for m in _THINKING.finditer(raw)).strip()
        return LLMResponse(
            text=_THINKING.sub("", raw).strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_s=round(time.perf_counter() - start, 3),
            model=self.model_id,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            reasoning=reasoning,
        )


if __name__ == "__main__":
    import sys

    llm = BedrockClient()
    if "--tools" in sys.argv:
        from src.assistant.tools import run_tool, tool_config

        reply = llm.chat(
            [{"role": "user", "content": "Can I open an account if I live in Poland, and how fast is card delivery?"}],
            system="You are a support assistant for a fictional bank. Use the tools for facts.",
            temperature=0.0,
            tool_config=tool_config(),
            run_tool=run_tool,
        )
    else:
        reply = llm.chat(
            [{"role": "user", "content": "My card hasn't arrived yet. What should I do? Answer in two sentences."}],
            system="You are a support assistant for a fictional bank.",
        )
    print(reply.text)
    print(reply)
