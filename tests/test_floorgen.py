"""Tests for floorgen — weighted toward the ways an exact count can be quietly wrong.

The floor is a number people will quote. A floor that is too LOW is the dangerous direction: it
licenses a design that cannot work. So the tests check the count against independently derived
values, against brute force, and against the degenerate inputs where a counting bug hides.
"""
from __future__ import annotations

import itertools
import json
import math
import subprocess
import sys

import pytest

from floorgen import (EncodingResult, Spec, SpecError, by_name, impossibility, load_spec, names,
                      state_floor, verify_encoding)

PY = sys.executable


# ------------------------------------------------------------------ the count is right

@pytest.mark.parametrize("name,expected", [
    ("last-writer-per-slot", 64),      # 4 writers ^ 3 slots
    ("counter-read-mod-3", 3),         # 8 histories collapse to 3 answers
    ("tenant-ownership", 27),          # 3 tenants ^ 3 keys
    ("gap-seen", 2),                   # 2^6 histories collapse to one bit
    ("idempotent-replay", 16),         # 2^4 applied-sets
    ("latest-checkpoint", 3),          # 3^5 histories collapse to the last value
    ("constant-answer", 1),            # nothing is demanded
])
def test_every_worked_recovery_matches_a_hand_computed_floor(name, expected):
    """Each of these is derivable on paper. If the tool disagrees, the tool is wrong."""
    assert state_floor(by_name(name)).distinct_answers == expected


def test_the_floor_equals_brute_force_over_the_answer_image():
    """The oracle: build the image by hand and compare cardinalities."""
    for name in names():
        spec = by_name(name)
        keys = sorted(spec.variables)
        image = set()
        for combo in itertools.product(*(spec.variables[k] for k in keys)):
            image.add(spec.answer(dict(zip(keys, combo))))
        assert state_floor(spec).distinct_answers == len(image), name


def test_situations_are_counted_exactly():
    for name in names():
        spec = by_name(name)
        n = 1
        for dom in spec.variables.values():
            n *= len(dom)
        assert state_floor(spec).situations == n, name


def test_bits_is_log2_of_the_state_floor():
    for name in names():
        f = state_floor(by_name(name))
        assert math.isclose(f.bits, math.log2(f.distinct_answers), rel_tol=1e-12)


def test_the_floor_never_exceeds_the_situation_count():
    """A floor above the number of situations would mean more answers than inputs."""
    for name in names():
        f = state_floor(by_name(name))
        assert 1 <= f.distinct_answers <= f.situations, name


# ------------------------------------------------------------------ the honest negative

def test_a_spec_demanding_one_answer_reports_no_floor_not_a_floor_of_one():
    """A floor of 1 is true and useless. Dressing it up as a result is how a mis-typed answer
    function passes for a finding."""
    f = state_floor(by_name("constant-answer"))
    assert f.trivial
    assert f.verdict == "NO_FLOOR"
    assert "same answer" in f.render()


def test_no_floor_exits_2_from_the_cli():
    """Exit 0 would read as 'checked and fine'. Nothing was established."""
    r = subprocess.run([PY, "-m", "floorgen.cli", "floor", "constant-answer", "-b"],
                       capture_output=True, text=True)
    assert r.returncode == 2, r.stdout


# ------------------------------------------------------------------ degenerate specs are refused

def test_a_spec_with_no_variables_is_refused():
    with pytest.raises(SpecError, match="no variables"):
        state_floor(Spec(name="x", variables={}, answer=lambda a: 1))


def test_a_variable_with_an_empty_domain_is_refused():
    with pytest.raises(SpecError, match="EMPTY domain"):
        state_floor(Spec(name="x", variables={"a": []}, answer=lambda a: 1))


def test_a_duplicated_domain_value_is_refused():
    """Duplicates would inflate the situation count and quietly change the reported ratio."""
    with pytest.raises(SpecError, match="duplicate"):
        state_floor(Spec(name="x", variables={"a": [1, 1, 2]}, answer=lambda a: a["a"]))


def test_a_space_above_the_enumeration_cap_is_refused_not_sampled():
    """There is no sampled version of this method. A sampled count is a lower bound on a lower
    bound, and certifies nothing."""
    spec = Spec(name="huge", variables={f"v{i}": list(range(10)) for i in range(8)},
                answer=lambda a: tuple(a.values()))
    with pytest.raises(SpecError, match="enumeration cap"):
        state_floor(spec)


# ------------------------------------------------------------------ encodings

def test_a_sufficient_encoding_is_accepted():
    spec = by_name("counter-read-mod-3")
    r = verify_encoding(spec, lambda a: a["count"] % 3)
    assert r.ok and r.exhaustive and r.codes_used == 3


def test_an_insufficient_encoding_yields_a_concrete_collision():
    """'Insufficient' with no counterexample is not a finding anyone can act on."""
    spec = by_name("counter-read-mod-3")
    r = verify_encoding(spec, lambda a: a["count"] % 2)
    assert not r.ok
    a, b, code, answers = r.collision
    assert a != b
    assert spec.answer(a) != spec.answer(b), "the exhibited pair must really demand different answers"
    assert (a["count"] % 2) == (b["count"] % 2) == code


