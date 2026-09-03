# FMP trust-calibration — synthetic pilot dataset

Supporting data for [`case-studies/fmp-trust-calibration.html`](../../case-studies/fmp-trust-calibration.html), the Final Major Project on trust calibration in human-AI financial decision systems.

This is **synthetic** data generated to pilot the analysis pipeline ahead of the live study — not real participant responses. It's deliberately built to look and behave like a messy real export (uneven group sizes, dropout, missing cells, a couple of inattentive respondents, realistic timestamps) rather than a clean textbook grid — see [Realism](#realism) below.

## Files

- `generate_dataset.py` — stdlib-only Python script that generates the dataset from a fixed seed (reproducible, no dependencies).
- `trust_calibration_synthetic.csv` — the generated long-form dataset.
- `run_models.py` — analysis pipeline (needs `numpy`, `pandas`, `scipy`, `statsmodels`): one-way ANOVA + Tukey-Kramer, a Bradley-Terry pairwise model, a logistic regression, and a mixed-effects model. See [Analysis](#analysis) below.
- `model_results.txt` — saved output of the last `run_models.py` run.
- **`REAL_DATA_SCHEMA.md`** — exactly what a real study export needs to contain for `run_models.py` to run on it unmodified once the live data exists, and `real_data_template.csv` — a blank file with just the required headers.

Regenerate with:

```
python3 generate_dataset.py
```

## Shape

- **350 respondents**, each rating up to **10 fictional loan scenarios** in a randomized per-respondent order → **3,430 observations** (long-form, one row per respondent × completed scenario — not a clean 3,500, because of dropout; see [Realism](#realism)).
- Condition assignment is simple random (not balanced), so cell sizes come out uneven: `counterfactual` 132 respondents, `none` 120, `surface` 98 (current seed).

## Columns

| Column | Description |
|---|---|
| `respondent_id` | Panel-style respondent token (e.g. `P511e7ea419`) |
| `age`, `gender`, `financial_literacy` | Respondent demographics (`financial_literacy` self-report, 1–5) — occasionally blank, see below |
| `need_for_cognition`, `tech_disposition` | Individual-difference covariates, 1–7 composite self-report scales — occasionally blank |
| `condition` | Explanation condition: `none`, `surface`, `counterfactual` |
| `scenario_id` | Fictional loan scenario (1–10, fixed bank shared by all respondents) |
| `presentation_position` | Trial order (1st, 2nd, ...) the respondent actually saw this scenario in — order is randomized per respondent, not fixed to `scenario_id` |
| `loan_amount`, `applicant_credit_score` | Scenario attributes |
| `ai_recommendation`, `ai_confidence` | The AI's recommendation (`approve`/`deny`) and stated confidence (0–100) |
| `ai_correct` | Pilot ground truth: whether the AI's recommendation was the "right" call for that scenario |
| `t1`–`t12` | Jian et al. (2000) Trust in Automation scale items, 1–7 Likert — individual cells occasionally blank |
| `participant_decision` | The simulated respondent's raw decision (`approve`/`deny`) — the field a real export would carry |
| `trust_composite`, `agree_with_ai`, `calibration_label` | Convenience columns derived from the raw fields above. `run_models.py` doesn't trust them — it recomputes `trust_composite` from `t1`–`t12` and `agree_with_ai` from `participant_decision` itself, exactly as it would for a real export (see `REAL_DATA_SCHEMA.md`) |
| `response_time_sec` | Response time, with genuine speeder/straggler outliers, not just symmetric noise |
| `response_timestamp` | When that scenario was completed — increases monotonically within a respondent's session |
| `attention_check_passed` | `False` for the small fraction of respondents who straightlined (answered every item identically) — flagged, not removed, same as a real dataset would keep them for the analyst to decide on |

## Design notes

Trust is simulated as a function of the AI's stated confidence, how strongly the scenario's actual correctness pulls trust in the right direction (weakest under `none`, strongest under `counterfactual` — the effect the live study is designed to test for real, deliberately kept modest rather than dominant), a stable per-respondent trust baseline applied across all of that person's scenarios (the reason a respondent's rows are correlated, not independent — and the signal the mixed-effects model's random intercept should recover), and per-observation noise that's larger for ambiguous scenarios (AI confidence near 50) than clear-cut ones. Individual-difference traits shift reliance on the AI independently of momentary trust: `tech_disposition` (+), `need_for_cognition` (–), `financial_literacy` (–). Between-respondent variance intentionally dominates the condition effect — real people vary far more than a single manipulation moves them. Run `generate_dataset.py` to print a count summary (respondents, observations, attrition, missingness) alongside the CSV.

## Realism

At n = 350 this isn't just resized — it's built with the messiness a real platform export actually has:

- **Uneven condition cells** — simple random assignment, not a balanced cycle, so group sizes differ (132/120/98 on the current seed).
- **Randomized presentation order** — `scenario_id` isn't shown in a fixed 1–10 order; `presentation_position` records what each respondent actually saw first, second, etc.
- **Early dropout** — ~5% of respondents quit partway through (`generate_dataset.py` picks a random stopping point between 3 and 8 scenarios); their remaining rows simply don't exist, they aren't padded or imputed. This is why observations ≠ respondents × 10.
- **Item-level missingness** — ~1.2% of individual trust-scale cells are blank, and ~3% of any given demographic field is blank per respondent, both handled by row-wise/available-item means rather than needing a separate imputation step.
- **Attention-check failures** — a couple of percent of respondents straightline (every item identical); flagged via `attention_check_passed` rather than silently dropped, the way a real dataset hands the exclusion decision to the analyst.
- **Realistic timestamps** — each respondent starts within a 6-week collection window, skewed toward weekdays and daytime/evening hours, and `response_timestamp` advances by each row's actual `response_time_sec` within a session.
- **Non-uniform response times** — most responses cluster around a plausible reading/deciding time, but a few respondents are flagged as speeders (rushing every item) or straggle badly on individual items, rather than one tidy symmetric distribution.

## Analysis

`run_models.py` runs four models against the pipeline the live study will use:

1. **One-way ANOVA + Tukey-Kramer** — on respondent-level means (trust, agreement rate, decision accuracy, response time) across the three conditions, with pairwise post-hoc tests where the omnibus test is significant.
2. **Bradley-Terry model** — for each scenario, runs individual duels: a random respondent from condition A vs. one from condition B on that scenario, decided by each person's *actual* decision outcome (not the group mean), ties split 0.5/0.5. Fits pairwise "win" strengths (MM/Zermelo algorithm) and head-to-head win probabilities from those duels.
3. **Logistic regression** — predicts "high AI follower" (agreement rate above the sample median) from `financial_literacy`, `need_for_cognition`, `tech_disposition`, and condition.
4. **Mixed-effects model** — `trust_composite ~ condition` with a random intercept per `respondent_id`, since each respondent contributes multiple non-independent observations (group sizes vary 3–10 because of dropout); reports the intraclass correlation (ICC).

Headline results from the current seed (see `model_results.txt` for full output):

- At n = 350 the omnibus ANOVAs are underpowered — none of the four outcome measures reach significance (trust p = .12, agreement rate p = .48, decision accuracy p = .17, response time p = .08), so no Tukey-Kramer post-hoc is run. That's an honest consequence of the smaller, uneven-celled sample, not a bug: a real pilot this size often can't detect effects a full-powered study would.
- The Bradley-Terry duels put all three conditions close together (strengths ≈ .32–.35 of 1), with `counterfactual` beating the other two about 52% of the time head-to-head — a small edge, not a rout.
- The logistic regression still finds condition non-significant (p = .38–.67), but the individual-difference predictors come through clearly on n = 316 (34 respondents dropped for missing demographic fields) — `tech_disposition` (OR ≈ 1.34, p = .004), `need_for_cognition` (OR ≈ 0.67, p < .001), and `financial_literacy` (OR ≈ 0.70, p = .004) all predict being a high AI follower.
- The mixed-effects model's random intercept has ICC ≈ 0.45 — about 45% of the variance in trust sits at the respondent level (group sizes range 3–10 due to dropout), still justifying the clustered model over a naive OLS/ANOVA across all rows. `counterfactual` remains a significant fixed effect (p = .043) even though the plain ANOVA on the same outcome wasn't — the random intercept soaks up between-person noise that the ANOVA couldn't separate out.

Run it with:

```
pip install numpy pandas scipy statsmodels
python3 run_models.py                      # synthetic pilot data (default)
python3 run_models.py path/to/real_export.csv   # real data, once it exists
```

The script doesn't hardcode the synthetic file's specifics — condition labels, item count, and which optional predictors exist are all read from whatever CSV you point it at. See `REAL_DATA_SCHEMA.md` for exactly what columns a real export needs.
