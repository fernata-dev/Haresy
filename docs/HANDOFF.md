# HANDOFF

_Updated at every milestone. Read this first if you are continuing the work (person or model)._

## Status: m9 done (install) — m10 next; real-model pilot NOT RUN

### m8–m10 (Zorfa) summary
- Product name: **Zorfa** (`zorfa` command, `src/zorfa/`). The research core keeps the package name
  `hares` on purpose: renaming it would change every import line in the frozen scanner files.
- Supported agents (official docs checked 2026-11-17, see docs/INTEGRATIONS.md): **claude-code**,
  **gemini-cli**. Everything else is listed as not supported with the reason.
- m8 `zorfa discover` (default command): read-only; tests in tests/test_zorfa_discover.py prove no
  writes, no network, no reads of unsupported (.cursor) or secret (.ssh) files, secrets redacted.
- m9 install: `pipx install .` / `pip install .` (distribution `zorfa`, commands `zorfa` and `hares`,
  agent list shipped as package data). Verified in the build container: fresh venv and pipx, run
  from a directory outside the repo. `pipx install git+https://...` depends on repo access.

| milestone | state | tag |
|---|---|---|
| m1 harness (env, tasks, worst-case agent, schema/encoders, D0, D1, runner, Wilson) | DONE | `m1` |
| m2 D2 normaliser + lexicon on dev only, then freeze | DONE | `m2`, `freeze-scanner` (test data before lexicon: `data-test-before-lexicon`) |
| m3 D5 guard + residual risk + benign utility | DONE | `m3` |
| m4 skill scanner + fixtures | DONE | `m4` |
| m5 real-LLM adapters + pilot | adapters DONE, **pilot NOT RUN** | `m5` |
| m6 report generator + demo | DONE | `m6` |
| m7 docs + self-audit + clean-checkout reproduction | DONE | `m7` |
| m8 Zorfa discover (read-only) | DONE | `m8` |
| m9 install (pip/pipx) | DONE (verified: fresh venv + pipx, run outside the repo) | `m9` |
| m10 protect / unprotect / MCP proxy / hook (opt-in) | next | |

## What works (verified in the build environment)

- `python -m pytest` — green (count printed by pytest).
- `python -m hares validate | eval --split dev|test | verify-freeze | verify-repro | report | demo | scan-skill | pilot | llm-check`.
- `eval --split test` reproduces `results/sim_test.json` bit-for-bit (digest), also from a fresh
  `git clone` (see "Clean-checkout reproduction").
- Demo: three tabs checked in headless Chromium with no console errors.

## What is NOT done / broken / not verified

1. **Real-model pilot not run.** No Ollama in the build container; ollama.com and huggingface.co
   blocked; Claude Code's own endpoint deliberately not used (rule 2). `results/pilot_status.json`
   says so. Adapters are tested only against a scripted local endpoint (NOT a model).
2. **D3 (LLM judge)** never run (needs a real model). **D4 (chars per token)** never run (tiktoken
   is installable but its vocabulary could not be downloaded; D4 now refuses to download it).
3. **All attack and benign texts are AI drafts.** No student-written data yet.
4. The skill scanner has no measured detection rate (fixtures only).
5. The GitHub Actions workflow (`.github/workflows/ci.yml`) was written but not run on GitHub.
6. **Git tags were NOT pushed.** The build session may only push its branch; every tag push was
   refused by the remote. All tags (`m1`..`m7`, `data-test-before-lexicon`, `freeze-scanner`) are
   pinned to their commits in `docs/tags.json`. After cloning, run `python -m hares restore-tags`
   (creates them locally, pushes nothing), then `git push origin --tags` yourself if you want them
   on GitHub. `verify-freeze` falls back to the pinned commit when the tag is missing, and refuses
   if a tag exists but points somewhere else (a moved tag).

## Conservative decisions taken (ambiguities in the brief)

1. Data live in top-level `data/` (attacks and benign); code in `src/hares/`.
2. Attacker HTTP destination: `http://test.local/attacker-inbox` (same reserved `test.local`;
   `http_post` only records in memory). Validators reject any other destination.
