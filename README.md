# Hares (حارس)

**Hares reduces the damage an injected instruction can cause; it does not stop a model from following it.**

Hares is a mock-environment benchmark and toolkit for **indirect prompt injection** against
tool-using LLM agents, built around one question:

> Do defenses against indirect prompt injection (keyword filters, scanners, classifiers) degrade
> when the attack is written in Egyptian Arabic (arz), Modern Standard Arabic (msa), Arabizi
> (Arabic in Latin letters) or mixed text, and/or is encoded (Base64, leetspeak, zero-width
> characters, ROT13, spaced letters)? Does a language-agnostic, task-bound capability guard hold
> regardless of language, what does it cost (blocked legitimate tasks), and what does it miss
> (attacks that stay inside allowed capabilities)?

Injection sources covered: e-mails, web pages, third-party skill files (`SKILL.md`) and tool
descriptions.

> حارس مشروع ISEF (برمجيات / أمن سيبراني). كل حاجة بتشتغل في بيئة وهمية: العنوان الوحيد للمهاجم
> هو `attacker@test.local` ومفيش أي إرسال حقيقي. نصوص الهجوم الحقيقية لازم يكتبها الطالب بنفسه
> (شوف `data/attacks/student_written/README.md`).

## Status

This repository contains **tables, not conclusions**. What the numbers do and do not support is
generated into [`CLAIMS_ALLOWED.md`](CLAIMS_ALLOWED.md) and
[`CLAIMS_NOT_ALLOWED.md`](CLAIMS_NOT_ALLOWED.md); the go/no-go rule is in
[`docs/PILOT_DECISION.md`](docs/PILOT_DECISION.md); weaknesses are in
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md). Read the limitations before quoting any number.

### Worst-case simulator, test split (generated)

<!-- BEGIN GENERATED:summary -->
Source: `results/sim_test.json` (digest `9e1eaa7b43488798`, commit `42427c42c8`, seed 1337). Agent: **worst-case simulated agent, not a real model**.

