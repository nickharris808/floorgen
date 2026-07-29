"""cli.py — floorgen floor | check | recoveries | impossible.

Exit codes: 0 checked and holds · 1 checked and fails · 2 NOT checked.
`floor` exits 2 on NO_FLOOR: a spec that demands nothing has not established anything, and
reporting that as success would let a mis-typed answer function pass for a result.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .core import SpecError, impossibility, load_spec, state_floor, verify_encoding
from .recoveries import RECOVERIES, by_name, names


def _emit(obj, as_json: bool) -> None:
    print(json.dumps(obj.to_dict(), indent=2) if as_json else obj.render())


def cmd_floor(args: argparse.Namespace) -> int:
    try:
        spec = by_name(args.spec) if args.builtin else load_spec(args.spec)
        floor = state_floor(spec)
    except (SpecError, KeyError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    _emit(floor, args.json)
    if args.budget_states is not None or args.budget_bits is not None:
        try:
            imp = impossibility(floor, budget_states=args.budget_states,
                                budget_bits=args.budget_bits)
        except SpecError as e:
            print(str(e), file=sys.stderr)
            return 2
        print()
        _emit(imp, args.json)
        return imp.exit_code
    return 2 if floor.trivial else 0


def cmd_recoveries(args: argparse.Namespace) -> int:
    print("Worked recoveries — each floor is checkable by hand:\n")
    worst = 0
    for name, build, desc in RECOVERIES:
        f = state_floor(build())
        tag = "NO_FLOOR" if f.trivial else f"floor {f.distinct_answers}"
        print(f"  {name:<22} {desc}")
        print(f"  {'':<22} {f.situations} situations -> {tag}"
              f"{'' if f.trivial else f' ({f.bits:.2f} bits)'}")
    print("\nEvery number above is an exact count over an enumerated space, not an estimate.")
    return worst


def cmd_impossible(args: argparse.Namespace) -> int:
    try:
        spec = by_name(args.spec) if args.builtin else load_spec(args.spec)
        floor = state_floor(spec)
        imp = impossibility(floor, budget_states=args.budget_states, budget_bits=args.budget_bits)
    except (SpecError, KeyError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    _emit(imp, args.json)
    return imp.exit_code


def cmd_selftest(args: argparse.Namespace) -> int:
    """Check the method against cases whose answers are obvious without it."""
    from .core import Spec
    checks = []
    expected = {"last-writer-per-slot": 64, "counter-read-mod-3": 3, "tenant-ownership": 27,
                "gap-seen": 2, "idempotent-replay": 16, "latest-checkpoint": 3,
                "constant-answer": 1}
    for name, want in expected.items():
        got = state_floor(by_name(name)).distinct_answers
        checks.append((got == want, f"{name}: floor {got} (hand-computed {want})"))

    f = state_floor(by_name("gap-seen"))
    imp = impossibility(f, budget_bits=0)
    checks.append((imp.proven, "a 0-bit budget cannot meet a 2-state floor — PROVEN impossible"))
    imp2 = impossibility(f, budget_bits=1)
    checks.append((not imp2.proven, "a 1-bit budget meets it, and that is reported as NOT_EXCLUDED "
                                    "rather than as a construction"))

    spec = by_name("counter-read-mod-3")
    good = verify_encoding(spec, lambda a: a["count"] % 3)
    bad = verify_encoding(spec, lambda a: a["count"] % 2)
    checks.append((good.ok, "retaining count mod 3 is SUFFICIENT for a mod-3 question"))
    checks.append((not bad.ok and bad.collision is not None,
                   "retaining count mod 2 is INSUFFICIENT, with a concrete colliding pair"))

    try:
        state_floor(Spec(name="empty", variables={}, answer=lambda a: 1))
        checks.append((False, "a spec with no variables is REFUSED"))
    except SpecError:
        checks.append((True, "a spec with no variables is REFUSED"))

    for ok, label in checks:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    bad_n = sum(1 for ok, _ in checks if not ok)
    print(f"\nRESULT: {'every floor matches an independently computed value' if not bad_n else f'{bad_n} FAILED'}")
    return 1 if bad_n else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="floorgen",
        description="Describe what your system must be able to recover; get the state floor.")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("floor", help="compute the exact state floor for a spec")
    f.add_argument("spec")
    f.add_argument("-b", "--builtin", action="store_true", help="`spec` names a worked recovery")
    f.add_argument("--budget-states", type=int, help="also test a state budget for impossibility")
    f.add_argument("--budget-bits", type=float, help="also test a bit budget for impossibility")
    f.add_argument("--json", action="store_true")
    f.set_defaults(func=cmd_floor)

    i = sub.add_parser("impossible", help="prove a budget cannot meet a spec")
    i.add_argument("spec")
    i.add_argument("-b", "--builtin", action="store_true")
    i.add_argument("--budget-states", type=int)
    i.add_argument("--budget-bits", type=float)
    i.add_argument("--json", action="store_true")
    i.set_defaults(func=cmd_impossible)

    r = sub.add_parser("recoveries", help="the worked recoveries and their floors")
    r.set_defaults(func=cmd_recoveries)

    t = sub.add_parser("selftest", help="check every floor against a hand-computed value")
    t.set_defaults(func=cmd_selftest)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
