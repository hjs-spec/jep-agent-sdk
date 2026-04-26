"""
CheckDeterminability + DeterminabilityGuard (runtime gate).
Extension module, not part of JEP-04/JAC-01 core protocol.
"""

import functools
from collections import defaultdict
from typing import Any, Callable, List, Optional, Tuple


def check_determinability(configs, omega, target):
    groups = defaultdict(list)
    for C in configs:
        groups[omega(C)].append(C)

    delta = {}
    for w, group in groups.items():
        values = {target(C) for C in group}
        if len(values) > 1:
            vals = list(values)
            C1 = next(C for C in group if target(C) == vals[0])
            C2 = next(C for C in group if target(C) == vals[1])
            return ("NotDetermined", C1, C2, w)
        delta[w] = target(group[0])

    return ("Determined", delta)


def conflict_edges(configs, omega, target):
    groups = defaultdict(list)
    for C in configs:
        groups[omega(C)].append(C)
    edges = []
    for w, group in groups.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if target(group[i]) != target(group[j]):
                    edges.append((group[i], group[j], w))
    return edges


def evidence_cover(configs, omega, target, evidences):
    for C1, C2, _ in conflict_edges(configs, omega, target):
        if not any(E(C1) != E(C2) for E in evidences):
            return False
    return True


class DeterminabilityGuard:
    """
    Runtime gate: intercept agent execution if evidence is insufficient.
    """

    def __init__(
        self,
        evidence_fn: Callable[[Any], Any],
        target_fn: Callable[[Any], Any],
        knowledge_base: Optional[List[Any]] = None,
        on_insufficient: str = "raise",
        fallback: Optional[Callable] = None,
    ):
        self.evidence_fn = evidence_fn
        self.target_fn = target_fn
        self.knowledge_base = knowledge_base or []
        self.on_insufficient = on_insufficient
        self.fallback = fallback

    def check(self, context: Any) -> Tuple[str, Any]:
        if not self.knowledge_base:
            return ("Determined", {})

        def omega(c):
            return self.evidence_fn(c)

        def target(c):
            return self.target_fn(c)

        test_set = self.knowledge_base + [context]
        return check_determinability(test_set, omega, target)

    def require_determinable(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = {
                "args": args,
                "kwargs": kwargs,
                "tools_used": [],
            }

            result = self.check(context)

            if result[0] == "NotDetermined":
                msg = (
                    f"DeterminabilityGuard blocked {func.__name__}: "
                    f"evidence insufficient. "
                    f"Counterexample: {result[1]} vs {result[2]} "
                    f"share observation {result[3]} but have different "
                    f"outcomes. Add more evidence before proceeding."
                )
                if self.on_insufficient == "raise":
                    raise RuntimeError(msg)
                elif self.on_insufficient == "warn":
                    print(f"[JEP WARNING] {msg}")
                elif (
                    self.on_insufficient == "fallback"
                    and self.fallback
                ):
                    return self.fallback(*args, **kwargs)

            return func(*args, **kwargs)

        return wrapper
