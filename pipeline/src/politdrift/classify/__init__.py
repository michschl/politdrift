"""LLM-assisted mapping proposals (KONZEPT 2.4).

Any OpenAI-compatible chat completions endpoint works (default: Infomaniak AI Tools).
Configuration only via environment variables, never in the repository:

- POLITDRIFT_LLM_BASE_URL  e.g. https://api.infomaniak.com/2/ai/<product_id>/openai/v1
- POLITDRIFT_LLM_MODEL     default mistralai/Ministral-3-14B-Instruct-2512 (ADR 0008)
- POLITDRIFT_LLM_API_KEY   bearer token (in Claude Code cloud sessions the proxy injects it)

Proposals are written with source: llm and reviewed: false. They never enter profiles until a
human reviews them (KONZEPT 2.2 rule 4).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from politdrift.models import AxisAssignment, AxisMapping, MappingSource, Slug
from politdrift.store import Store

HERE = Path(__file__).parent
PROMPT_PATH = HERE / "prompt.md"
EXAMPLES_PATH = HERE / "examples.yaml"
PROMPT_VERSION = "2026-11-07"

DEFAULT_BASE_URL = "https://api.infomaniak.com/2/ai/112859/openai/v1"
DEFAULT_MODEL = "mistralai/Ministral-3-14B-Instruct-2512"  # see ADR 0008

SCOPES: dict[str, str] = {
    "final": "subject IN ('Schlussabstimmung', 'Vote final')",
    "overall": "subject IN ('Gesamtabstimmung', 'Vote sur l''ensemble')",
    "motions": "subject IS NULL AND business <> '00.000'",
    "all": "business IS NULL OR business <> '00.000'",
}


class VoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business: str | None
    title: str
    subject: str | None
    meaning_yes: str | None
    meaning_no: str | None


class Proposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    axes: list[AxisAssignment] = Field(default_factory=list[AxisAssignment], max_length=3)
    topics: list[Slug] = Field(default_factory=list[Slug])
    confidence: float = Field(ge=0, le=1)
    contested: bool = False
    rationale: str = ""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str

    @classmethod
    def from_env(cls, model: str | None = None) -> LLMConfig:
        return cls(
            base_url=os.environ.get("POLITDRIFT_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            model=model or os.environ.get("POLITDRIFT_LLM_MODEL", DEFAULT_MODEL),
            api_key=os.environ.get("POLITDRIFT_LLM_API_KEY", "proxy-injected"),
        )


Complete = Callable[[list[dict[str, str]]], str]


def openai_compatible(config: LLMConfig, client: httpx.Client | None = None) -> Complete:
    http = client or httpx.Client(timeout=180)

    def complete(messages: list[dict[str, str]]) -> str:
        resp = http.post(
            f"{config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {config.api_key}"},
            json={
                "model": config.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4000,
            },
        )
        resp.raise_for_status()
        data: Any = resp.json()
        return str(data["choices"][0]["message"]["content"] or "")

    return complete


def load_examples(path: Path = EXAMPLES_PATH) -> list[tuple[VoteInput, Proposal]]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    items = cast(list[dict[str, Any]], raw)
    return [
        (VoteInput.model_validate(e["vote"]), Proposal.model_validate(e["answer"])) for e in items
    ]


def render_vote(v: VoteInput) -> str:
    return "\n".join(
        [
            f"Geschäft: {v.business or '-'}",
            f"Titel: {v.title}",
            f"Gegenstand: {v.subject or '-'}",
            f"Bedeutung Ja: {v.meaning_yes or '-'}",
            f"Bedeutung Nein: {v.meaning_no or '-'}",
        ]
    )


def build_messages(
    vote: VoteInput, examples: Iterable[tuple[VoteInput, Proposal]]
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8")}]
    for ex_vote, ex_answer in examples:
        messages.append({"role": "user", "content": render_vote(ex_vote)})
        messages.append(
            {"role": "assistant", "content": ex_answer.model_dump_json(exclude_defaults=False)}
        )
    messages.append({"role": "user", "content": render_vote(vote)})
    return messages


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "é": "e", "è": "e", "à": "a"})


def normalize_topic(topic: str) -> str:
    t = topic.lower().translate(_UMLAUTS)
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return re.sub(r"_+", "_", t)


def parse_response(text: str) -> Proposal:
    """Extract the JSON object from a model answer (tolerates <think> blocks and code fences)."""
    cleaned = _THINK_RE.sub("", text)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"no JSON object in model answer: {text[:200]!r}")
    try:
        data: Any = json.loads(cleaned[start : end + 1])
        if isinstance(data, dict):
            obj = cast(dict[str, Any], data)
            raw_topics = obj.get("topics")
            if isinstance(raw_topics, list):
                topics = cast(list[Any], raw_topics)
                obj["topics"] = [t for t in (normalize_topic(str(x)) for x in topics) if t]
        return Proposal.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as err:
        raise ValueError(f"invalid proposal: {err}") from err


def to_mapping(vote_id: int, vote: VoteInput, p: Proposal, model: str) -> AxisMapping:
    topics = p.topics
    if not p.axes and not topics:
        topics = ["kein_achsenbezug"]
    return AxisMapping(
        vote_id=vote_id,
        business=vote.business
        if vote.business and re.match(r"^\d{2}\.\d{3,4}$", vote.business)
        else None,
        title=" \u2013 ".join(x for x in (vote.title, vote.subject) if x),
        axes=p.axes,
        topics=topics,
        source=MappingSource.LLM,
        confidence=p.confidence,
        contested=p.contested,
        reviewed=False,
        note=f"{p.rationale.strip()} [{model}, prompt {PROMPT_VERSION}, {dt.date.today()}]".strip(),
    )


def select_votes(
    store: Store, session_ids: list[str], exclude: set[int], scope: str, limit: int | None
) -> list[tuple[int, VoteInput]]:
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; use one of {', '.join(SCOPES)}")
    rows = store.con.execute(
        "SELECT vote_id, business, title, subject, meaning_yes, meaning_no FROM votes "  # noqa: S608
        f"WHERE session_id IN (SELECT unnest(?::TEXT[])) AND ({SCOPES[scope]}) "
        "ORDER BY date, vote_id",
        [session_ids],
    ).fetchall()
    out: list[tuple[int, VoteInput]] = []
    for vid, business, title, subject, yes, no in rows:
        if int(vid) in exclude:
            continue
        out.append(
            (
                int(vid),
                VoteInput(
                    business=business,
                    title=title or "",
                    subject=subject,
                    meaning_yes=yes,
                    meaning_no=no,
                ),
            )
        )
        if limit is not None and len(out) >= limit:
            break
    return out


@dataclass
class ClassifyResult:
    mappings: list[AxisMapping]
    errors: list[str]


def classify_votes(
    votes: Iterable[tuple[int, VoteInput]],
    complete: Complete,
    model: str,
    examples: list[tuple[VoteInput, Proposal]] | None = None,
    log: Callable[[str], None] = print,
) -> ClassifyResult:
    examples = load_examples() if examples is None else examples
    result = ClassifyResult(mappings=[], errors=[])
    for vid, vote in votes:
        try:
            messages = build_messages(vote, examples)
            answer = complete(messages)
            try:
                proposal = parse_response(answer)
            except ValueError as first:
                # one correction round: show the model its error
                messages += [
                    {"role": "assistant", "content": answer},
                    {
                        "role": "user",
                        "content": f"Die Antwort ist ungültig: {str(first)[:500]}\n"
                        "Antworte nur mit dem korrigierten JSON-Objekt. Erlaubte Achsen-Keys "
                        "stehen in der Tabelle; Themen nur a-z, 0-9 und _.",
                    },
                ]
                proposal = parse_response(complete(messages))
            m = to_mapping(vid, vote, proposal, model)
        except (httpx.HTTPError, ValueError, KeyError) as err:
            result.errors.append(f"vote {vid}: {str(err).splitlines()[0]}")
            continue
        axes = ", ".join(
            f"{a.axis.value}{'+' if a.direction > 0 else '-'}{a.weight}" for a in m.axes
        )
        log(f"{vid} {vote.business or ''} {vote.subject or ''}: {axes or 'keine Achse'}")
        result.mappings.append(m)
    return result
