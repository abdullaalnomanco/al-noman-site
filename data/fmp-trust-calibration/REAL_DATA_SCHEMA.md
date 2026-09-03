# Real-export schema

What your actual study export needs to contain for `run_models.py` to run on it
unmodified — no renaming, no reshaping, no code changes:

```
python3 run_models.py path/to/real_export.csv
```

## Required columns (long-form: one row per respondent × scenario)

| Column | Notes |
|---|---|
| `respondent_id` | Any unique identifier per participant. |
| `condition` | Any labels for your explanation arms — not required to be `none`/`surface`/`counterfactual`. Whatever string you use for the no-explanation arm, set it as `PREFERRED_BASELINE_CONDITION` at the top of `run_models.py` so it's the regression reference level; otherwise the alphabetically-first label is used. |
| `scenario_id` | 1–10 (or however many scenarios your instrument used). |
| `ai_recommendation` | The AI's verdict shown to the participant, e.g. `approve`/`deny`. |
| `ai_correct` | Ground truth: was that verdict actually right for this scenario? `True`/`False` (or `1`/`0`, `yes`/`no`). |
| `participant_decision` | The participant's own raw decision on the scenario, in the same vocabulary as `ai_recommendation` (e.g. `approve`/`deny`). Agreement and decision accuracy are **derived** from this by comparing it to `ai_recommendation` and `ai_correct` — don't pre-compute and submit an `agree_with_ai` flag; submit the actual decision so it's checkable. |
| `t1`, `t2`, ... `tN` | **Each item of your trust scale, raw** — not a pre-averaged composite. `run_models.py` detects every column matching `t\d+`, uses all of them, and recomputes `trust_composite` as their mean itself. If your form only used a single trust rating, that's `t1` and nothing else. Do not submit only a composite trust score with no items behind it — there's no way to check that number without the items it came from. |

## Optional columns

| Column | Used by |
|---|---|
| `response_time_sec` | ANOVA outcome #4. Skipped (with a note) if absent. |
| `financial_literacy`, `need_for_cognition`, `tech_disposition` | Predictors in the logistic regression. Any subset you have is used; missing ones are dropped from the model (with a note) rather than failing. One row per respondent — `run_models.py` takes the first value it sees per `respondent_id`. |

Any other columns (loan amount, credit score, demographics, free text, whatever your form collected) are simply ignored — no need to strip them out before handing over the export.

## Why it's built this way

Nothing about condition labels, item counts, or which optional predictors exist is hardcoded — `run_models.py` inspects the file's own columns at load time and adapts (see the "Note:" lines it prints when something optional is missing). The two things it deliberately refuses to take pre-computed are agreement/accuracy (always derived from `participant_decision`) and `trust_composite` (always recomputed from the raw `t1..tN` items), because those are exactly the numbers a checkable pipeline shouldn't take on faith.

`trust_calibration_synthetic.csv` is generated to this same schema (see `generate_dataset.py`), which is why it's a legitimate stand-in for pilot-testing the pipeline rather than a special case that happens to work.
