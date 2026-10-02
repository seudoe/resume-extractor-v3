"""Hungarian matching between predicted and gold entity lists (PROMPT.md
§4.2). Used for workHistory/education/projects/certifications/awards: align
predicted entries to gold entries by a per-section key field, then let
metrics.py score the aligned pairs.
"""

from collections.abc import Callable

import numpy as np
from rapidfuzz.distance import JaroWinkler
from scipy.optimize import linear_sum_assignment

# Below this similarity, two entries are not considered a match at all (an
# unmatched cost of 0 would otherwise let the Hungarian algorithm pair up
# entries that share nothing, just to minimize total cost).
MIN_MATCH_SIMILARITY = 0.5


def _key_similarity(a: str, b: str) -> float:
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return JaroWinkler.similarity(a, b)


def match_entities(
    predicted: list[dict],
    gold: list[dict],
    key_fn: Callable[[dict], str],
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Align predicted[i] <-> gold[j] by Jaro-Winkler similarity of key_fn.

    Returns (matched_pairs, unmatched_predicted_indices, unmatched_gold_indices).
    """
    if not predicted or not gold:
        return [], list(range(len(predicted))), list(range(len(gold)))

    cost = np.ones((len(predicted), len(gold)))
    for i, p in enumerate(predicted):
        for j, g in enumerate(gold):
            cost[i, j] = 1.0 - _key_similarity(key_fn(p), key_fn(g))

    row_ind, col_ind = linear_sum_assignment(cost)

    matched, used_p, used_g = [], set(), set()
    for i, j in zip(row_ind, col_ind):
        if cost[i, j] <= (1.0 - MIN_MATCH_SIMILARITY):
            matched.append((int(i), int(j)))
            used_p.add(int(i))
            used_g.add(int(j))

    unmatched_p = [i for i in range(len(predicted)) if i not in used_p]
    unmatched_g = [j for j in range(len(gold)) if j not in used_g]
    return matched, unmatched_p, unmatched_g


# Per-section key fields, PROMPT.md §4.2: "An entity counts as correct only
# if aligned AND its key fields pass."
SECTION_KEYS: dict[str, Callable[[dict], str]] = {
    "workHistory": lambda e: f"{e.get('company', '')} {e.get('title', '')}",
    "education": lambda e: e.get("institution", ""),
    "projects": lambda e: e.get("title", ""),
    "certifications": lambda e: e.get("name", ""),
    "awards": lambda e: e.get("name", ""),
    "affiliations": lambda e: e.get("organization", ""),
    "publications": lambda e: e.get("title", ""),
}
