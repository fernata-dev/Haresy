# HANDOFF

_Updated at every milestone. Read this first if you are continuing the work._

## Status: m2 done (D2 scanner developed on dev, frozen)

| milestone | state |
|---|---|
| m1 harness | DONE |
| m2 D2 scanner + freeze | DONE (tag `freeze-scanner`) |
| m3 D5 guard, residual risk, benign utility | next |
| m4 skillscan | pending |
| m5 LLM adapters + pilot | pending |
| m6 report + demo | pending |
| m7 docs + self-audit | pending |

## What works

- `python -m hares validate` — validates data, prints the matrix.
- `python -m hares eval --split dev --defenses D0,D1` — worst-case simulator run.
- `pytest` — green.

## Scanner freeze (HARD RULE 4)

- Test-split AI-draft texts were committed first (tag `data-test-before-lexicon`), then the
  D2 lexicon was written using dev texts only. The provenance rule is in the header of
  `src/hares/defenses/d2_lexicon.py` (each entry is annotated with the dev text it came from).
- Frozen files: see `src/hares/eval/freeze.py::FROZEN_FILES` (encoders + D1..D4).
  `python -m hares verify-freeze` compares them byte-for-byte with tag `freeze-scanner`.
  `eval --split test` refuses to run when they differ (unless `--allow-unfrozen`, which is
  written into the results file). Any post-freeze change goes into CHANGELOG.md.
- Dev result at freeze time (worst-case simulator, D2 content hook): 546/558 dev attack cases
  flagged and 0 dev benign cases flagged. The 12 misses (msa-dev-02 transliterated, arz-dev-02
  transliterated + leet) were left in on purpose rather than tuned away on 10 texts.
- D3 needs a real model; D4 needs tiktoken's cl100k_base vocabulary, which could NOT be
  downloaded in the build environment (proxy blocks the host). Both are reported as skipped.

## What is not there yet

D5 guard, skillscan, LLM adapters, report, demo.

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
python -m hares eval --split dev --defenses D0,D1,D2
python -m hares verify-freeze
```
