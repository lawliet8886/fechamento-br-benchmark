# Targeted confirmation — protocol published before model measurement

This directory is a separate, prospective follow-up to the original frozen 84-response study in `research/`. The new corpus contains 12 fictional monetary cases: four explicit-convention contrast pairs and four controls. The plan is two repetitions with the original three models, at most 72 new responses.

**At the time of this commit, no supplementary model responses had been collected.** The corpus and all 12 gold answers were checked by a separate Codex AI reviewer, who saw the labels and the original study. This is not a blind review, independent human audit, or randomly sampled holdout. The supplementary implementation is undergoing review and native preflight before any inference.

The cases and protocol were authored after inspecting the original results. Values and wording change together; a change in outcomes cannot identify its cause. Successful and unsuccessful outcomes will both be reported. The strict scoring rule will not be changed after seeing answers.

The original published task, leaderboard, corpus, grader and 84 saved responses are unchanged. There are no supplementary performance results in this commit.
