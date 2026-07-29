"""floorgen — describe what your system must be able to recover; get the state floor.

    from floorgen import Spec, state_floor, impossibility, verify_encoding

    spec = Spec(name="gap-seen",
                variables={f"arrived{i}": [0, 1] for i in range(6)},
                answer=lambda a: 1 if any(a[f"arrived{i}"] == 0 for i in range(6)) else 0)

    state_floor(spec).distinct_answers        # 2 -- one bit, from 64 histories
    impossibility(state_floor(spec), budget_bits=0).proven   # True
"""
from .core import (SCHEMA, EncodingResult, Floor, Impossibility, Situation, Spec, SpecError,
                   impossibility, load_spec, state_floor, verify_encoding)
from .recoveries import RECOVERIES, by_name, names

__version__ = "0.1.0"
__all__ = ["Spec", "Situation", "Floor", "EncodingResult", "Impossibility", "SpecError",
           "state_floor", "verify_encoding", "impossibility", "load_spec", "SCHEMA",
           "RECOVERIES", "by_name", "names", "__version__"]
