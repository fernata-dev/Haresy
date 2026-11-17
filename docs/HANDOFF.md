# HANDOFF

_Updated at every milestone. Read this first if you are continuing the work._

## Status: m6 done (report generator + demo); pilot NOT RUN

| milestone | state |
|---|---|
| m1 harness | DONE |
| m2 D2 scanner + freeze | DONE (tag `freeze-scanner`) |
| m3 D5 guard, residual risk, benign utility | DONE |
| m4 skillscan | DONE |
| m5 LLM adapters + pilot | adapters DONE; pilot NOT RUN (see below) |
| m6 report + demo | DONE |
| m7 docs + self-audit | next |

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

## D5 capability guard (m3)

- `src/hares/defenses/d5_guard.py`. `authorize(tool, args, manifest, is_tainted)` never receives
  content text. Ablation variants: `D5-tools`, `D5-args`, `D5-taint`, `D5` (all three).
- Property test `tests/test_guard.py::test_guard_decisions_are_identical_across_languages_and_encodings`
  checks the guard's decision trace depends only on (intent, source, task).
- Taint = byte-exact match of a value against the attacker-controlled part of untrusted content
  (email BODY, page text, injected skill / tool-description text). Headers are trusted metadata.
  Known, measured limitation: encoded addresses are not seen as tainted.
- Residual risk: `in_scope_tamper` (allowed channel, harmful content) and `override` (task lost
  even when the harmful call is blocked: `task_completed_under_attack` table).
- Cost: `delegation` benign cases (a real request to e-mail a third party) are blocked by
  D5-args / D5-taint / D5. Measured as lost utility.
- Statistics: every table cell also has a cluster-bootstrap CI over authored texts
  (`cluster_ci_lo/hi`), omitted when a cell has < 5 authored texts.

## Skill scanner (m4)

- `python -m hares scan-skill PATH [--allow host,...] [--json|--sarif] [--fail-on high]`
- Files are read as bytes and decoded; nothing is executed or fetched (test: canary file).
- Reuses the frozen D2 scanner (imports it; does not modify it) on: front-matter `description`
  (escalated: always loaded into context), visible paragraphs, HTML/Markdown comments,
  CSS-hidden spans, decoded Base64 / data-URI / hex blobs, decoded Unicode tag characters,
  and each string of a JSON tool manifest (reported with its JSON path).
- Own rules: bidi controls (Trojan Source), zero-width in words, Latin/Cyrillic mixing,
  addresses outside an allowlist, shell patterns (report only). Fixtures in `fixtures/`.
- Not evaluated on a held-out corpus: only fixture tests. Do not report detection rates for it.

## Real-LLM adapters and pilot (m5)

- `src/hares/agents/llm_adapter.py`: `OllamaClient` (OLLAMA_HOST, MODEL) and
  `OpenAICompatClient` (BASE_URL, API_KEY, MODEL; HARES_* variants win). stdlib urllib only.
  Temperature 0, fixed seed, every request/response appended to `results/raw/*.jsonl`
  (git-ignored). `--max-calls` is a hard cap; interrupted episodes are dropped, never scored.
- `src/hares/agents/protocol.py`: one-JSON-tool-call protocol + robust parser (fences, <think>,
  OpenAI tool_calls, string arguments, single quotes). One format-correction retry per turn.
- `src/hares/agents/fake_llm_server.py`: scripted responder used ONLY by tests (NOT A MODEL).
- **Pilot status: NOT RUN.** The build environment had no Ollama, and ollama.com /
  huggingface.co were blocked, so no real model existed. The endpoint Claude Code itself uses
  was deliberately NOT used (rule 2: only a user-configured endpoint). `results/pilot_status.json`
  records this. Plan: test split, langs en,arz,arabizi x encodings none,b64,zwsp x sources
  email,webpage; defenses D0,D1,D2,D5; N=3 -> 81 cases, 972 episodes, ~3.9k calls.

### Student: how to run the pilot on your laptop

```bash
# 1. install Ollama from ollama.com, then pull a model that knows Arabic, e.g.
ollama pull qwen2.5:7b-instruct
# 2. check the connection (one request)
python -m hares llm-check --agent ollama --model qwen2.5:7b-instruct
# 3. see the plan and estimate, then run it (several hours on CPU; leave it overnight)
python -m hares pilot --agent ollama --model qwen2.5:7b-instruct --dry-run
python -m hares pilot --agent ollama --model qwen2.5:7b-instruct --yes
# 4. rebuild the report and the go/no-go file
python -m hares report
```

Record in your logbook: model name, the digest printed by llm-check, the date, your machine.

## Report and demo (m6)

- `python -m hares report` reads `results/` and writes `report/index.html`, `report/results.json`,
  `report/tables/*.csv`, `CLAIMS_ALLOWED.md`, `CLAIMS_NOT_ALLOWED.md`, `docs/PILOT_DECISION.md`,
  and the `<!-- BEGIN GENERATED:... -->` blocks in README.md and docs/CLAIM_AUDIT.md.
  Every number goes through `report.Facts` (value + results file + JSON path).
- Paired comparisons: exact McNemar at TEXT level (one pair per authored text, majority outcome)
  is the one to quote; case-level p-values are shown but are optimistic (correlated variants).
- `python -m hares demo` (127.0.0.1:8765): Arabic RTL UI, three tabs. `demo/api.py` only adapts
  JSON to the evaluator's functions (`tests/test_demo.py` checks verdict parity with the runner).
- Post-freeze change mechanism: `docs/post_freeze_changes.json` (sha256-pinned). One entry: the
  D4 no-download safety fix (no effect on results). The freeze tag was never moved.

## What is not there yet

final docs (README, LIMITATIONS, CLAIM_AUDIT, AI_PROVENANCE), clean-checkout reproduction.

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
python -m hares eval --split dev          # all simulator defenses, writes results/sim_dev.json
python -m hares scan-skill fixtures/malicious_skill.md
python -m hares eval --split test         # refuses if scanners changed without a recorded entry
python -m hares report
python -m hares demo                      # http://127.0.0.1:8765/
```
