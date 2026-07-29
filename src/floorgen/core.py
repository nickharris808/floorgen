"""core.py — from "what must my system be able to recover?" to a proven state floor.

THE ARGUMENT, ONCE. If a system must answer a question about its past, and two different pasts
demand two different answers, then the system's retained state must differ between those two
pasts. Otherwise it is in the same state in both and must give the same answer in both, and one of
them is wrong.

Count the distinct answers the specification demands, and you have counted the states the system
must be able to occupy. That is the floor. It is pigeonhole, lifted pointwise. It is NOT new
mathematics, and this package says so in every report it emits -- the value here is that the
counting is done exactly, from a machine-readable spec, rather than argued in a design document.

WHAT MAKES IT EXACT. The floor is `|image(answer)|` -- the number of distinct answers over the
declared situations -- computed by evaluating the answer function at every situation. That is a
count, not an estimate, and it is only available because the spec is required to be FINITE and
ENUMERATED. A spec that cannot be enumerated gets a refusal, not a guess.

WHAT IT IS NOT. A floor is a lower bound on state. It is not an achievable design, not an upper
bound, and not a claim that any particular encoding attains it. `verify_encoding` answers the
separate question of whether a PROPOSED encoding is sufficient, and it answers it by exhaustive
check, not by argument.
"""
from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Hashable, Iterable, List, Optional, Sequence, Tuple

__all__ = ["Situation", "Spec", "Floor", "EncodingResult", "SpecError",
           "state_floor", "verify_encoding", "impossibility", "load_spec"]

SCHEMA = "floorgen-spec/v1"

# Enumerating a spec is the whole method, so the cap is a real limit rather than a tuning knob.
# Above it the answer is a refusal: an approximate floor is not a floor.
ENUMERATION_CAP = 5_000_000


class SpecError(ValueError):
    """The specification cannot be used. Never downgraded to a warning."""


@dataclass(frozen=True)
class Situation:
    """One concrete past the system might be in, and the answer the spec demands for it."""
    assignment: Tuple[Tuple[str, Any], ...]
    answer: Hashable

    @property
    def as_dict(self) -> Dict[str, Any]:
        return dict(self.assignment)


@dataclass
class Spec:
    """A finite, enumerated description of what must be distinguishable.

    `variables` — the axes of the situation space, each with an explicit finite domain.
    `answer`    — the quantity that must be recoverable, as a function of a situation.
    """
    name: str
    variables: Dict[str, List[Any]]
    answer: Callable[[Dict[str, Any]], Hashable]
    answer_source: str = ""
    notes: List[str] = field(default_factory=list)

    def size(self) -> int:
        n = 1
        for dom in self.variables.values():
            n *= len(dom)
        return n

    def validate(self) -> None:
        if not self.variables:
            raise SpecError(
                "the spec declares no variables, so the situation space is a single point. "
                "A floor of 1 is true and vacuous: it says a system needs at least one state. "
                "Refusing rather than reporting it.")
        for k, dom in self.variables.items():
            if not isinstance(dom, (list, tuple)) or len(dom) == 0:
                raise SpecError(f"variable {k!r} has an EMPTY domain: the situation space is "
                                f"empty, and every statement about an empty space is vacuously "
                                f"true")
            if len(set(map(_key, dom))) != len(dom):
                raise SpecError(f"variable {k!r} has duplicate values in its domain; the "
                                f"situation count would be wrong")
        n = self.size()
        if n > ENUMERATION_CAP:
            raise SpecError(
                f"the situation space has {n:,} points, above the enumeration cap of "
                f"{ENUMERATION_CAP:,}. The floor is computed by evaluating the answer at every "
                f"situation; there is no sampled version of this method, because a sampled "
                f"count is a lower bound on a lower bound and certifies nothing.")

    def situations(self) -> Iterable[Situation]:
        keys = sorted(self.variables)
        for combo in itertools.product(*(self.variables[k] for k in keys)):
            assign = dict(zip(keys, combo))
            yield Situation(tuple(sorted(assign.items(), key=lambda kv: kv[0])),
                            _key(self.answer(assign)))


