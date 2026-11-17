# CHANGELOG

All notable changes. **Any change to a frozen scanner file after git tag
`freeze-scanner` MUST be listed in the "Post-freeze scanner changes" section**
(HARD RULE 4), with the reason and whether test-split results were regenerated.

## Post-freeze scanner changes

_None._ (Checked by `python -m hares verify-freeze`.)

## History

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