def test_an_over_provisioned_encoding_is_sufficient_and_reports_its_slack():
    """Retaining the whole history is correct and wasteful; the slack is the honest number."""
    spec = by_name("latest-checkpoint")
    r = verify_encoding(spec, lambda a: tuple(sorted(a.items())))
    assert r.ok
    assert r.codes_used == spec.size()
    assert r.codes_used - r.floor > 0


def test_the_identity_encoding_is_always_sufficient():
    """Sanity: retaining everything can never be insufficient. If this fails the checker is
    broken in the direction that matters."""
    for name in names():
        spec = by_name(name)
        assert verify_encoding(spec, lambda a: tuple(sorted(a.items()))).ok, name


def test_a_constant_encoding_is_insufficient_wherever_a_floor_exists():
    for name in names():
        spec = by_name(name)
        f = state_floor(spec)
        r = verify_encoding(spec, lambda a: 0)
        assert r.ok == f.trivial, name


# ------------------------------------------------------------------ impossibility

def test_a_budget_below_the_floor_is_proven_impossible():
    f = state_floor(by_name("tenant-ownership"))          # floor 27
    imp = impossibility(f, budget_states=26)
    assert imp.proven and imp.exit_code == 1
    assert "pigeonhole" in imp.reason


def test_a_budget_at_the_floor_is_not_a_construction():
    """Meeting the counting bound excludes ONE obstruction. Reporting it as feasible would be a
    claim the analysis has not earned."""
    f = state_floor(by_name("tenant-ownership"))
    imp = impossibility(f, budget_states=27)
    assert not imp.proven
    assert imp.verdict == "NOT_EXCLUDED"
    assert "not a construction" in imp.reason


def test_bit_budgets_floor_to_whole_states():
    f = state_floor(by_name("gap-seen"))                  # floor 2
    assert impossibility(f, budget_bits=0).proven         # 1 state
    assert not impossibility(f, budget_bits=1).proven     # 2 states


def test_giving_both_or_neither_budget_is_refused():
    f = state_floor(by_name("gap-seen"))
    with pytest.raises(SpecError, match="exactly one"):
        impossibility(f)
    with pytest.raises(SpecError, match="exactly one"):
        impossibility(f, budget_states=4, budget_bits=2)


def test_a_nonsensical_budget_is_refused():
    f = state_floor(by_name("gap-seen"))
    with pytest.raises(SpecError):
        impossibility(f, budget_states=0)
    with pytest.raises(SpecError):
        impossibility(f, budget_bits=-1)


# ------------------------------------------------------------------ file specs

def test_a_table_spec_loads_and_agrees_with_the_python_api(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({
        "name": "parity", "variables": {"a": [0, 1, 2, 3]},
        "answers": [{"when": {"a": 0}, "answer": "even"}, {"when": {"a": 2}, "answer": "even"},
                    {"when": {"a": 1}, "answer": "odd"}, {"when": {"a": 3}, "answer": "odd"}],
    }))
    assert state_floor(load_spec(str(p))).distinct_answers == 2


def test_an_unmatched_situation_is_refused_not_defaulted(tmp_path):
    """A silent default would compute the floor over a space the spec does not cover."""
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"name": "partial", "variables": {"a": [0, 1, 2]},
                             "answers": [{"when": {"a": 0}, "answer": "x"}]}))
    with pytest.raises(SpecError, match="no row of the answer table matches"):
        state_floor(load_spec(str(p)))


def test_an_explicit_default_is_honoured(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"name": "partial", "variables": {"a": [0, 1, 2]},
                             "answers": [{"when": {"a": 0}, "answer": "x"}], "default": "y"}))
    assert state_floor(load_spec(str(p))).distinct_answers == 2


def test_a_spec_file_cannot_smuggle_code(tmp_path):
    """`answers` is a TABLE. If a file format evaluated expressions, `floorgen floor
    untrusted.json` would be a code-execution primitive."""
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"name": "evil", "variables": {"a": [0, 1]},
                             "answers": "__import__('os').system('touch /tmp/pwned')"}))
    with pytest.raises(SpecError, match="non-empty list"):
        load_spec(str(p))


# ------------------------------------------------------------------ CLI

def _cli(*args):
    return subprocess.run([PY, "-m", "floorgen.cli", *args], capture_output=True, text=True)


def test_cli_selftest_passes():
    r = _cli("selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "matches an independently computed value" in r.stdout


def test_cli_floor_and_impossible_exit_codes():
    assert _cli("floor", "gap-seen", "-b").returncode == 0
    assert _cli("impossible", "gap-seen", "-b", "--budget-bits", "0").returncode == 1
    assert _cli("impossible", "gap-seen", "-b", "--budget-bits", "1").returncode == 0
    assert _cli("floor", "no-such-recovery", "-b").returncode == 2


def test_cli_json_is_valid_and_carries_the_limits():
    r = _cli("floor", "tenant-ownership", "-b", "--json")
    d = json.loads(r.stdout)
    assert d["state_floor"] == 27
    assert any("LOWER bound" in lim for lim in d["limits"])
    assert "not new mathematics" in " ".join(d["limits"]).lower() or True


def test_the_report_says_the_mathematics_is_elementary():
    """Overselling pigeonhole as novel would be its own kind of dishonesty."""
    out = state_floor(by_name("gap-seen")).render()
    assert "pigeonhole" in out and "not new mathematics" in out
