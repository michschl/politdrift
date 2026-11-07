from pathlib import Path

import pytest
from typer.testing import CliRunner

from politdrift.cli import app
from politdrift.mappings import load_file, validate_tree

FIXTURES = Path(__file__).parent / "fixtures" / "mappings"
REPO_MAPPINGS = Path(__file__).parents[2] / "data" / "mappings"
runner = CliRunner()


def test_valid_tree() -> None:
    report = validate_tree(FIXTURES / "valid")
    assert report.ok, report.errors
    assert (report.files, report.mappings, report.reviewed) == (1, 1, 1)


def test_repository_mappings_are_valid() -> None:
    report = validate_tree(REPO_MAPPINGS)
    assert report.ok, report.errors


def test_invalid_tree_reports_every_problem() -> None:
    report = validate_tree(FIXTURES / "invalid")
    assert not report.ok
    text = "\n".join(report.errors)
    assert "vote_id=1" in text
    assert "axes.0.axis" in text
    assert "axes.0.direction" in text


def write(tmp_path: Path, body: str, rel: str = "nr/52.yaml") -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


BASE = """
- vote_id: 7
  title: "x"
  axes: [{axis: law_order, direction: 1, weight: 0.5}]
  source: manual
  confidence: 0.5
"""


def test_minimal_unreviewed_mapping_is_valid(tmp_path: Path) -> None:
    [m] = load_file(write(tmp_path, BASE))
    assert not m.reviewed


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ("  reviewed: true\n", "reviewed_by and reviewed_at"),
        ("  reviewed_by: someone\n", "reviewed is false"),
        ("  unknown_field: 1\n", "Extra inputs"),
        ("  source_url: x\n", "Extra inputs"),
        ("  business: '25-024'\n", "business"),
    ],
)
def test_rejects_bad_fields(tmp_path: Path, extra: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_file(write(tmp_path, BASE + extra))


@pytest.mark.parametrize(
    ("axes", "message"),
    [
        ("[{axis: law_order, direction: 1, weight: 0}]", "weight"),
        ("[{axis: law_order, direction: 1, weight: 1.5}]", "weight"),
        ("[{axis: law_order, direction: 2, weight: 0.5}]", "direction"),
        (
            "[{axis: law_order, direction: 1, weight: 0.5}, {axis: law_order, direction: -1, "
            "weight: 0.5}]",
            "only once",
        ),
        (
            "[{axis: a, direction: 1, weight: 0.1}, {axis: b, direction: 1, weight: 0.1}, "
            "{axis: c, direction: 1, weight: 0.1}, {axis: d, direction: 1, weight: 0.1}]",
            "axes",
        ),
        ("[]", "at least one axis or topic"),
    ],
)
def test_rejects_bad_axes(tmp_path: Path, axes: str, message: str) -> None:
    body = BASE.replace("[{axis: law_order, direction: 1, weight: 0.5}]", axes)
    with pytest.raises(ValueError, match=message):
        load_file(write(tmp_path, body))


def test_rejects_duplicate_vote_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate vote_id 7"):
        load_file(write(tmp_path, BASE + BASE))


def test_rejects_non_list(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="list"):
        load_file(write(tmp_path, "vote_id: 1\n"))


def test_rejects_wrong_layout(tmp_path: Path) -> None:
    write(tmp_path, BASE, rel="Nationalrat/52.yaml")
    write(tmp_path, BASE, rel="nr/legislatur52.yaml")
    report = validate_tree(tmp_path)
    assert len(report.errors) == 2


def test_cli_validate_ok() -> None:
    result = runner.invoke(app, ["validate", str(FIXTURES / "valid")])
    assert result.exit_code == 0, result.output
    assert "1 reviewed, 0 error(s)" in result.output


def test_cli_validate_fails_on_invalid() -> None:
    result = runner.invoke(app, ["validate", str(FIXTURES / "invalid")])
    assert result.exit_code == 1


@pytest.mark.parametrize("command", ["classify", "review"])
def test_stubs_exit_with_code_2(command: str) -> None:
    assert runner.invoke(app, [command]).exit_code == 2
