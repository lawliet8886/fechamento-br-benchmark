# Fechamento BR — separate confirmation experiment v1

Status: candidate before reviewer approval and before any new model answers. Preserve the original 28-case / 84-response study byte-for-byte. Gabriel approved the 12-new-case, two-repetition follow-up on 08 October 2026, with no personal spending.

## Question and fixed scope
Do the original two failure categories recur after the monetary values and source-rule wording change? Eight explicit-convention target cases form four contrast pairs; four controls test genuine ambiguity, a normal decimal, forbidden rounding, and explicit zero. Cases are in cases.json. They were authored after seeing the original results, so this is a targeted follow-up, NOT a blind or independently sampled holdout.

12 new cases × 3 original models × 2 repetitions = at most 72 new requests. In each repetition use this model order: google/gemini-3.8-flash; anthropic/claude-sonnet-4-6@default; google/gemma-4-26b-a4b. Case order is fixed in cases.json. One attempt per case per repetition, each in its own native child task and conversation. No success-dependent retries or model substitutions.

## Outcomes fixed before measurement
Primary: unchanged original strict grader (correct status, exact canonical string, exact JSON container), with 12-case total and 8-target-case total separately per model and repetition; four controls reported individually. Keep all original raw responses.

Secondary descriptive failure categories, mutually exclusive in this order: strict_pass; json_container_violation; unnecessary_abstention (gold ok but predicted ambiguous); wrong_decision (other status mismatch); canonical_format_only (both statuses ok and exactly equal finite Decimal magnitudes but noncanonical required string); wrong_value. Numerical equivalence never replaces the strict score. No postprocessing or repairing the primary responses.

Preserve the four frozen scientific source modules. Reuse their global prompt and strict grader unchanged, with timeout=120 s, client retries=0, workers=2, seed request=0 and the same temperature policy. Execute using the separately hashed confirmation_runner.py, derived from the reviewed public-v2 fail-fast adapter, NOT the original final-v1 dispatcher. The first provider/native-child failure stops new submissions and all following attempts; one already-running sibling may complete. Each 12-case attempt has a confirmation-specific manifest; the outer schedule binds six attempts and the protocol hash. The separate verifier recomputes grades and matches 72 prompts/answers and model identity to six native parent traces; it never extends the original verifier or RUN_INDEX. No claim that repetitions are independent random draws or that providers honor identical sampling.

## Safety and integrity
SDK must be the reviewed version 0.6.1 with native run cache explicitly disabled. Only Kaggle native included model quota; verify available quota and platform settings before execution. No personal API keys, prepaid account, paid Cloud, purchases, subscriptions or paid fallback. Quota exhaustion stops requests. Infrastructure failure leaves a recorded incomplete attempt without total score; no fabricated zero. Original records, published task and leaderboard must not be overwritten.

Use a separate new notebook/working-output path for the supplementary run. Reusing the original task function as an ephemeral notebook task is allowed; never click Build/Update Task for the original benchmark. Archive native traces and original answers separately and reconcile them after completion. No need to publish a new benchmark or a second DEV entry.

Before model calls, record exact corpus, source, builder, notebook and protocol hashes plus the Codex review receipt. Do not change cases, gabarito, grading rules or schedule after inspecting answers. Original source hashes and supplementary builder hashes must be separately identified rather than pretending changed code is the original instrument. Hashes detect accidental drift, not external authorship attestation.

## Review and stopping
Codex Desktop GPT-6.1 Sol / Maximum reviews cases, gold, protocol and instrument before the run. It is a separate AI reviewer, not a blind human audit; it has seen the original study. The reviewer rederives answers and compares them with visible gold labels. The labels and original study are visible; there is no blinding or knowledge isolation.

Stop after the predefined six attempts (or on infrastructure/quota blocking further safe execution). Report disconfirming results and all incomplete attempts, not only supporting cases. Correlated pairs, constructed cases and two repetitions do not justify population confidence intervals or universal model rankings. If the models pass this follow-up, state only that the original failures did not recur on these new values and contexts under the observed conditions. Values and wording changed together, and time/provider conditions may also change; the cause of any difference remains unestablished. Do not keep testing until a preferred finding appears.
