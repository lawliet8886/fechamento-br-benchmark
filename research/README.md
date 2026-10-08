# Fechamento BR — offline reproducibility kit

This directory contains the final 28-case corpus, frozen grading/instrument code, the 84 original prompts and answers, run manifests, summaries, a safe notebook and the revised article draft.

## Verify without spending anything

Use Python 3.10 or newer, then run from this folder:

```text
python verify_results.py
```

No package installation, account, network, SDK import or model call is required by this verification command. Expected strict results: Gemini 28/28; Claude 26/28; Gemma 26/28. This is a consistency check and regrade of saved outputs, not new independent measurements.

The safe notebook keeps its execution and approval switches disabled. Future native Kaggle measurements need an explicitly reviewed environment and free quota; do not enable gates merely to view results. The current study is already measured. Reruns are not necessary to read this package.

## What is not included

No account credentials, private desktop history, failed-attempt logs or personal documents are included. The original full native task traces remain preserved in the private project, and were reconciled against the saved record files. This public-oriented kit does not include HTTP/session metadata from those traces. FILE_HASHES.json detects accidental byte changes; it is not an externally signed attestation.

ARTICLE_DRAFT.md is not ready to publish until a genuine public Kaggle benchmark URL replaces its placeholder. This kit and a local notebook do not substitute for the contest's required benchmark link. No publication was performed by this packaging step.

One run, 28 authored cases, explicit rules and no measured rule-based baseline: do not interpret the score as general model reliability. The strict grader intentionally distinguishes canonical strings from merely equal numerical magnitudes. A separate AI review by Codex is not an independent human audit.
