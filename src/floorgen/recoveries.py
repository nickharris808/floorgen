"""recoveries.py — worked recoveries, each a real "what must be retained" question.

Each is a Spec plus the floor it yields. They exist so the method can be checked against cases
where the answer is independently obvious, which is the only way to know a floor computation is
not quietly counting the wrong thing.

The last one is deliberately a NEGATIVE: a spec that demands nothing and correctly yields no
floor. A library of examples that all succeed teaches nothing about when the tool says no.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from .core import Spec

__all__ = ["RECOVERIES", "by_name", "names"]


def _last_writer(n_writers: int = 4, n_slots: int = 3) -> Spec:
    """To name the last writer to each slot, you must retain the last writer of each slot."""
    return Spec(
        name="last-writer-per-slot",
        variables={f"slot{i}": list(range(n_writers)) for i in range(n_slots)},
        answer=lambda a: tuple(a[f"slot{i}"] for i in range(n_slots)),
        notes=[f"{n_writers} writers, {n_slots} slots: the floor is {n_writers}^{n_slots}, "
               f"because every assignment demands a different answer"],
    )


def _counter_mod(n: int = 8, modulus: int = 3) -> Spec:
    """A counter you only ever read modulo m needs m states, not n."""
    return Spec(
        name=f"counter-read-mod-{modulus}",
        variables={"count": list(range(n))},
        answer=lambda a: a["count"] % modulus,
        notes=[f"{n} distinct histories collapse to {modulus} answers: the floor is the number "
               f"of ANSWERS, not the number of histories. This is the case that catches a floor "
               f"computed from the wrong set."],
    )


def _tenant_isolation(n_tenants: int = 3, n_keys: int = 3) -> Spec:
    """To refuse a cross-tenant read you must retain which tenant owns each key."""
    return Spec(
        name="tenant-ownership",
        variables={f"key{i}": list(range(n_tenants)) for i in range(n_keys)},
        answer=lambda a: tuple(a[f"key{i}"] for i in range(n_keys)),
        notes=["the decision 'may this caller read this key' is a function of ownership, so "
               "ownership is what must be retained"],
    )


def _sequence_gap(n: int = 6) -> Spec:
    """To report whether a sequence had a gap you need only one bit, not the sequence."""
    return Spec(
        name="gap-seen",
        variables={f"arrived{i}": [0, 1] for i in range(n)},
        answer=lambda a: 1 if any(a[f"arrived{i}"] == 0 for i in range(n)) else 0,
        notes=[f"2^{n} histories, 2 answers. The floor is 2 — one bit — and a design retaining "
               f"the whole sequence is {2**n // 2}x above it."],
    )


def _idempotent_replay(n_requests: int = 4) -> Spec:
    """To make replay idempotent you must remember which requests were already applied."""
    return Spec(
        name="idempotent-replay",
        variables={f"applied{i}": [0, 1] for i in range(n_requests)},
        answer=lambda a: tuple(a[f"applied{i}"] for i in range(n_requests)),
        notes=["the answer 'should I apply request i' is a function of the whole applied-set, so "
               "the set is the floor"],
    )


def _checkpoint_restore(n_steps: int = 5, n_values: int = 3) -> Spec:
    """Restoring to the LATEST checkpoint needs only the latest, not the history."""
    return Spec(
        name="latest-checkpoint",
        variables={f"step{i}": list(range(n_values)) for i in range(n_steps)},
        answer=lambda a: a[f"step{n_steps - 1}"],
        notes=[f"{n_values}^{n_steps} histories, {n_values} answers. Retaining the history is "
               f"correct and enormously wasteful; the floor says how wasteful, exactly."],
    )


def _nothing_demanded() -> Spec:
    """An honest NEGATIVE: a spec that demands one answer everywhere forces no state at all."""
    return Spec(
        name="constant-answer",
        variables={"a": [0, 1, 2], "b": [0, 1, 2]},
        answer=lambda a: "always-the-same",
        notes=["Included because a library whose every example produces a floor teaches nothing "
               "about when the tool correctly says there is none. floorgen reports NO_FLOOR "
               "here, which is the right answer and a warning to re-read your answer function."],
    )


RECOVERIES: List[Tuple[str, Callable[[], Spec], str]] = [
    ("last-writer-per-slot", _last_writer,
     "name the last writer to each slot"),
    ("counter-read-mod-3", _counter_mod,
     "a counter only ever read modulo 3"),
    ("tenant-ownership", _tenant_isolation,
     "refuse a cross-tenant read"),
    ("gap-seen", _sequence_gap,
     "did the stream have a gap?"),
    ("idempotent-replay", _idempotent_replay,
     "apply each request at most once"),
    ("latest-checkpoint", _checkpoint_restore,
     "restore to the most recent checkpoint"),
    ("constant-answer", _nothing_demanded,
     "an honest negative: nothing has to be remembered"),
]


def names() -> List[str]:
    return [n for n, _, _ in RECOVERIES]


def by_name(name: str) -> Spec:
    for n, build, _ in RECOVERIES:
        if n == name:
            return build()
    raise KeyError(f"no recovery named {name!r}; known: {', '.join(names())}")
