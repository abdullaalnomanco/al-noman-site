# FMP trust-calibration — synthetic pilot dataset

Supporting data for [`case-studies/fmp-trust-calibration.html`](../../case-studies/fmp-trust-calibration.html), the Final Major Project on trust calibration in human-AI financial decision systems.

This is **synthetic** data generated to pilot the analysis pipeline ahead of the live study — not real participant responses.

## Files

- `generate_dataset.py` — stdlib-only Python script that generates the dataset from a fixed seed (reproducible, no dependencies).
- `trust_calibration_synthetic.csv` — the generated long-form dataset.

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

Trust is simulated as a function of the AI's stated confidence plus how strongly the scenario's actual correctness pulls trust in the right direction — that pull is weakest under `none` and strongest under `counterfactual`, which is the effect the live study is designed to test for real. Run `generate_dataset.py` to print a count summary (respondents, observations, per-condition and per-label breakdowns) alongside the CSV.
