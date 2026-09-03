# FMP trust-calibration — synthetic pilot dataset

Supporting data for [`case-studies/fmp-trust-calibration.html`](../../case-studies/fmp-trust-calibration.html), the Final Major Project on trust calibration in human-AI financial decision systems.

This is **synthetic** data generated to pilot the analysis pipeline ahead of the live study — not real participant responses.

## Files

- `generate_dataset.py` — stdlib-only Python script that generates the dataset from a fixed seed (reproducible, no dependencies).
- `trust_calibration_synthetic.csv` — the generated long-form dataset.
- `run_models.py` — analysis pipeline (needs `numpy`, `pandas`, `scipy`, `statsmodels`): one-way ANOVA + Tukey-Kramer, a Bradley-Terry pairwise model, a logistic regression, and a mixed-effects model. See [Analysis](#analysis) below.
- `model_results.txt` — saved output of the last `run_models.py` run.

Regenerate with:

```
python3 generate_dataset.py
```

## Shape

- **678 respondents**, each rating the same **10 fictional loan scenarios** → **6,780 observations** (long-form, one row per respondent × scenario).
- Respondents are split as evenly as possible across three between-subjects explanation conditions: `none`, `surface`, `counterfactual` (226 respondents / 2,260 observations each).

## Columns

| Column | Description |
|---|---|
| `respondent_id` | Respondent identifier (R001–R678) |
| `age`, `gender`, `financial_literacy` | Respondent demographics (`financial_literacy` self-report, 1–5) |
| `need_for_cognition`, `tech_disposition` | Individual-difference covariates, 1–7 composite self-report scales |
| `condition` | Explanation condition: `none`, `surface`, `counterfactual` |
| `scenario_id` | Fictional loan scenario (1–10, fixed bank shared by all respondents) |
| `loan_amount`, `applicant_credit_score` | Scenario attributes |
| `ai_recommendation`, `ai_confidence` | The AI's recommendation (`approve`/`deny`) and stated confidence (0–100) |
| `ai_correct` | Pilot ground truth: whether the AI's recommendation was the "right" call for that scenario |
| `t1`–`t12` | Jian et al. (2000) Trust in Automation scale items, 1–7 Likert |
| `trust_composite` | Mean of `t1`–`t12` |
| `agree_with_ai` | Whether the simulated respondent went along with the AI's recommendation |
| `response_time_sec` | Simulated response time |
| `calibration_label` | Derived: `calibrated` / `over-trust` / `under-trust`, from `trust_composite` vs. `ai_correct` |

## Design notes

Trust is simulated as a function of the AI's stated confidence, how strongly the scenario's actual correctness pulls trust in the right direction (weakest under `none`, strongest under `counterfactual` — the effect the live study is designed to test for real, deliberately kept modest rather than dominant), a stable per-respondent trust baseline applied across all 10 of that person's scenarios (the reason the 10 rows per respondent are correlated, not independent — and the signal the mixed-effects model's random intercept should recover), and per-observation noise that's larger for ambiguous scenarios (AI confidence near 50) than clear-cut ones. Individual-difference traits shift reliance on the AI independently of momentary trust: `tech_disposition` (+), `need_for_cognition` (–), `financial_literacy` (–). Between-respondent variance intentionally dominates the condition effect — real people vary far more than a single manipulation moves them — so the numbers below read like noisy human data rather than a plan executing cleanly. Run `generate_dataset.py` to print a count summary (respondents, observations, per-condition and per-label breakdowns) alongside the CSV.

## Analysis

`run_models.py` runs four models against the pipeline the live study will use:

1. **One-way ANOVA + Tukey-Kramer** — on respondent-level means (trust, agreement rate, decision accuracy, response time) across the three conditions, with pairwise post-hoc tests where the omnibus test is significant.
2. **Bradley-Terry model** — for each scenario, runs individual duels: a random respondent from condition A vs. one from condition B on that scenario, decided by each person's *actual* decision outcome (not the group mean), ties split 0.5/0.5. Fits pairwise "win" strengths (MM/Zermelo algorithm) and head-to-head win probabilities from those duels.
3. **Logistic regression** — predicts "high AI follower" (agreement rate above the sample median) from `financial_literacy`, `need_for_cognition`, `tech_disposition`, and condition.
4. **Mixed-effects model** — `trust_composite ~ condition` with a random intercept per `respondent_id`, since each respondent contributes 10 non-independent observations; reports the intraclass correlation (ICC).

Headline results from the current seed (see `model_results.txt` for full output):

- Trust (p = .016) and decision accuracy (p < .001) differ across conditions, but not every pairwise contrast does — `none` vs `surface` is never significant, and agreement rate alone doesn't reach significance (p = .072). That patchiness is expected: a real manipulation nudges some measures more than others.
- The Bradley-Terry duels put the three conditions close together (strengths ≈ .32–.36 of 1), with `counterfactual` beating `none` about 53% of the time head-to-head — a real edge, not a rout. A "weaker" condition still wins plenty of individual duels, because individual variability swamps the condition effect at the person level.
- In the logistic regression, condition itself drops out as non-significant (p = .18–.75) once individual differences are in the model — `tech_disposition` (OR ≈ 1.42, p < .001), `need_for_cognition` (OR ≈ 0.78, p = .001), and `financial_literacy` (OR ≈ 0.85, p = .045) are what actually predict being a high AI follower.
- The mixed-effects model's random intercept has ICC ≈ 0.42 — about 42% of the variance in trust sits at the respondent level, confirming the 10 observations per respondent aren't independent and justifying the clustered model over a naive OLS/ANOVA on all 6,780 rows.

Run it with:

```
pip install numpy pandas scipy statsmodels
python3 run_models.py
```