3. ai-draft cap (≤ 5 per language) applies to every language including English; enforced by code.
   Split per language: 2 dev + 3 test.
4. An encoding is generated for a text only if it changes ≥ 25% of ordinary tokens; N/A cells are
   never reported. Extra encoders (tatweel, tashkeel, homoglyph, translit, arabizi_noise, stacks)
   are reported as separate families from the core five.
5. The simulated agent runs once per case (repeating a deterministic agent would inflate n).
6. A scanner hit withholds the whole content (worst case for scanner utility).
7. Encoders are part of the frozen file set (dropping an encoding a scanner fails on = rigging).
8. Post-freeze changes are allowed only if sha256-pinned in `docs/post_freeze_changes.json` and
   described in CHANGELOG; the freeze tag is never moved. One such change exists (D4 no-download).
9. "Every number generated from results": README numbers live only inside generated blocks;
   prose docs contain no result numbers (method parameters like the 25% coverage rule are not results).
10. Paired tests: text-level exact McNemar is primary; case-level is shown as optimistic.
11. The go/no-go uses the test split; dev is shown as informational only.
12. `hares.py` at the repo root is only a path shim so `python -m hares` works without installing.
13. Model identifiers are kept out of repository files (session policy); AI_PROVENANCE names the
    assistant as "Claude (Anthropic) via Claude Code".

## Layout

```
src/hares/  env/ agents/ attacks/ benign/ defenses/ skillscan/ eval/ demo/ cli.py util.py
data/       attacks/{ai_draft,student_written,templates}  benign/{ai_draft,student_written}
results/    sim_dev.json sim_test.json (+ _rows.csv) pilot_status.json raw/ (git-ignored)
report/     index.html results.json tables/*.csv            (generated)
docs/       HANDOFF LIMITATIONS DESIGN CLAIM_AUDIT AI_PROVENANCE prompt_log PILOT_DECISION
            STUDENT_GUIDE post_freeze_changes.json
fixtures/   malicious_skill.md benign_skill.md malicious_tool_descriptions.json
```

## Exact next commands

```bash
# after cloning: recreate the tags (they could not be pushed from the build session)
python -m hares restore-tags
# sanity
python -m pytest
python -m hares verify-freeze && python -m hares verify-repro

# student data (see data/attacks/student_written/README.md), then
python -m hares validate
python -m hares eval --split dev --authors student
python -m hares eval --split test --authors student --out results/sim_test_student.json
#   (report.py reads results/sim_test.json; to make the student set the main one, write it there
#    instead, after keeping a copy of the AI-draft run)
python -m hares report
python -m hares demo
```

### Real-model pilot (on the student's laptop)

```bash
ollama pull qwen2.5:7b-instruct                       # any local model that knows Arabic
python -m hares llm-check --agent ollama --model qwen2.5:7b-instruct
python -m hares pilot --agent ollama --model qwen2.5:7b-instruct --dry-run
python -m hares pilot --agent ollama --model qwen2.5:7b-instruct --yes   # hours on CPU
python -m hares report                                 # updates PILOT_DECISION, README, claims
```

OpenAI-compatible servers: set `BASE_URL`, `API_KEY`, `MODEL` and use `--agent openai`.

### Changing a scanner later (do it right)

Add NEW dev texts → change the lexicon → run dev → `git tag freeze-scanner-v2` → write a NEW
test set nobody tuned on → update `FREEZE_TAG` in `src/hares/eval/freeze.py` → run test →
document everything in CHANGELOG. Never edit the lexicon in response to test results.

## Clean-checkout reproduction

Done at m7 by cloning the repository into a temporary directory (deleted afterwards), running
`pytest`, `python -m hares eval --split test --out <tmp>` and comparing the digest with
`results/sim_test.json`. Outcome at m7: the fresh clone passed all tests, `verify-freeze` was OK,
and the re-run test-split digest was IDENTICAL to the committed one (also recorded in the
annotated tag `m7`: `git show m7`).
