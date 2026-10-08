# Targeted confirmation — frozen before model measurement

This is a separate follow-up to the original 28-case / 84-response study in `research/`. It contains 12 new fictional monetary cases: four explicit-convention contrast pairs and four controls, with two predeclared repetitions using the original three models (at most 72 requests).

The corpus and protocol were publicly registered in commit `6cf0c5824e9dac4871c9ea7827c9b0ab90c6c2e3`, before any supplementary model outputs. Their pre-review metadata is preserved unchanged; subsequent approval and the exact source bundle are recorded in `FREEZE_RECEIPT.json` and `NATIVE_PREFLIGHT_RECEIPT.json`.

At this source-freeze commit, the revised implementation has passed the separate Codex AI review and the actual Kaggle zero-model preflight: SDK 0.6.1, run cache disabled, seven executed source cells checked, decorators registered, and no model calls. **No supplementary model responses have yet been collected.**

The follow-up was designed after seeing the original results. Values and wording change together; a different outcome cannot identify its cause. The reviewers saw the original study and the labels: this is not a blind, human, or independent-sample audit. The strict score, cases and schedule will not be changed after seeing outputs.

## Reproduce offline, without accounts, packages or API calls

From the repository root, using Python 3.10 or newer:

```text
python confirmation_v1/reproduce.py --test
```

This rebuilds the self-contained SAFE notebook identically, regrades the 84 original records and runs 25 isolated fixture tests. When the separate measured evidence directory is present, it also regrades and reconciles that evidence. The wrapper recreates the historical development layout in a temporary folder; the frozen builder does not need edits. Fixture responses are software tests, not measured model performance.

The SAFE notebook has all model-execution gates disabled. Never enable them merely to inspect evidence. Native model reruns require a reviewed environment and included quota; no personal paid API or fallback is allowed.

The original public task, leaderboard, data, grader and 84 saved responses remain unchanged.
