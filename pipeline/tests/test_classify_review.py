# ruamel.yaml nodes are untyped.
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
import datetime as dt
import json
import shutil
from pathlib import Path

import pytest

from politdrift import mapping_io
from politdrift.classify import (
    LLMConfig,
    Proposal,
    VoteInput,
    build_messages,
    classify_votes,
    load_examples,
    normalize_topic,
    parse_response,
    select_votes,
    to_mapping,
)
from politdrift.mappings import load_file, validate_tree
from politdrift.models import MappingSource, Session, Vote
from politdrift.review import Action, apply, describe, pending, replace_with
from politdrift.store import Store

REPO_MAPPING = Path(__file__).parents[2] / "data" / "mappings" / "nr" / "52.yaml"
VOTE = VoteInput(
    business="23.3833",
    title="Die Stärkeproduktion in der Schweiz erhalten",
    subject=None,
    meaning_yes="Antrag der Mehrheit (Annahme der Motion)",
    meaning_no="Antrag der Minderheit (Ablehnung der Motion)",
)
GOOD = json.dumps(
    {
        "axes": [{"axis": "wirtschaft_liberal", "direction": -1, "weight": 0.5}],
        "topics": ["Landwirtschaft"],
        "confidence": 0.7,
        "contested": False,
        "rationale": "Subvention für die Landwirtschaft.",
    }
)


def quiet(_: str) -> None:
    pass


def test_examples_are_valid_and_prompt_is_complete() -> None:
    examples = load_examples()
    assert len(examples) >= 3
    msgs = build_messages(VOTE, examples)
    assert msgs[0]["role"] == "system"
    assert "Bedeutung Ja" in msgs[0]["content"]
    assert msgs[-1]["content"].endswith("Ablehnung der Motion)")
    assert len(msgs) == 1 + 2 * len(examples) + 1


def test_parse_response_tolerates_think_blocks_and_fences() -> None:
    p = parse_response(f"<think>hmm {{x}}</think>\n```json\n{GOOD}\n```")
    assert p.axes[0].direction == -1
    assert p.topics == ["landwirtschaft"]


@pytest.mark.parametrize("bad", ["no json here", '{"axes": [{"axis": "recht_ordnung"}]}'])
def test_parse_response_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_response(bad)


def test_normalize_topic() -> None:
    assert normalize_topic("Gesundheit Prävention") == "gesundheit_praevention"
    assert normalize_topic("  Öffentlicher Verkehr! ") == "oeffentlicher_verkehr"


def test_to_mapping_marks_llm_unreviewed() -> None:
    m = to_mapping(31570, VOTE, parse_response(GOOD), "test-model")
    assert m.source is MappingSource.LLM
    assert not m.reviewed
    assert "test-model" in (m.note or "")
    empty = to_mapping(1, VOTE, Proposal(confidence=0.9), "m")
    assert empty.axes == [] and empty.topics == ["kein_achsenbezug"]


def test_classify_retries_once_with_feedback() -> None:
    answers = iter(['{"axes": [{"axis": "recht_ordnung", "direction": 1, "weight": 1}]}', GOOD])
    seen: list[int] = []

    def fake(messages: list[dict[str, str]]) -> str:
        seen.append(len(messages))
        return next(answers)

    res = classify_votes([(31570, VOTE)], fake, "m", log=quiet)
    assert res.errors == []
    assert len(res.mappings) == 1
    assert seen[1] == seen[0] + 2  # previous answer + correction request


def test_classify_reports_persistent_errors() -> None:
    res = classify_votes([(1, VOTE)], lambda _: "nope", "m", log=quiet)
    assert res.mappings == [] and "vote 1" in res.errors[0]


def test_llm_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLITDRIFT_LLM_MODEL", raising=False)
    monkeypatch.setenv("POLITDRIFT_LLM_BASE_URL", "https://example.test/v1/")
    cfg = LLMConfig.from_env()
    assert cfg.base_url == "https://example.test/v1"
    assert LLMConfig.from_env("other").model == "other"


def test_select_votes_scopes() -> None:
    s = Store(":memory:")
    s.put_sessions(
        [
            Session(
                session_id="1",
                body_id="nr",
                legislature=52,
                name="S",
                start=dt.date(2024, 3, 1),
                end=dt.date(2024, 3, 20),
            )
        ]
    )

    def vote(vid: int, business: str, title: str, subject: str | None) -> Vote:
        return Vote(
            vote_id=vid,
            body_id="nr",
            session_id="1",
            date=dt.datetime(2024, 3, 2, tzinfo=dt.UTC),
            business=business,
            title=title,
            subject=subject,
        )

    s.put_votes(
        [
            vote(1, "24.001", "A", "Schlussabstimmung"),
            vote(2, "24.002", "B", "Vote final"),
            vote(3, "24.3001", "M", None),
            vote(4, "00.000", "Ordnungsantrag", None),
            vote(5, "24.001", "A", "Gesamtabstimmung"),
        ]
    )

    def ids(scope: str, exclude: set[int] | None = None) -> list[int]:
        return [v for v, _ in select_votes(s, ["1"], exclude or set(), scope, None)]

    assert ids("final") == [1, 2]
    assert ids("final", {1}) == [2]
    assert ids("motions") == [3]
    assert ids("overall") == [5]
    assert 4 not in ids("all")
    with pytest.raises(ValueError, match="scope"):
        ids("nope")


def test_mapping_io_round_trip_preserves_comments(tmp_path: Path) -> None:
    path = tmp_path / "nr" / "52.yaml"
    path.parent.mkdir()
    shutil.copy(REPO_MAPPING, path)
    original = path.read_text(encoding="utf-8")
    mapping_io.save(path, mapping_io.load(path))
    assert path.read_text(encoding="utf-8") == original

    m = to_mapping(31570, VOTE, parse_response(GOOD), "m")
    assert mapping_io.append(path, [m, m]) == 1
    assert mapping_io.append(path, [m]) == 0
    text = path.read_text(encoding="utf-8")
    assert text.startswith(original.split("\n- vote_id")[0])  # header comments intact
    assert validate_tree(tmp_path).ok
    assert [x.vote_id for x in load_file(path)] == [35460, 31570]


def test_review_accept_no_axis_and_edit(tmp_path: Path) -> None:
    path = tmp_path / "nr" / "52.yaml"
    m = to_mapping(31570, VOTE, parse_response(GOOD), "m")
    mapping_io.append(path, [m, to_mapping(2, VOTE, parse_response(GOOD), "m")])
    data = mapping_io.load(path)
    todo = pending(list(data))
    assert len(todo) == 2
    today = dt.date(2026, 11, 7)

    apply(todo[0], Action.ACCEPT, "michschl", today)
    assert todo[0]["reviewed"] is True and todo[0]["reviewed_by"] == "michschl"

    edited = dict(todo[1])
    edited["axes"] = [{"axis": "umwelt_ausgebaut", "direction": 1, "weight": 0.4}]
    replace_with(todo[1], edited, "michschl", today)
    assert todo[1]["source"] == "manual"  # axes changed by a human
    with pytest.raises(ValueError, match="vote_id"):
        replace_with(todo[1], {**edited, "vote_id": 9}, "michschl", today)

    mapping_io.save(path, data)
    assert validate_tree(tmp_path).ok
    assert pending(list(mapping_io.load(path))) == []
    assert "Ja → tief" in describe(todo[0], None)

    node = mapping_io.to_node(to_mapping(3, VOTE, parse_response(GOOD), "m"))
    apply(node, Action.NO_AXIS, "michschl", today)
    assert node["axes"] == [] and node["topics"] == ["landwirtschaft"]
