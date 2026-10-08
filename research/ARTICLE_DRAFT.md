---
title: "Same Score, Different Failure: Fechamento BR"
published: false
tags: devchallenge, kagglechallenge, ai, machinelearning
---

> PREPUBLICATION DRAFT. The 84 final responses have been collected and checked. Editorial feedback has been applied; the public Kaggle benchmark link is still pending. Do not publish with this banner or the link placeholder.

*For the [Kaggle Benchmarking Challenge](https://dev.to/challenges/kaggle-2026-09-23).*

## What I Benchmarked

Two models scored **26 out of 28** on my data-normalization benchmark. Looking at that number alone, you might think they failed in the same way.

They did not.

On the same monetary inputs, one model declined to choose even though the source convention was explicit. The other returned the right numerical magnitudes but omitted decimal places required by the output contract.

That difference is the main lesson of **Fechamento BR**: a leaderboard total can hide the distinction between a decision error and a representation error.

### Why this problem

I work with administrative spreadsheets. A blank field is not the same statement as zero. A code such as `00072` is not necessarily the number 72. And `4.700` cannot be interpreted correctly without knowing how its source uses punctuation.

I wanted to test a narrow question: **can a model normalize a field without changing its meaning, and decline to choose only when the supplied context actually leaves more than one valid interpretation?**

Every record in this benchmark is fictional. No workplace documents, patient information, employee records or customer files were used.

The final corpus contains **28 authored cases**, with seven cases in each of four families: monetary values, missing values, dates and identifiers. There are **12 contrast pairs plus four standalone controls**. A pair changes a relevant input or context while retaining a similar surface form; controls do not count as one-question pairs.

Examples include a year divisible by 400 versus a century year that is not; an explicit zero versus a missing field; and the same digit string treated as an identifier versus a quantity. The aim is not to make the model guess a hidden convention. The required interpretation rules are supplied.

### What earns a point

Each response must be a bare JSON object with exactly `status` and `value`. The four statuses are `ok`, `missing`, `ambiguous` and `invalid`. A non-`ok` status requires JSON null, not an invented replacement.

The primary point requires all three:

- the correct status;
- the exact canonical value required by the field contract;
- the requested JSON keys and types, without surrounding prose.

For money, the value must be a string with a decimal point and **exactly two decimal places**. For an identifier, meaningful zeros and inner characters must survive.

This is intentionally stricter than numerical equivalence. `"4700"` and `"4700.00"` represent the same magnitude, but only the latter meets the declared money-output contract. The secondary metric named `semantic_correct` in the code also requires the canonical string; it is not a measure of unrestricted semantic or numerical equivalence.

The grader is deterministic Python, not another model voting on an answer. I report individual correctness, JSON-contract compliance, fully correct pairs, controls and per-family counts separately.

## Models Tested

The final run evaluated the following exact Kaggle model identifiers:

| Model | Kaggle identifier |
|---|---|
| Gemini 3.8 Flash | `google/gemini-3.8-flash` |
| Claude Sonnet 4.6 | `anthropic/claude-sonnet-4-6@default` |
| Gemma 4 26B A4B | `google/gemma-4-26b-a4b` |

The models were selected before the final run, following an eight-case engineering pilot. An earlier Qwen pilot attempt encountered transport timeouts; its exclusion was operational, not a finding about its reasoning quality. The original pilot and interrupted attempts remain separate from the final results.

The final protocol used Kaggle Benchmarks SDK **0.6.1**, one attempt per case, two concurrent case workers and a 120-second HTTP timeout with client retries disabled. Each case had its own native child task and conversation. Gold labels, rationales and case IDs were not placed in the model prompt.

All three registered models reported temperature control unsupported. Accordingly, no temperature override was passed. A seed of zero was requested, but effective provider support was not established. This is a common recorded execution policy, **not a claim of identical sampling internals or deterministic responses across providers**.

The SDK's run cache was checked as disabled before execution. Provider-side prompt caching was not controlled and is not claimed to be disabled.

### Reproducibility before measurement

The corpus and gold labels were reviewed and frozen before final measurement. Software checks and a separate two-old-case integration test preceded the run; smoke responses are excluded. Final records were reconciled with native child-task traces. The reproducibility material retains the protocol, source hashes and verification details.

These checks detect accidental drift. They do not externally authenticate the author, the chronology or deliberately rewritten verification code.

## Findings

All three final model attempts completed, so the comparison has **84 responses with no missing cases**. I downloaded the evidence, recalculated the grades and matched the prompts and answers to the native Kaggle child-task traces.

| Model | Strictly correct | JSON-container compliance | Fully correct pairs | Controls |
|---|---:|---:|---:|---:|
| Gemini 3.8 Flash | **28/28** | 28/28 | 12/12 | 4/4 |
| Claude Sonnet 4.6 | **26/28** | 28/28 | 11/12 | 4/4 |
| Gemma 4 26B A4B | **26/28** | 28/28 | 11/12 | 4/4 |

All models answered the 21 cases outside the monetary family correctly. Within the seven money cases, Gemini answered seven correctly, while Claude and Gemma answered five correctly. Every discrepancy occurred in the same pair, **N01A/N01B**.

### One pair, two different failures

Both cases use the raw text `4.700`. N01A explicitly declares the Brazilian convention: dot for thousands and comma for decimals. N01B explicitly declares the US convention: comma for thousands and dot for decimals. The instructions require a money string with two decimal places, without rounding.

The resulting answers were:

| Case | Expected canonical value | Gemini | Claude | Gemma |
|---|---|---|---|---|
| N01A: declared pt-BR | `"4700.00"` | `ok`, `"4700.00"` | `ambiguous`, null | `ok`, `"4700"` |
| N01B: declared en-US | `"4.70"` | `ok`, `"4.70"` | `ambiguous`, null | `ok`, `"4.7"` |

Claude's two responses were valid JSON, but they classified determined inputs as ambiguous. Within this test, that is **unnecessary abstention**: the source already supplied the missing piece needed to choose.

Gemma's answers have the correct numerical magnitudes. Their failure is **canonical money representation**, not evidence that it selected the wrong locale or amount. Describing these as “two wrong amounts” would overstate what the outputs show.

Both models lose two strict points and one complete pair. Their totals and pair counts therefore tie, yet the interventions one might investigate next are different. One would test whether unnecessary abstention can be reduced; the other would test canonical output validation. This experiment did not evaluate either intervention, and I did not repair answers before scoring.

### What did not fail

The genuine-ambiguity cases were correctly handled by all three models. So were the missing-data, invalid-date and identifier cases in this corpus. The experiment does **not** show that these models routinely invent values or lose identifiers.

All 84 responses also met the JSON-container contract. The observed gap was not extra Markdown, missing keys or non-JSON text. Separating the container format from the field's canonical value made that distinction visible.

### Limits

This is one run on **28 constructed cases**, not a representative sample of all administrative work. Paired questions are related observations, and the status distribution is not balanced: 19 `ok`, three `missing`, two `ambiguous` and four `invalid`.

A perfect score here does not establish general reliability; a two-point gap does not establish general model superiority or statistical significance. The prompts explicitly teach a data contract. They test following that contract, not discovering every convention from an unlabeled spreadsheet.

These inputs follow explicit normalization rules, so a deterministic implementation is a plausible alternative. **I did not measure that baseline; this study does not establish that an LLM is necessary for the task.** A deterministic grader is not a measured normalization baseline.

No corpus or gold-label edits were made after the final outputs were seen. The strict score remains the predeclared score; the explanation of Gemma's numerical equivalence is a diagnostic reading of its two responses, not a replacement metric invented to change the ranking.

Next, I would test independently authored paraphrases and repeated runs before making a deployment recommendation. Those are future experiments, not claims supported by this submission.

## My Benchmark

**PENDING_PUBLIC_KAGGLE_BENCHMARK_LINK**

The required public Kaggle benchmark link must be inserted and checked without login before publication. A notebook draft, local evidence archive or screenshot is not a substitute. The benchmark and this article have not yet been published.

### Evidence and AI assistance

The reproducibility package contains the frozen cases and grader, protocol and source hashes, run manifests, original responses, native task traces and recomputed summaries. The scorer rejects records that do not match the frozen attempt, corpus and instrument manifest; incomplete runs receive no aggregate score.

ChatGPT assisted with implementation, analysis and writing. Codex provided a separate AI review of the corpus and instrument, with access to pilot results. **This was not a blind review or an independent human audit.** Matching saved records to native traces is a consistency check, not a second independent measurement. I remain responsible for the claims and materials.

The implementation uses the official [Kaggle Benchmarks SDK](https://github.com/Kaggle/kaggle-benchmarks) and its [quick start](https://github.com/Kaggle/kaggle-benchmarks/blob/ci/quick_start.md). Measurements used Kaggle's native model allowance, without personal paid API keys. Local fixed-response tests are kept distinct from model-performance evidence.

<!-- Final publication gate: insert the actual public benchmark link, reconcile wording with the evidence and complete the editorial review. No automated publication or bypass of the previously recorded tool restriction is authorized by this file. -->
