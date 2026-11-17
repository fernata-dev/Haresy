# HANDOFF

_Updated at every milestone. Read this first if you are continuing the work._

## Status: m1 done (harness)

| milestone | state |
|---|---|
| m1 harness | DONE |
| m2 D2 scanner + freeze | next |
| m3 D5 guard, residual risk, benign utility | pending |
| m4 skillscan | pending |
| m5 LLM adapters + pilot | pending |
| m6 report + demo | pending |
| m7 docs + self-audit | pending |

## What works

- `python -m hares validate` — validates data, prints the matrix.
- `python -m hares eval --split dev --defenses D0,D1` — worst-case simulator run.
- `pytest` — green.

## What is not there yet

D2..D5, skillscan, LLM adapters, report, demo, test-split data (written only after the scanner freeze).

## Conservative decisions taken (ambiguities in the brief)

1. **Data location.** The brief lists `data/benign/` under `src/hares/` but also
   `data/attacks/student_written/README.md`. Data lives in top-level `data/`
   (attacks and benign); code lives in `src/hares/`.
2. **Attacker HTTP destination.** Rule 2 says the attacker destination is always
   `attacker@test.local`. `http_post` needs a URL, so the single mock attacker URL
   is `http://test.local/attacker-inbox` (same reserved name, never resolved,
   `http_post` only appends to an in-memory list). Validators reject anything else.
3. **ai-draft cap** (at most 5 per language) is applied to ALL languages including
   English and is enforced by the validator, not by convention. Split: 2 dev + 3 test.
4. **Encoding applicability.** leet/rot13 do nothing to Arabic script; tatweel/tashkeel
   do nothing to Latin. A (text, encoding) pair is generated only if the encoding
   changes >= 25% of ordinary tokens. N/A cells are never reported as results.
5. **Extra encoders** beyond the five required: tatweel, tashkeel, homoglyph
   (Arabic-relevant obfuscations). Reported separately from the core five.
6. **Simulated agent is never repeated** (N=1): repeating a deterministic agent
   would only inflate n.
7. **Scanner hit => content withheld => benign task counted as failed.** Simple and
   conservative against scanners; stated in LIMITATIONS.
8. **`hares.py` at the repo root** is only a path shim so `python -m hares` works
   without `pip install -e .`.

## Exact next commands

```bash
python -m pytest
python -m hares validate
python -m hares eval --split dev --defenses D0,D1
```
