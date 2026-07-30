# floorgen

**Describe what your system must be able to recover; get a proven state floor.**

[![tests](https://github.com/nickharris808/floorgen/actions/workflows/tests.yml/badge.svg)](https://github.com/nickharris808/floorgen/actions/workflows/tests.yml)
[![licence](https://img.shields.io/badge/licence-Apache--2.0-blue.svg)](LICENSE)

If your system must answer a question about its past, and two different pasts demand two different
answers, the system's retained state must differ between them. Otherwise it is in the same state
in both, must give the same answer in both, and one of those answers is wrong.

Count the distinct answers your specification demands and you have counted the states any correct
implementation must be able to occupy. `floorgen` does that counting **exactly**, from a
machine-readable spec, and turns a design-review argument into a number.

**This is pigeonhole, lifted pointwise. It is not new mathematics** — and every report says so.
What is mechanised is the exact count over an enumerated space, which is the part people get wrong.

## Install

**Not yet on PyPI.** The command below is the one that works today. It installs from this repository, pinned to a tag.

```bash
pip install "git+https://github.com/nickharris808/floorgen@v0.1.0"
```

`pip install floorgen` is the intended command once the name is published. **It 404s today**, which is why it is not the first step above. The tag is pinned rather than `@main` so a reader installs the exact code this README documents.

## 30-second quickstart

```bash
floorgen recoveries                                     # seven worked examples and their floors
floorgen floor gap-seen -b                              # the floor for one of them
floorgen floor gap-seen -b --budget-bits 0              # ...and whether a budget can meet it
floorgen selftest                                       # every floor vs a hand-computed value
```

Exit codes: **0** checked and holds · **1** checked and fails (or impossibility **proven**) ·
**2** NOT checked.

## Worked example — one bit out of sixty-four histories

"Did the stream have a gap?" over six arrivals. There are 2⁶ = 64 possible histories and exactly
two answers, so a design that retains the whole sequence is 32× above the floor:

```console
$ floorgen floor gap-seen -b --budget-bits 0
FLOOR — gap-seen
  situations .......... 64
  distinct answers .... 2
  state floor ......... >= 2 distinguishable states
  bits floor .......... >= 1.0000 bits (1 whole bits)
  exemplars:
    answer 0             <- arrived0=1, arrived1=1, arrived2=1, ...
    answer 1             <- arrived0=0, arrived1=0, arrived2=0, ...
  pigeonhole lifted pointwise — this is not new mathematics; the value is that the count is exact

IMPOSSIBLE
  the spec demands 2 distinguishable answers and the budget allows 1 states. By pigeonhole two
  situations demanding different answers must share a state, and in that state the system answers
  both the same way. No implementation, however clever, can meet this specification.
$ echo $?
1
```

## Checking a proposed encoding

A floor tells you what is necessary. `verify_encoding` answers the other question — *is what I
plan to keep enough?* — and answers it by exhaustive check, returning the colliding pair when it
is not:

```python
from floorgen import by_name, verify_encoding

spec = by_name("counter-read-mod-3")          # a counter only ever read modulo 3
print(verify_encoding(spec, lambda a: a["count"] % 3).verdict)   # SUFFICIENT
print(verify_encoding(spec, lambda a: a["count"] % 2).render())
```

```console
INSUFFICIENT — the encoding collapses two situations that demand different answers
  situation A ......... count=0
  situation B ......... count=2
  shared code ......... 0
  demanded answers .... (0, 2)
  In this state the system cannot tell A from B, so it must answer both the same way,
  and the spec says the answers differ. One of them will be wrong.
```

**"Insufficient" with no counterexample is not a finding anyone can act on**, so a concrete
colliding pair is always exhibited.

## The seven worked recoveries

Every floor below is derivable on paper, which is the point — the tool is checked against cases
whose answers do not depend on it.

| recovery | question | situations | floor |
|---|---|---:|---:|
| `last-writer-per-slot` | name the last writer to each slot | 64 | **64** |
| `tenant-ownership` | refuse a cross-tenant read | 27 | **27** |
| `idempotent-replay` | apply each request at most once | 16 | **16** |
| `counter-read-mod-3` | a counter only ever read mod 3 | 8 | **3** |
| `latest-checkpoint` | restore to the most recent checkpoint | 243 | **3** |
| `gap-seen` | did the stream have a gap? | 64 | **2** |
| `constant-answer` | *(honest negative)* nothing is demanded | 9 | **NO_FLOOR** |

The last row is deliberate. A library whose every example produces a floor teaches nothing about
when the tool correctly says there is none — and a `NO_FLOOR` exits **2**, not 0, because nothing
was established and a mis-typed answer function should not pass for a result.

## Library use

```python
from floorgen import Spec, state_floor, impossibility, verify_encoding

spec = Spec(
    name="gap-seen",
    variables={f"arrived{i}": [0, 1] for i in range(6)},
    answer=lambda a: 1 if any(a[f"arrived{i}"] == 0 for i in range(6)) else 0,
)

f = state_floor(spec)
f.distinct_answers                       # 2
f.bits                                   # 1.0
impossibility(f, budget_bits=0).proven   # True
```

Spec files are also supported, but `answers` is a **table**, never an expression — a file format
that evaluated code from disk would make `floorgen floor untrusted.json` a code-execution
primitive. Executable answer functions are available through the Python API only.

## What is refused, and why

| input | response |
|---|---|
| no variables | refused — the space is a single point and a floor of 1 is vacuous |
| a variable with an empty domain | refused — every statement about an empty space is vacuously true |
| duplicate values in a domain | refused — the situation count, and every ratio derived from it, would be wrong |
| more than 5,000,000 situations | refused — **there is no sampled version of this method**; a sampled count is a lower bound on a lower bound and certifies nothing |
| a situation no answer row matches | refused — the floor would be computed over a space the spec does not cover |
| an impossibility query with no budget, or with both | refused |

## Honest scope

A floor is a **lower bound on retained state**. It says:

- **what it does mean** — no implementation meeting this spec can distinguish fewer than N
  situations, and if your budget is below N the spec is impossible. That impossibility is proven,
  not suspected.
- **it is not an achievable design.** Meeting the bound *excludes the counting obstruction and
  nothing else*. `floorgen` reports that as `NOT_EXCLUDED`, never as "feasible", because no
  encoding is claimed to exist.
- **it is exact only for the space the spec declares.** A spec that omits a distinction the real
  system must make yields a floor that is too low, and this package cannot detect that. The floor
  is only as honest as the spec.
- **it is elementary mathematics.** Pigeonhole, applied pointwise. The contribution is the exact
  mechanised count, not the theorem.

## What this does not do

`floorgen` **computes and reports**. It never provisions at a floor, refuses below one, or gates
anything on the result. See [CLAIMS-MAP.md](CLAIMS-MAP.md).

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q          # 35 tests
floorgen selftest
```

The suite checks the count against brute force over the answer image, asserts the identity
encoding is always sufficient and a constant encoding never is (except where the floor is
trivial), and pins all seven floors to hand-computed values.

## License

Apache-2.0. See [LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md).

**Citing this?** Metadata is in [CITATION.cff](CITATION.cff) — GitHub's "Cite this repository" button reads it directly.

<!-- PORTFOLIO -->
---

## The rest of the portfolio

25 artifacts, one idea: **a measurement you cannot check is a press release.** Every tool
here reports; none of them gates.

**Tools**

| | |
|---|---|
| [`abstain-bench`](https://github.com/nickharris808/abstain-bench) | how often does a verifier pass input it could not check? |
| [`evidence`](https://github.com/nickharris808/evidence) | run the whole portfolio over your repo — the weakest leg, never the mean |
| [`floorgen`](https://github.com/nickharris808/floorgen) | what must your system remember? an exact lower bound ← you are here |
| [`formal-proof-mcp`](https://github.com/nickharris808/formal-proof-mcp) | a proof kernel for your coding agent |
| [`gatecount`](https://github.com/nickharris808/gatecount) | exactly how many states does removing this check admit? |
| [`gridlock`](https://github.com/nickharris808/gridlock) | certify a wait-for relation cannot wedge |
| [`honestbench`](https://github.com/nickharris808/honestbench) | measure your CI's escape rate |
| [`kvleak`](https://github.com/nickharris808/kvleak) | cross-tenant leak scanner |
| [`kvprobe`](https://github.com/nickharris808/kvprobe) | model-substitution detector with a measured FPR |
| [`preregister`](https://github.com/nickharris808/preregister) | refuses to seal a plan whose conclusion is already fixed |
| [`proof-carrying-ci`](https://github.com/nickharris808/proof-carrying-ci) | the whole portfolio as one CI check, with SARIF |
| [`proof-to-code-drift`](https://github.com/nickharris808/proof-to-code-drift) | fail the build when the proof stops matching |
| [`sf-verify`](https://github.com/nickharris808/sf-verify) | re-derive admission decisions offline |
| [`signoff-cert`](https://github.com/nickharris808/signoff-cert) | certificates that carry their own false-pass bound |
| [`tokencount`](https://github.com/nickharris808/tokencount) | a token count both parties can recompute |

**Benchmarks** — each recomputes one of our own published numbers from its certificate

| | |
|---|---|
| [`illusion-bench`](https://github.com/nickharris808/illusion-bench) | how many broken kernels does your oracle admit? |
| [`kv-reuse-econ-bench`](https://github.com/nickharris808/kv-reuse-econ-bench) | recompute our economics headline |
| [`llm-tenant-isolation-bench`](https://github.com/nickharris808/llm-tenant-isolation-bench) | recompute our isolation figures |

**Datasets**

| | |
|---|---|
| [`abstain-corpus`](https://huggingface.co/datasets/nickh007/abstain-corpus) | 32 inputs a verifier must NOT pass |
| [`kv-reuse-econ-traces`](https://huggingface.co/datasets/nickh007/kv-reuse-econ-traces) | per-workload reuse accounting + the closed form |
| [`kv-tenant-isolation-bench`](https://huggingface.co/datasets/nickh007/kv-tenant-isolation-bench) | isolation observations, uninterpretable rows included |
| [`llm-precision-fingerprints`](https://huggingface.co/datasets/nickh007/llm-precision-fingerprints) | precision-labelled logprobs with a negative control |

**Try it in a browser** — no install, no GPU

| | |
|---|---|
| [`negative-results-atlas`](https://huggingface.co/spaces/nickh007/negative-results-atlas) | ten claims we took back |
| [`tenant-leak-demo`](https://huggingface.co/spaces/nickh007/tenant-leak-demo) | the residency calculator |
| [`wait-for-visualiser`](https://huggingface.co/spaces/nickh007/wait-for-visualiser) | paste a wait-for graph, see the cycle |

### Documentation

Everything above, explained in one place: **<https://nickharris808.github.io/evidence-docs/>** —
the [tutorial](https://nickharris808.github.io/evidence-docs/start/tutorial/),
[what this proves and what it does not](https://nickharris808.github.io/evidence-docs/concepts/what-this-proves/),
and a [CLI reference](https://nickharris808.github.io/evidence-docs/reference/cli/) generated by
running `--help` on every published command.

### The commercial edition

Everything above is **measure-only** and Apache-2.0: it tells you what is true and never acts on
it. The **enforcement** side — binding a partition key at the admission decision, the compiled gate
corpus, and the certificate-*issuing* faucet — is covered by filed patents and licensed separately.

**Reading is free. Enforcing is licensed.**
<!-- /PORTFOLIO -->
