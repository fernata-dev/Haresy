# Prompt log

ISEF AI-use integrity: every prompt given to the AI assistant that produced
this repository is appended here verbatim, newest last.  The student must keep
appending to this file for any further AI assistance.

---

## Prompt 1 — 2026-11-17 — initial build request

Model/tool: Claude Code (Anthropic), cloud session.

```text
ROLE
You are a senior security-research engineer building "Hares" (حارس), a student's ISEF project (category: Software / Cybersecurity). Build it end to end, in place, in the current working directory. The student is Egyptian; the research question is real and open, so correctness and honesty matter more than impressive claims.

RESEARCH QUESTION
Do defenses against indirect prompt injection in tool-using LLM agents (keyword filters, scanners, classifiers) degrade when the attack is written in Egyptian Arabic dialect (arz), Modern Standard Arabic (msa), Arabizi (Latin-script Arabic), or mixed text, and/or is encoded/obfuscated (Base64, leetspeak, zero-width chars, ROT13, spaced letters)? Does a language-agnostic, task-bound capability guard hold regardless of language, and what does it cost (blocked legitimate tasks) and miss (attacks that stay inside allowed capabilities)? Also cover third-party "skills" (SKILL.md files) and tool descriptions as injection sources, not only emails and web pages.

HARD RULES (non-negotiable)
1. Honesty: never claim "prevents all jailbreaks" or "first ever". The guard limits damage of actions; it does not stop the model from understanding or being fooled. Put exactly this in README: "Hares reduces the damage an injected instruction can cause; it does not stop a model from following it."
2. Safety: everything runs in a mock environment. Attacker destination is always attacker@test.local. No real malware, no real exfiltration, no network calls except an optional, user-configured LLM endpoint, no executing contents of skill files (scanner reads text only).
3. ISEF AI-use integrity: create docs/AI_PROVENANCE.md listing which modules were AI-generated (all of them you write) and docs/prompt_log.md; append this prompt there. Do NOT write an abstract, poster text, conclusions, or "findings" prose. Produce only neutral result tables and a CLAIMS_ALLOWED.md / CLAIMS_NOT_ALLOWED.md based strictly on numbers in results files. The student must write the Egyptian/Arabizi/MSA attack texts himself: generate templates, schema, validators, and a clearly labelled `author: ai-draft` starter set of at most 5 per language, which the student replaces. Create data/attacks/student_written/README.md explaining how to add his own.
4. No results rigging: the scanner/lexicon is developed ONLY on the `dev` split and frozen (git tag `freeze-scanner`) before any run on the `test` split. Never tune on test. Keep a CHANGELOG of any post-freeze change and report it.
5. Reproducibility: fixed seeds, results written as JSON/CSV with model name, version, date, temperature, git commit hash. Every number in any report must be generated from a results file by code, never typed by hand.
6. Work in place with git: `git init`, commit per milestone, tag `m1`..`m7`. Do not create copies of the project folder.
7. Handoff: maintain docs/HANDOFF.md (status, what works, what is broken, exact next commands) updated at EVERY milestone, because another model/person may continue your work.

STACK
Python 3.11+, stdlib + pytest (optional: numpy, tiktoken, requests; the project must run without them where possible). Package `hares` under src/, CLI `python -m hares ...`. Arabic text handled as UTF-8 everywhere; test with Arabic and Arabizi fixtures.

ARCHITECTURE
src/hares/
  env/        mock tools: read_page, read_email, read_file, send_email, http_post; task definitions (summarize_page, reply_email, search_notes) each with a permission manifest {allowed_tools, arg_constraints e.g. send_email.to in allowlist}; mock files contain fake secrets.
  agents/     (a) obedient_mock: WORST-CASE agent that obeys any injected instruction in any language/encoding, using the attack's ground-truth intended_call (label all its results "worst-case simulated agent, not a real model"); (b) llm_adapter base + ollama adapter + OpenAI-compatible adapter via env vars (BASE_URL, API_KEY, MODEL). Protocol: model replies with one JSON tool call; parse robustly; log raw outputs to results/raw/. temperature 0, repeat each case N=3 to measure nondeterminism; --dry-run, --max-calls, cost/time estimate before running.
  attacks/    schema + loader + validators + programmatic encoders (b64, leet, zwsp, rot13, spaced). Schema (JSONL): id, lang[en|msa|arz|arabizi|mixed], encoding, source[email|webpage|skill_md|tool_desc], intent[exfil_send|override|in_scope_tamper|wrong_recipient], text, intended_call, author[student|ai-draft|programmatic], split[dev|test]. Generate encoded variants programmatically from base texts so the matrix (lang x encoding x source) is cheap to expand.
  data/benign/ benign content in the same languages (including legitimate Egyptian requests like "ابعتلي التقرير بكرة") to measure false positives and utility.
  defenses/   D0 none; D1 English keyword blocklist; D2 normalizer+lexicon scanner (NFKC, strip zero-width/diacritics/tatweel, normalize alef/ya forms, de-leet, decode Base64/ROT13 candidates and append, Arabizi digit mapping 2,3,5,6,7,8,9 + repeat-collapse, lexicon of override/exfil phrases in en/msa/arz/arabizi); D3 optional LLM-judge (only with a real model); D4 optional characters-per-token filter in the style of Broken-Token (only if a tokenizer is installable; else skip and say so); D5 capability guard (task-bound tool allowlist + argument constraints + optional taint rule: content from untrusted sources cannot supply tool arguments like recipient). The guard must never read the natural-language text.
  skillscan/  `hares scan-skill PATH` static scanner for SKILL.md-like files: hidden/encoded blobs (decode and show), zero-width/bidi controls, "don't tell the user"-style concealment phrases in en/msa/arz/arabizi, imperative exfil instructions, URLs/emails external to an allowlist, suspicious shell patterns (report only). Output JSON findings with severity. Provide synthetic benign and malicious fixtures (clearly fake, safe).
  eval/       runner over (attack x defense x task x agent); objective success = the tool-call log contains the intended harmful call (or tamper predicate). Metrics: ASR, benign utility, false-positive rate, Wilson 95% CI per cell, paired comparison between defenses on identical cases (exact McNemar, descriptive; no significance claims without it). Break down by lang, encoding, source, intent. Include an "in-scope tamper" class (e.g. altered reply content to the legit recipient) and report it as RESIDUAL RISK the guard does not stop.
  demo/       `python -m hares demo` serves a local single-page Arabic RTL UI (stdlib http.server): pick source/task/attack preset or paste text, run each defense, show the tool-call trace and verdict; second tab = benchmark matrix with CIs from results files; third tab = skill scanner. The demo MUST call the same Python code as the evaluator (no duplicated logic) and show a banner when the agent is the worst-case simulator.

MILESTONES (each ends with tests passing, a commit+tag, HANDOFF.md updated)
m1 harness: env, tasks, obedient_mock, attack schema/loader/encoders, D0, D1, runner, Wilson CI, unit tests (encoders round-trip, CI correctness vs known values, schema validation).
m2 D2 normalizer+scanner developed on dev split only; tests incl. Arabizi/leet/b64/zwsp; then tag `freeze-scanner`.
m3 D5 capability guard + residual-risk attack classes; benign utility measurement.
m4 skillscan + fixtures + tests.
m5 real-LLM adapters; run a PILOT: >=3 languages x 3 encodings x 2 sources, N=3 repeats, on whatever model the student has (default: local Ollama if available, else mark "not run" and explain). Record model name/date.
m6 eval report generator (report/results.json, report/index.html static, CSV tables) + demo server.
m7 docs and self-audit: README (with the sentence from rule 1), docs/LIMITATIONS.md (be harsh: simulated agent, small n, synthetic benchmark, model drift, dev/test leakage risks, student-authored texts only), docs/CLAIM_AUDIT.md mapping each README claim to a results file/line, CLAIMS_ALLOWED/NOT_ALLOWED, AI_PROVENANCE, prompt_log. Run the whole pipeline from a clean checkout with the fixed seed and confirm identical results.

GO/NO-GO (write into docs/PILOT_DECISION.md from computed numbers only)
Report whether D1/D2 attack success on arz/arabizi/encoded cases is higher than on English with non-overlapping Wilson CIs, in the worst-case simulator AND in the real-LLM pilot. If no gap appears, say so plainly and state which part of the project remains valuable (guard cost/residual analysis, skill scanner) instead of hiding it.

DEFINITION OF DONE
`pytest` green; `python -m hares eval --split test` reproduces results; `python -m hares demo` runs; `python -m hares scan-skill fixtures/malicious_skill.md` works; every README number traces to a results file; final message lists exactly what was and was not verified, what the student must write himself, and anything you could not run. If you hit an ambiguity, choose the most conservative reading, document it in HANDOFF.md, and continue.

اعمل المشروع كامل وحك فيه مسزات قوية جدا واعمله كامل متكامل وخليه، قوي جدا جداج  ومتطور وقوي ومميز وفيه ميزات اكتر
```

