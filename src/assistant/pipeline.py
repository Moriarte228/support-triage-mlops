"""Answer a customer question: retrieve sections, choose a route, ask the LLM.

Routes (thresholds picked on the validation set):
    answer   - the retriever is confident: the top section goes to the LLM
    clarify  - the top two sections are almost tied: the LLM asks a clarifying question
    fallback - low confidence: the top three sections go to the LLM

Run from the project root:  python -m src.assistant.pipeline "I want to close my account"
"""

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.assistant.kb.store import load_chunks
from src.assistant.llm import BedrockClient, LLMClient, ToolRunner
from src.assistant.retrieval import Hit, Retriever, get_retriever
from src.assistant.tools import run_tool, tool_config, tools_for_texts
from src.preprocess import normalize

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"
INDEX = ROOT / "data" / "index" / "heading" / "chunks.jsonl"

AMBIGUOUS_NOTE = "The question is ambiguous between the sections above."
_SOURCES = re.compile(r"SOURCES:[ \t]*([^\n]*)", flags=re.IGNORECASE)  # the model may put it on the last line or not
_SECTION_ID = re.compile(r"^[\w-]+#[\w-]+$")

@dataclass
class RouteConfig:
    answer_min_score: float = 0.30  # top-1 score at or above this: answer from one section
    clarify_max_gap: float = 0.05   # top-1 minus top-2 below this ...
    clarify_min_score: float = 0.15  # ... and top-1 at least this: ask a clarifying question
    fallback_k: int = 3             # sections given to the LLM when unsure


@dataclass
class AnswerResult:
    query: str
    answer: str
    route: str
    sections: list[str]   # ids of the sections given to the LLM
    cited: list[str]      # ids the LLM listed on its SOURCES line
    confidence: float     # score of the top section
    input_tokens: int
    output_tokens: int
    latency_s: float      # whole answer: retrieval + LLM
    llm_latency_s: float
    model: str
    prompt_version: str
    tools_offered: list[str] = field(default_factory=list)  # tools the model was allowed to call
    tool_calls: list[dict] = field(default_factory=list)     # tools the model used: name, input, output

    def to_dict(self) -> dict:
        return asdict(self)


def choose_route(hits: list[Hit], config: RouteConfig) -> str:
    """Pick 'answer', 'clarify' or 'fallback' from the retrieval scores."""
    if not hits:
        return "fallback"
    top1 = hits[0].score
    top2 = hits[1].score if len(hits) > 1 else 0.0
    if top1 - top2 < config.clarify_max_gap and top1 >= config.clarify_min_score:
        return "clarify"
    if top1 >= config.answer_min_score:
        return "answer"
    return "fallback"


def sections_for_route(hits: list[Hit], route: str, config: RouteConfig) -> list[Hit]:
    """How many of the top sections the LLM sees on each route."""
    n = {"answer": 1, "clarify": 2}.get(route, config.fallback_k)
    return hits[:n]


def build_user_message(query: str, hits: list[Hit], route: str) -> str:
    sections = "\n".join(f'<section id="{hit.chunk.id}">\n{hit.chunk.text}\n</section>' for hit in hits)
    message = f"<context>\n{sections}\n</context>\n\n<question>\n{query}\n</question>"
    if route == "clarify":
        message += f"\n\n{AMBIGUOUS_NOTE}"
    return message


def parse_sources(text: str) -> tuple[str, list[str]]:
    """Split the reply into the answer and the section ids from its last SOURCES: list."""
    matches = list(_SOURCES.finditer(text))
    if not matches:
        return text.strip(), []
    last = matches[-1]
    parts = [part.strip(" .`*") for part in last.group(1).split(",")]
    parts = [part for part in parts if part]
    ids = [part for part in parts if _SECTION_ID.match(part)]
    if not ids and [part.lower() for part in parts] != ["none"]:
        return text.strip(), []  # "sources:" inside an ordinary sentence, not our list
    answer = (text[: last.start()] + text[last.end():]).strip()
    return answer, ids

def log_answer(result: AnswerResult) -> None:
    """One JSON line per answer. The answer text is not logged; digits in the query are masked."""
    record = {k: v for k, v in result.to_dict().items() if k not in ("query", "answer", "tool_calls")}
    record["query"] = normalize(result.query)
    record["tools"] = [{"name": call["name"], "input": call["input"]} for call in result.tool_calls]
    logger.info(json.dumps({"event": "answer", **record}))

    unknown = sorted(set(result.cited) - set(result.sections))
    if unknown:
        logger.warning(json.dumps({"event": "unknown_sources", "query": record["query"], "cited": unknown}))


def load_prompt(version: str) -> str:
    return (PROMPTS_DIR / f"{version}.txt").read_text(encoding="utf-8")


class Assistant:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMClient,
        prompt_version: str = "answer_v1",
        config: RouteConfig | None = None,
        tool_runner: ToolRunner | None = None,
        tool_selection: str = "sections",
    ):
        self.retriever = retriever
        self.llm = llm
        self.prompt_version = prompt_version
        self.system_prompt = load_prompt(prompt_version)
        self.config = config or RouteConfig()
        self.tool_runner = tool_runner        # runs the tool the model asked for; None: no tools at all
        self.tool_selection = tool_selection  # "sections": only the tools the sections refer to; "all": every tool

    def tools_for(self, route: str, used: list[Hit]) -> dict | None:
        """toolConfig for this answer, or None when the model gets no tools."""
        if self.tool_runner is None:
            return None
        if self.tool_selection == "all" or route != "answer":
            return tool_config()  # unsure which section is right: keep every tool as a safety net
        return tool_config(tools_for_texts([hit.chunk.text for hit in used]))

    def answer(self, query: str) -> AnswerResult:
        start = time.perf_counter()
        hits = self.retriever.retrieve(query, k=self.config.fallback_k)
        route = choose_route(hits, self.config)
        used = sections_for_route(hits, route, self.config)
        tools = self.tools_for(route, used)

        reply = self.llm.chat(
            [{"role": "user", "content": build_user_message(query, used, route)}],
            system=self.system_prompt,
            temperature=0.0 if tools else 0.2,  # tool calls are more reliable with greedy decoding
            tool_config=tools,
            run_tool=self.tool_runner if tools else None,
        )
        text, cited = parse_sources(reply.text)

        result = AnswerResult(
            query=query,
            answer=text,
            route=route,
            sections=[hit.chunk.id for hit in used],
            cited=cited,
            confidence=round(hits[0].score, 4) if hits else 0.0,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            latency_s=round(time.perf_counter() - start, 3),
            llm_latency_s=reply.latency_s,
            model=reply.model,
            prompt_version=self.prompt_version,
            tools_offered=[tool["toolSpec"]["name"] for tool in tools["tools"]] if tools else [],
            tool_calls=reply.tool_calls,
        )
        log_answer(result)
        return result


def build_assistant(prompt_version: str = "answer_v3", use_tools: bool = True) -> Assistant:
    """The default assistant: intent retriever over the heading index + Bedrock + database tools."""
    retriever = get_retriever("intent", load_chunks(INDEX))
    tool_runner = run_tool if use_tools else None
    return Assistant(retriever, BedrockClient(), prompt_version=prompt_version, tool_runner=tool_runner)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logging.getLogger("botocore").setLevel(logging.WARNING)
    question = " ".join(sys.argv[1:]) or "I want to close my account"
    result = build_assistant().answer(question)
    print(result.answer)
    print()
    print(json.dumps({k: v for k, v in result.to_dict().items() if k != "answer"}, indent=2))