def _key(v: Any) -> Hashable:
    """A hashable, order-stable key for an arbitrary answer value."""
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return tuple(_key(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((str(k), _key(x)) for k, x in v.items()))
    if isinstance(v, (set, frozenset)):
        return tuple(sorted(_key(x) for x in v))
    return repr(v)


@dataclass
class Floor:
    name: str
    situations: int
    distinct_answers: int
    bits: float
    exemplars: Dict[Any, Dict[str, Any]] = field(default_factory=dict)
    collapsing_pairs: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def trivial(self) -> bool:
        """One answer for every situation: nothing has to be remembered."""
        return self.distinct_answers <= 1

    @property
    def verdict(self) -> str:
        if self.trivial:
            return "NO_FLOOR"
        return "FLOOR"

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": "floorgen-floor/v1", "name": self.name, "verdict": self.verdict,
                "situations": self.situations, "distinct_answers": self.distinct_answers,
                "state_floor": self.distinct_answers, "bits_floor": self.bits,
                "collapsing_pairs": self.collapsing_pairs,
                "exemplars": {str(k): v for k, v in self.exemplars.items()},
                "method": "exhaustive evaluation of the answer at every declared situation",
                "limits": LIMITS, "notes": self.notes}

    def render(self) -> str:
        if self.trivial:
            return (f"NO_FLOOR — {self.name}\n"
                    f"  situations .......... {self.situations}\n"
                    f"  distinct answers .... {self.distinct_answers}\n"
                    f"  Every situation demands the same answer, so nothing has to be "
                    f"distinguished and\n  no state is forced. This is a real result, not an "
                    f"error — but check that the answer\n  function is the one you meant.")
        lines = [f"FLOOR — {self.name}",
                 f"  situations .......... {self.situations}",
                 f"  distinct answers .... {self.distinct_answers}",
                 f"  state floor ......... >= {self.distinct_answers} distinguishable states",
                 f"  bits floor .......... >= {self.bits:.4f} bits "
                 f"({math.ceil(self.bits)} whole bits)"]
        if self.exemplars:
            lines.append("  exemplars:")
            for ans, sit in list(sorted(self.exemplars.items(), key=lambda kv: str(kv[0])))[:6]:
                pretty = ", ".join(f"{k}={v}" for k, v in sorted(sit.items()))
                lines.append(f"    answer {str(ans)[:20]:<20} <- {pretty}")
            if len(self.exemplars) > 6:
                lines.append(f"    ... and {len(self.exemplars) - 6} more")
        lines.append("  pigeonhole lifted pointwise — this is not new mathematics; the value is "
                     "that the count is exact")
        return "\n".join(lines)


LIMITS = [
    "A floor is a LOWER bound on retained state. It is not an achievable design and not an upper "
    "bound; no encoding is claimed to attain it.",
    "The floor is exact for the situation space THE SPEC DECLARES. A spec that omits a "
    "distinction the real system must make yields a floor that is too low, and this package "
    "cannot detect that.",
    "Pigeonhole lifted pointwise. The mathematics is elementary; what is mechanised is the exact "
    "count over an enumerated space.",
]


def state_floor(spec: Spec) -> Floor:
    """The exact number of states any correct implementation must be able to distinguish."""
    spec.validate()
    seen: Dict[Any, Dict[str, Any]] = {}
    n = 0
    for sit in spec.situations():
        n += 1
        if sit.answer not in seen:
            seen[sit.answer] = sit.as_dict
    distinct = len(seen)
    bits = math.log2(distinct) if distinct > 0 else 0.0
    collapsing = n - distinct
    notes = []
    if distinct == n:
        notes.append("every situation demands a distinct answer, so the floor equals the whole "
                     "situation space: nothing may be forgotten")
    return Floor(spec.name, n, distinct, bits, seen, collapsing, notes)


@dataclass
class EncodingResult:
    ok: bool
    n_checked: int
    exhaustive: bool
    collision: Optional[Tuple[Dict[str, Any], Dict[str, Any], Any, Any]] = None
    codes_used: int = 0
    floor: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "SUFFICIENT" if self.ok else "INSUFFICIENT"

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1

    def to_dict(self) -> Dict[str, Any]:
        d = {"schema": "floorgen-encoding/v1", "verdict": self.verdict,
             "situations_checked": self.n_checked, "exhaustive": self.exhaustive,
             "codes_used": self.codes_used, "state_floor": self.floor, "notes": self.notes}
        if self.collision:
            a, b, ca, cb = self.collision
            d["collision"] = {"situation_a": a, "situation_b": b,
                              "shared_code": _jsonable(ca), "differing_answers": _jsonable(cb)}
        return d

    def render(self) -> str:
        if self.ok:
            return (f"SUFFICIENT — the encoding separates every pair the spec requires\n"
                    f"  situations checked .. {self.n_checked} (exhaustive)\n"
                    f"  distinct codes ...... {self.codes_used}\n"
                    f"  state floor ......... {self.floor}\n"
                    f"  slack ............... {self.codes_used - self.floor} code(s) above the "
                    f"floor")
        a, b, code, answers = self.collision or ({}, {}, None, None)
        pa = ", ".join(f"{k}={v}" for k, v in sorted(a.items()))
        pb = ", ".join(f"{k}={v}" for k, v in sorted(b.items()))
        return (f"INSUFFICIENT — the encoding collapses two situations that demand different "
                f"answers\n"
                f"  situation A ......... {pa}\n"
                f"  situation B ......... {pb}\n"
                f"  shared code ......... {code}\n"
                f"  demanded answers .... {answers}\n"
                f"  In this state the system cannot tell A from B, so it must answer both the "
                f"same way,\n  and the spec says the answers differ. One of them will be wrong.")


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    return str(v)