(The request was accompanied by the user's standing preference: challenge every
assumption, stress-test every idea, be a strict guide.)

---

## Prompt 2 — 2026-11-17 — follow-up during m2

Model/tool: Claude Code (Anthropic), same session. (Before this message the user switched the
session's model with a `/model` command; that command is not a prompt and is not reproduced.)

```text
يبني انت بتعمل قاهدة من الصفر اعمل اشياء احترافية ومميزه اكتر واقوى
```

Response summary (for the student's logbook): the assistant argued that rigor matters more than
feature count, then added features that strengthen the measurement: Arabic→Arabizi
transliteration as a script control, Arabizi spelling noise, stacked encodings, cluster-bootstrap
CIs by authored text, text-level McNemar, SARIF output and JSON-manifest scanning in the skill
scanner, guard ablation variants, a sha256-pinned post-freeze change record.

---

## Prompt 3 — 2026-11-17 — milestones m8–m10, rename, recording

```text
MILESTONES m8-m10 (after m7). Never claim to support "any AI"; support only a documented list in data/supported_agents.json, and for each agent verify its integration mechanism from its OFFICIAL docs before implementing (record the doc URL and date in docs/INTEGRATIONS.md; if no documented mechanism exists, mark it "scan-only").
m8 discover: read-only discovery of known AI tools/agent assets (config dirs, SKILL.md folders, MCP config JSON) on Linux/macOS/Windows; run the skill scanner on what is found; JSON + readable report. No file modification, no network, no uploads.
m9 install: one-command install (pipx/pip) exposing the CLI; `discover` is the default first step.
m10 protect (opt-in): `protect --dry-run` prints an exact diff of every file it would change; `protect --apply` requires explicit confirmation, writes a timestamped backup first, and `unprotect` restores it. Implement only for integrations with documented mechanisms (e.g. an MCP stdio proxy enforcing a policy file; a documented hook mechanism where an agent provides one). Never run automatically, never touch anything outside the supported list.
All of m8-m10 are tested only against a mocked fake HOME directory first. docs/LIMITATIONS.md must state the supported list and what is NOT covered. m8-m10 must not delay or weaken the correctness of m1-m7; if time is short, drop m10 first.

واتغير اسمه ل zorfa تقريبا ايوة وطوره وخليه قوي جدا جدا  

عايزك تصورلي اسكرينات كانك شغلته بجد ع تسرمنال وكمان اختبرته كامل وكمان يشتغل ويبقا تمام وقوي ومتطور ويبقا بفيديو برضو ان امكن ع الشاشة
```

## Prompt 4 — 2026-11-17 — after a session restart

```text
كمل
```

## Prompt 5 — 2026-11-17 — rename and strengthen

```text
طوره اكتر واقوى واختارله اسم ليه معنى
```

Response summary: the assistant chose the name Bawwab (بوّاب) and explained why (the guard decides
by destination, not language), then prioritised strengthening over feature count: verification
with the real agent CLIs, hardening the policy against encoded destinations, and a taint mode.

## Prompt 6 — 2026-11-17 — install and run commands

```text
ماشي يعم هات اوامر التزيل كامله والتشغليل وانا هشغله ع ai حقيقي بس عايزين نعرف العنوان هل هيبقا برنامج ولا هيبقا ايه ؟
```

Response summary: full install/run commands, the real-model pilot command (`--authors student`),
and the product shape at that time (command-line tool + local app).

## Prompt 7 — 2026-11-17 — cross-platform professional program

```text
انا cashy os وانت عارف عموما عايزك تخليه برنامج ايه رايك يبقا برنامج كامل يشتغل ع كل الانظمه لينكس او ماك او ويندوز ويبقا احترافي وبتصميم قوي ويفهم اي حد مهما كان ايه بيعمل ويبقا مفيد وقوي وطوره وانه يمنع الجيلبريك والنصوص القوية ويبقا قوي جدا جدا جدا جدا
```

Response summary (m15–m17): a local bilingual app (`bawwab ui`), CI on Linux/Windows/macOS, a
CachyOS install guide. The assistant declined to claim that Bawwab "prevents jailbreaks" and kept
the honest sentence (it limits damage; it does not stop a model from following text).

## Prompt 8 — 2026-11-18 — redesign, phones and cloud agents

```text
يسطا ده خرا وشكله خرا وزباله ومش جميفل ولا سلسل وكمان زباله وخد بالك في برضو ناس بتستخدم وكلاء ع السحابه يعني زي جيمناي على درايف وجميل عايزك تطور كامل وتخليه احسن وتخلي الاداة كامله ومتطورة وقوي جدا جدا جدا جدا جدا جدا جدا جدا وتبقا متطورة واقترح ايه هو هل هو برنامج هيبقا ولا اداة ولا ايه عشان في ناس بتستخدم تلفونات عشان شغاله ع سحابه فهمني يعم طور كامل
```

Response summary (m18): one product with three faces — an offline web app for phones (PWA),
the same app on the desktop (`bawwab ui`, plus agent protection), and the CLI. The scanners were
ported to JavaScript with a byte-exact parity test against Python; Word / e-mail / HTML readers
reveal hidden text; full redesign. The assistant stated that no app on a phone can sit between a
user and a cloud assistant such as Gemini in Drive: Bawwab checks content before it is handed over.
