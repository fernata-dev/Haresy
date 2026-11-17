"""D4: characters-per-token filter in the style of Broken-Token (optional).

Idea: obfuscated text (Base64, leet, zero-width, spaced letters) splits into
many short tokens, so its characters-per-token (CPT) ratio is low.  D4 flags
content whose CPT is below a threshold.

Requires a BPE tokenizer.  We use tiktoken's `cl100k_base` if it can be loaded
(it needs its vocabulary file: downloaded once, or cached via
TIKTOKEN_CACHE_DIR).  If it cannot be loaded, D4 is SKIPPED and every results
file says so; no fallback "tokenizer" is invented.

Threshold: calibrated on the DEV benign split only (the 5th percentile of CPT
over dev benign texts), per script group (Arabic script vs Latin script),
because the same tokenizer gives Arabic far fewer characters per token.

FROZEN at git tag `freeze-scanner`.
"""
from __future__ import annotations

import re
from functools import lru_cache

from hares.defenses.base import Defense, ScreenVerdict

_AR = re.compile(r"[؀-ۿ]")


@lru_cache(maxsize=1)
def _encoding():
    try:
        import tiktoken  # optional dependency
        return tiktoken.get_encoding("cl100k_base"), ""
    except ImportError:
        return None, "tiktoken is not installed (pip install tiktoken)"
    except Exception as exc:  # vocabulary download blocked / offline
        return None, f"tokenizer vocabulary could not be loaded ({type(exc).__name__})"


def cpt(text: str) -> float | None:
    enc, _ = _encoding()
    if enc is None or not text:
        return None
    n = len(enc.encode(text))
    return len(text) / n if n else None


def _group(text: str) -> str:
    return "arabic" if len(_AR.findall(text)) > 0.3 * max(1, sum(c.isalpha() for c in text)) else "latin"


@lru_cache(maxsize=1)
def thresholds() -> dict[str, float]:
    from hares.benign import load_benign

    vals: dict[str, list[float]] = {"arabic": [], "latin": []}
    for rec in load_benign("dev"):
        c = cpt(rec["text"])
        if c is not None:
            vals[_group(rec["text"])].append(c)
    out = {}
    for g, xs in vals.items():
        xs.sort()
        if xs:
            out[g] = xs[max(0, int(0.05 * len(xs)) - 1)] * 0.95
    return out


class D4CharsPerToken(Defense):
    name = "D4"
    kind = "scanner"
    description = "Characters-per-token filter (Broken-Token style), tiktoken cl100k_base, dev-calibrated."

    def available(self) -> tuple[bool, str]:
        enc, why = _encoding()
        return (enc is not None), why

    def screen(self, text: str, source: str) -> ScreenVerdict:
        c = cpt(text)
        if c is None:
            return ScreenVerdict(False, defense=self.name)
        g = _group(text)
        th = thresholds().get(g)
        if th is None:
            return ScreenVerdict(False, defense=self.name)
        flagged = c < th
        return ScreenVerdict(flagged, round(c, 3),
                             [{"rule": "low_chars_per_token", "evidence": f"cpt={c:.2f} < {th:.2f} ({g})"}]
                             if flagged else [], self.name)
