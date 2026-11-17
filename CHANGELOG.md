# CHANGELOG

All notable changes. **Any change to a frozen scanner file after git tag
`freeze-scanner` MUST be listed in the "Post-freeze scanner changes" section**
(HARD RULE 4), with the reason and whether test-split results were regenerated.

## Post-freeze scanner changes

Machine-readable list: `docs/post_freeze_changes.json` (file + sha256 of the new content).
`python -m hares verify-freeze` accepts a frozen file that differs from tag `freeze-scanner`
ONLY if its exact sha256 is recorded there, and every results file and the report list it.

1. **2026-11-17 — `src/hares/defenses/d4_cpt.py` — safety fix, no effect on results.**
   Found while screenshotting the demo: `tiktoken.get_encoding("cl100k_base")` tries to download
   its vocabulary from the internet, which breaks HARD RULE 2 (no network calls except a
   user-configured LLM endpoint). The attempt failed in the build environment (blocked by the
   proxy), so D4 was skipped in every run. D4 now checks tiktoken's local cache first and never
   downloads. D4 is skipped before and after the change, so no number changes. The freeze tag was
   NOT moved.

## Post-freeze inspections (no code changed)

- 2026-11-17, after the first test-split run: D2's reasons on the 15 test base texts were
  printed (read-only) to check whether any miss was caused by a code bug rather than by the
  lexicon. None was found: the misses come from wording absent from dev. The scanner was NOT
  changed. Anyone continuing this work must not add those test phrasings to the lexicon; new
  lexicon entries must come from new dev texts, followed by a NEW freeze tag and a NEW test set.

## History

- **Reproducibility bug found by CI (fixed):** the cluster-bootstrap CI used numpy's random
  generator when numpy was installed and Python's `random` otherwise, so results digests depended
  on whether an optional package was present. GitHub CI (no numpy) got different digests than the
  build container (numpy) on every push since m3 (`verify-repro` failed there). The m7
  "clean-checkout reproduction" was done in the same container and could not catch it. Fix: one
  pure-Python generator always; regression test; results regenerated (Wilson CIs, counts and rates
  are unchanged; only cluster-bootstrap intervals move). CI now runs on Linux, Windows and macOS,
  with and without numpy. Also: LF line endings pinned (`.gitattributes`) because the freeze check
  compares bytes; UTF-8 forced on subprocess pipes (Windows).
- `pilot --authors student`: run the real-model pilot on the student's own texts only (empty set is
  refused with instructions); install/run commands added to docs/STUDENT_GUIDE.md (checked in a fresh clone).
- m14: new real recording under the name Bawwab (allowlist vs taint mode, D5-taint vs D6), docs updated.
- m13: Bawwab policy hardening (Base64/percent-encoded and disguised destinations, numeric IP forms,
  destination-named arguments, punycode for look-alike hosts) and **taint mode** (MCP proxy: outputs
  and descriptions; Claude Code: PostToolUse hook + per-session host store). Benchmark: new guard
  variant **D6** (taint over normalised/decoded content), added to the simulator defaults; designed
  after D5-taint's dev and test numbers were seen (LIMITATIONS 4b). D5 and the frozen scanners are
  unchanged; results regenerated.
- m12: MCP wrapping verified with the real Claude Code 2.1.326 and Gemini CLI 0.68.0 (`mcp list`
  health checks, clean env without credentials): docs/VERIFICATION.md, tools/verify/verify_agents.sh.
  Hook not verified (`claude mcp list` does not validate hooks: shown with a broken value).
- m11: product renamed **Bawwab** (بوّاب, the Egyptian building doorman: decides by destination and
  what is carried out, not by language). Package `src/bawwab`, command `bawwab` (`zorfa` kept as an
  alias), config dir `~/.bawwab`; servers and hooks wrapped under the old name are still recognised.
  The research package `hares` and its frozen files are unchanged.
- post-m10: real terminal recording (pty, fake HOME) -> `docs/media/` (11 screenshots, MP4, raw cast,
  replay page) and `tools/record/`; discover fix (analyse the real server behind the proxy), found
  while reviewing the recording; README demo section; prompt log, provenance and claim audit updated.
- m10: opt-in `protect` (dry-run diff with secret masking, typed confirmation, timestamped backup,
  atomic writes, validation, rollback), `unprotect`, MCP stdio policy proxy (hides poisoned tools,
  blocks denied calls with isError), Claude Code PreToolUse hook (fails closed), policy engine.
- m9: distribution renamed `zorfa` (v0.2.0) with `zorfa` and `hares` commands; agent list shipped as
  package data; README install section.
- m8: Zorfa discover (read-only) for the documented agents in data/supported_agents.json
  (claude-code, gemini-cli), secret redaction, skill scanning, JSON + text report; shim fix
  (src always first on sys.path).
- cleanup: 16 third-party wheel files (~11 MB) that a network probe (`pip download`) had left in
  the project folder were committed by mistake in m1 (`dbe7e8b`). They are removed from the tree
  in this commit and `*.whl` is ignored. They remain in git history: rewriting history would change
  every commit hash that the freeze tag, `docs/tags.json` and the results files refer to.
- post-m7: tags pinned in `docs/tags.json` (tag pushes refused by the session's remote);
  `restore-tags` command; freeze check falls back to the pinned commit and detects moved tags.
- m6: report generator (HTML/CSV/JSON, claims, go/no-go, generated doc blocks, text-level McNemar),
  Arabic RTL demo server sharing the evaluator's code paths, recorded post-freeze change mechanism.
- m5: Ollama + OpenAI-compatible adapters, robust tool-call parser, raw logging, max-calls cap,
  pilot command (recorded as NOT RUN: no model available), scripted test endpoint.
- m4: skill scanner (front matter, hidden carriers, decoded blobs, bidi/tag/zero-width,
  homoglyphs, JSON tool manifests, allowlist, shell patterns report-only), SARIF output.
- m3: D5 capability guard (tools / args / taint, ablation variants), path normalisation,
  body-only taint, residual-risk tables, cluster-bootstrap CI by authored text.
- m2: D2 normaliser + concept lexicon (en/msa/arz/arabizi, Arabizi skeletons, cross-script
  matching), extended encoders (tatweel, tashkeel, homoglyph, translit, arabizi_noise, stacks),
  optional D3 (LLM judge) and D4 (chars per token). Developed on dev only; tag `freeze-scanner`.
- data: test split committed before the lexicon (tag `data-test-before-lexicon`).
- m1: harness - mock world, tasks + manifests, worst-case simulated agent,
  attack schema/loader/encoders, D0, D1, runner, Wilson CI, exact McNemar, tests.
