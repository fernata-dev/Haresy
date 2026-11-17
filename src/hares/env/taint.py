"""Value-level taint tracking (deliberately simple and language-blind).

A string value is *tainted* when it occurs verbatim inside untrusted content
that was delivered to the agent AND does not occur in any trusted string
(the user's instruction or the task manifest).  This is byte-for-byte
matching: it never interprets, normalises or decodes text.  Consequence
(measured, not hidden): if untrusted content carries a destination in an
encoded form, the decoded value is NOT recognised as tainted.
"""
from __future__ import annotations


class TaintTracker:
    def __init__(self, trusted: list[str] | None = None) -> None:
        self._trusted: list[str] = [t for t in (trusted or []) if t]
        self._untrusted: list[str] = []

    def add_trusted(self, text: str) -> None:
        if text:
            self._trusted.append(text)

    def add_untrusted(self, text: str) -> None:
        if text:
            self._untrusted.append(text)

    def is_tainted(self, value: object) -> bool:
        if not isinstance(value, str) or len(value) < 3:
            return False
        if any(value in t for t in self._trusted):
            return False
        return any(value in u for u in self._untrusted)
