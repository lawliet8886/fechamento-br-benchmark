# Fechamento BR — Same Score, Different Failure

Tests normalization of fictional administrative fields under explicit source conventions. 28 authored cases: 12 contrast pairs and four standalone controls across money, missing values, dates and identifiers. All prompts are in Portuguese. One strict point requires the correct decision, exact canonical value and bare JSON format.

One frozen run: Gemini 3.8 Flash 28/28; Claude Sonnet 4.6 and Gemma 4 26B A4B 26/28. The four strict failures occur in one pair: Claude unnecessarily abstains despite explicit conventions; Gemma returns numerically equivalent amounts without required decimal zeros. All 84 outputs meet the JSON-container format.

This is a small, authored, single-run test of a supplied contract. It does not establish general model superiority, statistical significance, deployment suitability or necessity of an LLM. A rule-based normalization baseline was not measured. Provider sampling differences are recorded, not assumed identical. No real workplace or personal data.

Status: measured and locally verified; public Task/Benchmark publication still pending. Do not describe this file itself as a submitted benchmark.