| defense | attack success (Wilson 95% CI) | benign utility | benign flagged |
|---|---|---|---|
| D0 | 100.0% [99.7%, 100.0%] (1224/1224) | 100.0% [93.2%, 100.0%] (53/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D1 | 100.0% [99.7%, 100.0%] (1224/1224) | 100.0% [93.2%, 100.0%] (53/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D2 | 94.1% [92.7%, 95.3%] (1152/1224) | 100.0% [93.2%, 100.0%] (53/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D5-tools | 45.8% [43.1%, 48.6%] (561/1224) | 100.0% [93.2%, 100.0%] (53/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D5-args | 33.3% [30.7%, 36.0%] (408/1224) | 90.6% [79.7%, 95.9%] (48/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D5-taint | 42.2% [39.4%, 44.9%] (516/1224) | 90.6% [79.7%, 95.9%] (48/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D5 | 33.3% [30.7%, 36.0%] (408/1224) | 90.6% [79.7%, 95.9%] (48/53) | 0.0% [0.0%, 6.8%] (0/53) |
| D2+D5 | 33.3% [30.7%, 36.0%] (408/1224) | 90.6% [79.7%, 95.9%] (48/53) | 0.0% [0.0%, 6.8%] (0/53) |

Attack cases: 1224 from 15 authored texts; authors: {'ai-draft': 15}. Benign cases: 53.

Not run: D4 (skipped: D4: cl100k_base vocabulary is not in the local tiktoken cache; Hares never downloads it (see the D4 docstring to enable it)).

Scanner freeze: OK; post-freeze changes recorded: 1 (`src/hares/defenses/d4_cpt.py`, affects results: False; see CHANGELOG.md).
<!-- END GENERATED:summary -->

### Real-model pilot (generated)

<!-- BEGIN GENERATED:pilot -->
Real-model pilot: **NOT RUN** (2026-11-17T08:21:56Z). Reason: Ollama not reachable: URLError: <urlopen error [Errno 111] Connection refused>. Source: `results/pilot_status.json`. No statement about real models is supported.
<!-- END GENERATED:pilot -->

Every number above is written by `python -m hares report` from a file in `results/`;
[`docs/CLAIM_AUDIT.md`](docs/CLAIM_AUDIT.md) maps each one to its file and JSON path.

## Safety

- Every tool (`read_page`, `read_email`, `read_file`, `send_email`, `http_post`) is a Python
  function over in-memory dictionaries. Nothing is sent, fetched or written outside the process.
- The only attacker destinations are `attacker@test.local` and `http://test.local/attacker-inbox`
  (`.local` is never resolved). The data validator rejects any other address or URL.
- Mock "secrets" are synthetic strings (`FAKE-PASSWORD-hares-...`).
- The skill scanner reads files as text. It never executes, imports or fetches anything; shell
  patterns are reported only (a test checks a canary file is never created).
- No network calls, except to an LLM endpoint **you** configure for the optional real-model runs.
  D4 never downloads its tokenizer (a test blocks all sockets during a full simulator run).

## Quick start

Python 3.11+, standard library only. `pytest` for tests. Optional: `numpy` (faster bootstrap),
`tiktoken` with a locally cached `cl100k_base` vocabulary (enables D4).

```bash
python -m pytest                                  # all tests
python -m hares validate                          # check data files, show the matrix
python -m hares eval --split dev                  # development split (scanner was tuned here)
python -m hares eval --split test                 # refuses if frozen scanners changed (unrecorded)
python -m hares verify-repro                      # re-run and compare digests with results/
python -m hares report                            # report/index.html + claims + generated blocks
python -m hares demo                              # Arabic UI on http://127.0.0.1:8765/
python -m hares scan-skill fixtures/malicious_skill.md
python -m hares scan-skill path/to/skills --allow docs.example.test --sarif > scan.sarif
```

`python -m hares` works from a fresh checkout (a small `hares.py` shim puts `src/` on the path);
`pip install -e .` also installs a `hares` command.

## What is in the box

| part | what it does |
|---|---|
| `env/` | mock world, three tasks (`summarize_page`, `reply_email`, `search_notes`), each bound to a permission manifest (allowed tools + argument constraints) |
| `agents/obedient_mock.py` | **worst-case simulated agent, not a real model**: obeys every injection in every language and encoding using the attack's ground truth |
| `agents/llm_adapter.py` | Ollama and OpenAI-compatible adapters (temperature 0, fixed seed, N repeats, raw logs, call cap) |
| `attacks/` | JSONL schema + validators, encoders: core (`b64`, `leet`, `zwsp`, `rot13`, `spaced`), extended (`tatweel`, `tashkeel`, `homoglyph`, `translit` Arabic→Arabizi, `arabizi_noise`), stacked (`translit+leet`, …) |
| `defenses/` | D0 none · D1 English keyword list · D2 normaliser + concept lexicon (en/msa/arz/arabizi, Arabizi consonant skeletons, cross-script matching, Base64/ROT13/tag decoding) · D3 LLM judge (real model only) · D4 chars-per-token (local tokenizer only) · D5 capability guard (tool allowlist, argument constraints, taint) with ablation variants |
| `skillscan/` | static scanner for `SKILL.md` / tool manifests: hidden carriers, decoded blobs, bidi/zero-width/tag characters, homoglyphs, concealment and exfiltration instructions in four language varieties, external destinations, shell patterns; JSON or SARIF |
| `eval/` | runner, ASR / utility / false positives, Wilson 95% CI, cluster bootstrap by authored text, exact McNemar (text level and case level), freeze check, reproduction check, report |
| `demo/` | local Arabic RTL page: playground, results matrix, skill scanner; calls the evaluator's own functions |

Design details, threat model and metric definitions: [`docs/DESIGN.md`](docs/DESIGN.md).

## Research integrity

- **Dev/test discipline.** The D2 lexicon was written from the `dev` split only. The test split
  was committed first (tag `data-test-before-lexicon`), then the scanners were frozen (tag
  `freeze-scanner`). `eval --split test` refuses to run if a frozen file changed unless the
  change is sha256-pinned in `docs/post_freeze_changes.json` and described in `CHANGELOG.md`.
- **No hand-typed numbers.** Report, claims, go/no-go and the blocks above are generated.
- **Reproducible.** Fixed seed, digests over all rows and tables, `verify-repro`.
- **AI use.** All code and the starter texts were written by an AI assistant; see
  [`docs/AI_PROVENANCE.md`](docs/AI_PROVENANCE.md) and [`docs/prompt_log.md`](docs/prompt_log.md).
  The attack texts that count must be written by the student; AI drafts are capped at 5 per
  language and labelled `author: ai-draft`.

## For the student

Start with [`docs/STUDENT_GUIDE.md`](docs/STUDENT_GUIDE.md) (Arabic) and
[`docs/HANDOFF.md`](docs/HANDOFF.md).
