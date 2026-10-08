# Fechamento BR: preregistered targeted follow-up

**Completed on 8 October 2026.** This is a separate 12-case, 72-response experiment. It does not replace or expand the original 28-case / 84-response study, and it does not change the public Kaggle leaderboard.

## What we asked

The original study found two different strict failures on the same monetary pair: unnecessary abstention by Claude, and a numerically correct but noncanonical money string from Gemma. Would either category appear again on new values and rewritten source rules?

We authored four new explicit-convention contrast pairs and four controls, then publicly registered the cases and protocol in commit `6cf0c5824e9dac4871c9ea7827c9b0ab90c6c2e3` before any follow-up responses. The reviewed instrument and actual zero-model native preflight were published in commit `c86393a3a6b497b027b58a59aa4f82a3dd271d22` before the six measured attempts began. These public commits make the prospective plan inspectable; hashes and self-authored receipts are not third-party attestation.

The fixed plan was 12 cases × three original model IDs × two repetitions. All six attempts completed with no missing cases or native task errors. The run started at **2026-10-08 09:08:27 UTC** and finished at **09:20:28 UTC**. No follow-up cases, gold labels, primary grading rules or sampling schedule were changed after answers were seen.

## Results, not pooled with the original experiment

| Model | Repetition 1: strict | Repetition 2: strict | Explicit-convention targets: R1; R2 | Controls: R1; R2 |
| --- | ---: | ---: | ---: | ---: |
| Gemini 3.8 Flash | 12/12 | 12/12 | 8/8; 8/8 | 4/4; 4/4 |
| Claude Sonnet 4.6 | 7/12 | 6/12 | 3/8; 2/8 | 4/4; 4/4 |
| Gemma 4 26B A4B | 11/12 | 12/12 | 7/8; 8/8 | 4/4; 4/4 |

All **24 control responses** were correct. The controls covered genuinely unspecified locale, an ordinary decimal amount, a forbidden nonzero extra decimal digit, and an explicit zero. Every strict failure occurred among the explicit-convention targets.

Across its two repetitions, Claude had **seven unnecessary abstentions**, **three JSON-container violations**, and **one wrong numerical value**. In the three container violations, prose preceded a JSON object containing the expected answer; that is still a strict failure of the predeclared bare-JSON requirement. The categories are mutually exclusive under the prospective diagnostic order, and they do not replace the primary score.

Gemma had **one canonical-format-only failure in repetition 1** and none in repetition 2. Gemini had no strict failures in either repetition. These are descriptive counts of this constructed corpus, not estimates of population reliability.

## Concrete examples

**C04B, raw `3.600`, declared decimal point, expected `"3.60"`:** in repetition 1 Claude returned `{"status": "ambiguous", "value": null}`, while Gemma returned `{"status": "ok", "value": "3.6"}`. The same distinction observed in the original study therefore occurred on a new value and rewritten context. In repetition 2, Claude again abstained, but Gemma returned the exact expected string. The canonical-format failure was observed again; it was not stable across both repetitions.

**C01A, raw `7.300`, declared thousands point, expected `"7300.00"`:** Claude returned `{"status": "ok", "value": "7.30"}` in repetition 2. Unlike Gemma's missing trailing zero, this changes the numerical amount. We do not count it as mere formatting.

**C03A, raw `12.500`, declared thousands point:** Claude included the correct `"12500.00"` JSON answer in both repetitions, but prefaced it with explanatory prose. The original 84 outputs all satisfied the JSON-container requirement; the new outputs show why that observation should not be generalized beyond its original batch.

## What changed our conclusion

The original distinction survived a targeted follow-up: unnecessary abstention and canonical-format errors appeared again. But the follow-up also exposed a broader set of failures and a between-repetition change. The defensible lesson is to inspect **decision, magnitude, canonical representation and the JSON container separately**, rather than treating every lost strict point as the same kind of mistake.

These observations suggest different checks worth investigating; this experiment did not test repair strategies, deployment safeguards, or a rule-based normalization baseline. It does not establish that an LLM is necessary for this task.

## Verification and reproducibility

Every raw answer was regraded by the unchanged original strict scorer. All 72 prompts, answers and recorded model identities were reconciled against six native parent runs and 72 distinct native conversations. The verifier also checks the complete trace tree for extra requests, with identical duplicate references deduplicated rather than double-counted.

The original 84 responses remain byte-for-byte unchanged. Native metrics record **US$0.1470522 of included Kaggle model quota** for this follow-up; that is quota accounting, not a personal API payment. Measurements used the native Kaggle proxy, with no personal paid API fallback.

The public native extracts retain every conversation/request and all fields required by the verifier, while omitting duplicated task definitions and unused platform metadata. Original full exports are preserved privately. The extraction receipt records hashes of the full source traces and the public extracts; the public extracts are not claimed to be byte-identical full exports.

From the repository root, with Python 3.10 or newer:

```text
python confirmation_v1/reproduce.py --test
```

This checks the unchanged original study, rebuilds the frozen SAFE notebook, runs the 25 offline fixture tests, and verifies the separate measured follow-up when its evidence directory is present. No accounts, packages, network access or model calls are required. Fixture responses are software tests, not performance measurements.

## Limits

This corpus was designed after seeing the original results. The separate Codex reviewer saw the gold labels and original findings; this is neither a blind holdout nor a human audit. Values and wording changed together, so changed outcomes cannot identify a causal wording effect. Paired cases are related, and two repetitions are not independent population samples or evidence of statistical significance. SDK run caching was disabled; provider-side caching and effective seed support were not controlled. The platform model IDs identify the recorded routes, not an externally authenticated model build. Neither a perfect score nor the gaps above establish general model superiority.
