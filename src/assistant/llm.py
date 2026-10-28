"""LLM clients behind one interface: Bedrock now, Ollama can be added as another class.

Quick check from the project root:  python -m src.assistant.llm
"""

import os
import time
from dataclasses import dataclass
from typing import Protocol

import boto3

DEFAULT_MODEL = os.getenv("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0")
DEFAULT_REGION = os.getenv("AWS_REGION", "eu-north-1")


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str
    stop_reason: str = ""


class LLMClient(Protocol):
    name: str

    def chat(
        self, messages: list[dict], system: str | None = None, max_tokens: int = 400, temperature: float = 0.2
    ) -> LLMResponse: ...

class BedrockClient:
    name = 'bedrock'

    def __init__(self, model_id: str = DEFAULT_MODEL, region: str = DEFAULT_REGION, client=None):
        self.model_id = model_id
        # `client` can be passed directly (a fake one in tests); otherwise a real boto3 client is created.
        self.client = client if client is not None else boto3.client("bedrock-runtime", region_name=region)

    def chat(
        self, messages: list[dict], system: str | None = None, max_tokens: int = 400, temperature: float = 0.2
    ) -> LLMResponse:
        request = {
            "modelId": self.model_id,
            "messages": [{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            request["system"] = [{"text": system}]
        start = time.perf_counter()
        response = self.client.converse(**request)
        latency = time.perf_counter() - start
        blocks = response["output"]["message"]["content"]
        usage = response.get("usage", {})
        return LLMResponse(
            text="".join(block.get("text", 0) for block in blocks),
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            latency_s=round(latency, 3),
            model=self.model_id,
            stop_reason=response.get("stopReason", ""),
        )


if __name__ == "__main__":
    llm = BedrockClient()
    reply = llm.chat(
        [{"role": "user", "content": "My card hasn't arrived yet. What should I do? Answer in two sentences."}],
        system="You are a support assistant for a fictional bank.",
    )
    print(reply.text)
    print(reply)