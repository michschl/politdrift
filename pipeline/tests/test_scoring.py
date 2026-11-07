import pytest

from politdrift.axes import AXIS_ORDER, Axis
from politdrift.models import Decision
from politdrift.scoring import (
    N_MIN,
    WeightedBallot,
    axis_score,
    ballot_value,
    coverage,
    distance,
    drift,
)

Y, N, A = Decision.YES, Decision.NO, Decision.ABSTAIN


def wb(decision: Decision, direction: int = 1, weight: float = 1.0) -> WeightedBallot:
    return WeightedBallot(decision=decision, direction=direction, weight=weight)


def test_axis_order_matches_concept() -> None:
    assert [a.value for a in AXIS_ORDER] == [
        "aussenpolitik_offen",
        "wirtschaft_liberal",
        "finanzen_restriktiv",
        "law_order",
        "migration_restriktiv",
        "umwelt_ausgebaut",
        "sozialstaat_ausgebaut",
        "gesellschaft_liberal",
    ]


def test_ballot_value() -> None:
    assert ballot_value(Y) == 1
    assert ballot_value(N) == -1
    for d in (Decision.ABSTAIN, Decision.ABSENT, Decision.EXCUSED, Decision.PRESIDENT):
        assert ballot_value(d) == 0


def test_all_yes_in_axis_direction_is_100() -> None:
    result = axis_score([wb(Y)] * N_MIN)
    assert result.score == pytest.approx(100)
    assert result.n == N_MIN


def test_all_no_in_axis_direction_is_0() -> None:
    assert axis_score([wb(N)] * N_MIN).score == pytest.approx(0)


def test_negative_direction_flips() -> None:
    assert axis_score([wb(Y, direction=-1)] * N_MIN).score == pytest.approx(0)
    assert axis_score([wb(N, direction=-1)] * N_MIN).score == pytest.approx(100)


def test_balanced_is_50() -> None:
    assert axis_score([wb(Y), wb(N)] * 4).score == pytest.approx(50)


def test_weights() -> None:
    # S = (1*1 - 0.5*1*6 ... ) checked by hand: 4 yes at w=1, 4 no at w=0.5
    # S = (4 - 2) / (4 + 2) = 1/3 -> score = (1/3 + 1) / 2 * 100 = 66.67
    ballots = [wb(Y, weight=1.0)] * 4 + [wb(N, weight=0.5)] * 4
    assert axis_score(ballots).score == pytest.approx(200 / 3)


def test_below_n_min_is_none() -> None:
    result = axis_score([wb(Y)] * (N_MIN - 1))
    assert result.score is None
    assert result.n == N_MIN - 1


def test_abstentions_do_not_count_towards_n_min() -> None:
    result = axis_score([wb(Y)] * (N_MIN - 1) + [wb(A)] * 10)
    assert result.score is None
    assert result.n == N_MIN - 1


def test_custom_n_min() -> None:
    assert axis_score([wb(Y)], n_min=1).score == pytest.approx(100)


def test_invalid_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        axis_score([wb(Y, direction=0)] * N_MIN)


def test_coverage_and_distance() -> None:
    soll = {Axis.LAW_ORDER: 80.0, Axis.UMWELT_AUSGEBAUT: 20.0, Axis.WIRTSCHAFT_LIBERAL: None}
    ist = {Axis.LAW_ORDER: 70.0, Axis.UMWELT_AUSGEBAUT: 40.0, Axis.WIRTSCHAFT_LIBERAL: 50.0}
    assert coverage(soll, ist) == pytest.approx(85)
    assert distance(soll, ist) == pytest.approx(15)
    assert coverage({}, ist) is None


def test_drift() -> None:
    before = {Axis.LAW_ORDER: 60.0, Axis.UMWELT_AUSGEBAUT: None}
    after = {Axis.LAW_ORDER: 45.0, Axis.UMWELT_AUSGEBAUT: 70.0}
    assert drift(before, after) == {Axis.LAW_ORDER: pytest.approx(-15)}
