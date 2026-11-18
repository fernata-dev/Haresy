"""Bawwab (بوّاب): discover, scan and (opt-in) protect AI agent setups against prompt injection.

Why the name: an Egyptian bawwab (building doorman) does not need to understand the
language a visitor speaks; he looks at where they are going and what they carry out.
Bawwab's guard works the same way: it decides from tool calls (destinations, files),
never from the language of the text, so Egyptian Arabic, Arabizi or Base64 make no
difference to it.

Bawwab is the product name of the Hares project (it was briefly called Zorfa).  The research benchmark lives in
the `hares` package and is unchanged (its scanners are frozen); Bawwab adds
discovery, installation and opt-in protection on top of it.

Bawwab reduces the damage an injected instruction can cause; it does not stop a
model from following it.
"""

__version__ = "0.4.0"