def verify_encoding(spec: Spec, encode: Callable[[Dict[str, Any]], Hashable]) -> EncodingResult:
    """Does `encode` retain enough to answer the spec? Checked at every situation, not argued.

    Returns the FIRST collision as a concrete pair. A counterexample is what makes the negative
    result actionable; "insufficient" on its own is not a finding anyone can fix.
    """
    spec.validate()
    by_code: Dict[Any, Tuple[Dict[str, Any], Any]] = {}
    n = 0
    for sit in spec.situations():
        n += 1
        assign = sit.as_dict
        code = _key(encode(assign))
        if code in by_code:
            prev_assign, prev_answer = by_code[code]
            if prev_answer != sit.answer:
                return EncodingResult(
                    False, n, True,
                    (prev_assign, assign, code, (_jsonable(prev_answer), _jsonable(sit.answer))),
                    len(by_code), 0)
        else:
            by_code[code] = (assign, sit.answer)
    floor = state_floor(spec)
    return EncodingResult(True, n, True, None, len(by_code), floor.distinct_answers)


@dataclass
class Impossibility:
    proven: bool
    budget_states: int
    floor_states: int
    reason: str

    @property
    def verdict(self) -> str:
        return "IMPOSSIBLE" if self.proven else "NOT_EXCLUDED"

    @property
    def exit_code(self) -> int:
        """1 when impossibility is PROVEN — a proven impossibility is a failing check."""
        return 1 if self.proven else 0

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": "floorgen-impossibility/v1", "verdict": self.verdict,
                "budget_states": self.budget_states, "state_floor": self.floor_states,
                "reason": self.reason, "limits": LIMITS}

    def render(self) -> str:
        return f"{self.verdict}\n  {self.reason}"


def impossibility(floor: Floor, *, budget_states: Optional[int] = None,
                  budget_bits: Optional[float] = None) -> Impossibility:
    """Given a floor and a state budget, is the specification impossible to meet?

    Exactly one budget must be given. Supplying neither is a request for a verdict with no
    evidence, and this package will not manufacture one.
    """
    if (budget_states is None) == (budget_bits is None):
        raise SpecError("give exactly one of budget_states or budget_bits: with neither there is "
                        "nothing to compare the floor against, and with both the two can "
                        "disagree")
    if budget_bits is not None:
        if budget_bits < 0:
            raise SpecError("a negative bit budget is not a budget")
        if budget_bits > 63:
            raise SpecError(f"a {budget_bits}-bit budget exceeds any floor this package can "
                            f"compute, so the comparison would be vacuous")
        budget_states = int(2 ** math.floor(budget_bits))
    assert budget_states is not None
    if budget_states < 1:
        raise SpecError("a system with fewer than one state does not exist")

    if budget_states < floor.distinct_answers:
        return Impossibility(
            True, budget_states, floor.distinct_answers,
            f"the spec demands {floor.distinct_answers} distinguishable answers and the budget "
            f"allows {budget_states} states. By pigeonhole two situations demanding different "
            f"answers must share a state, and in that state the system answers both the same "
            f"way. No implementation, however clever, can meet this specification.")
    return Impossibility(
        False, budget_states, floor.distinct_answers,
        f"the budget of {budget_states} states meets the floor of {floor.distinct_answers}. "
        f"This EXCLUDES the counting obstruction and nothing else — it is not a construction, "
        f"and no encoding is claimed to exist.")


# --- declarative specs ----------------------------------------------------------------------------
def load_spec(path: str) -> Spec:
    """Load a JSON spec whose answer is a TABLE, not code.

    Executable specs are supported through the Python API only. A file format that evaluates
    arbitrary expressions from disk would make `floorgen check untrusted.json` a code-execution
    primitive, which is too high a price for the convenience.
    """
    raw = json.loads(open(path, encoding="utf-8").read())
    if not isinstance(raw, dict):
        raise SpecError("a spec file must be a JSON object")
    for k in ("name", "variables", "answers"):
        if k not in raw:
            raise SpecError(f"missing required field {k!r}")
    variables = raw["variables"]
    if not isinstance(variables, dict):
        raise SpecError("`variables` must be an object mapping each name to its finite domain")
    table = raw["answers"]
    if not isinstance(table, list) or not table:
        raise SpecError("`answers` must be a non-empty list of {when: {...}, answer: ...} rows")

    rows: List[Tuple[Dict[str, Any], Any]] = []
    for i, row in enumerate(table):
        if not isinstance(row, dict) or "when" not in row or "answer" not in row:
            raise SpecError(f"answers[{i}] must have both `when` and `answer`")
        rows.append((dict(row["when"]), row["answer"]))
    default = raw.get("default", None)
    has_default = "default" in raw

    def answer(assign: Dict[str, Any]) -> Hashable:
        for when, ans in rows:
            if all(assign.get(k) == v for k, v in when.items()):
                return _key(ans)
        if has_default:
            return _key(default)
        raise SpecError(
            f"no row of the answer table matches {assign!r} and no `default` was declared. An "
            f"unmatched situation has no demanded answer, so the floor would be computed over a "
            f"space the spec does not actually cover.")

    return Spec(name=str(raw["name"]), variables={k: list(v) for k, v in variables.items()},
                answer=answer, answer_source=path, notes=list(raw.get("notes", [])))
