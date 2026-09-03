#!/usr/bin/env python3
"""
Analysis pipeline for the FMP trust-calibration synthetic dataset.

Runs the four models used to pilot the analysis approach ahead of the
live study:

  1. One-way ANOVA (+ Tukey-Kramer post-hoc) on each outcome measure,
     across the three explanation conditions.
  2. Bradley-Terry pairwise-comparison model — which condition "wins"
     head-to-head on decision accuracy, per scenario.
  3. Logistic regression predicting "high AI follower" status from
     financial literacy, need for cognition, and tech disposition.
  4. Mixed-effects model on trust, with a random intercept per
     respondent (since each respondent contributes 10 non-independent
     observations).

Usage:
    python3 run_models.py [path/to/real_export.csv]

Defaults to the synthetic pilot file, but takes any CSV built to the
schema documented in REAL_DATA_SCHEMA.md — real study data plugs in
with no code changes. Everything the models need is *re-derived* here
from raw fields rather than trusted as pre-computed:
  - agreement/accuracy come from comparing participant_decision to
    ai_recommendation and ai_correct, not from a precomputed flag.
  - trust_composite is the mean of whatever t1..tN item columns are
    present, not taken as a given pre-averaged number.
  - condition categories and the reference level are inferred from the
    data itself, not hardcoded to the synthetic label set.

Requires numpy / pandas / scipy / statsmodels.
"""
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd

DATA_PATH = "trust_calibration_synthetic.csv"
TRUST_ITEM_PATTERN = re.compile(r"^t\d+$")
# Preferred reference/baseline level for the condition factor, if present
# in the data (e.g. the "no explanation" arm). Falls back to whichever
# condition sorts first when this isn't found.
PREFERRED_BASELINE_CONDITION = "none"


def _to_bool(series):
    if series.dtype == bool:
        return series
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "t"})


def load_data(path=DATA_PATH):
    df = pd.read_csv(path)

    trust_items = sorted(
        (c for c in df.columns if TRUST_ITEM_PATTERN.match(c)),
        key=lambda c: int(c[1:]),
    )
    if not trust_items:
        raise ValueError(
            "No raw trust item columns found (expected t1, t2, ... — one per scale "
            "item). A pre-averaged composite alone isn't enough to check the number."
        )
    # Always recompute from the raw items, even if a trust_composite column
    # is already present, so the figure is checkable rather than assumed.
    df["trust_composite"] = df[trust_items].mean(axis=1).round(2)

    df["ai_correct"] = _to_bool(df["ai_correct"])

    if "participant_decision" in df.columns:
        df["agree_with_ai"] = df["participant_decision"].astype(str).str.strip().str.lower() == \
            df["ai_recommendation"].astype(str).str.strip().str.lower()
    elif "agree_with_ai" in df.columns:
        df["agree_with_ai"] = _to_bool(df["agree_with_ai"])
    else:
        raise ValueError("Need either a participant_decision column or a precomputed agree_with_ai column.")

    conditions = sorted(df["condition"].dropna().unique().tolist())
    if PREFERRED_BASELINE_CONDITION in conditions:
        conditions.remove(PREFERRED_BASELINE_CONDITION)
        conditions.insert(0, PREFERRED_BASELINE_CONDITION)
    df["condition"] = pd.Categorical(df["condition"], categories=conditions)

    # "Good decision": followed the AI when it was right, didn't when it was wrong.
    df["decision_correct"] = df["agree_with_ai"] == df["ai_correct"]
    return df, conditions, trust_items


# ---------------------------------------------------------------------
# 1. One-way ANOVA + Tukey-Kramer
# ---------------------------------------------------------------------
def run_anova(df, conditions):
    print("\n" + "=" * 72)
    print("1. ONE-WAY ANOVA + TUKEY-KRAMER POST-HOC")
    print("=" * 72)

    agg = {
        "trust_mean": ("trust_composite", "mean"),
        "agree_rate": ("agree_with_ai", "mean"),
        "accuracy": ("decision_correct", "mean"),
    }
    outcomes = {
        "trust_mean": "Mean trust composite (1-7)",
        "agree_rate": "Rate of agreeing with the AI",
        "accuracy": "Decision accuracy (agreed iff AI correct)",
    }
    if "response_time_sec" in df.columns:
        agg["rt_mean"] = ("response_time_sec", "mean")
        outcomes["rt_mean"] = "Mean response time (s)"
    else:
        print("Note: response_time_sec not in this export — skipping that outcome.")

    per_resp = df.groupby(["respondent_id", "condition"], observed=True).agg(**agg).reset_index()
    k = len(conditions)

    for col, label in outcomes.items():
        groups = [per_resp.loc[per_resp["condition"] == c, col].values for c in conditions]
        f_stat, p_val = stats.f_oneway(*groups)
        means = {c: g.mean() for c, g in zip(conditions, groups)}
        print(f"\n-- {label} --")
        print("   means: " + "  ".join(f"{c}={means[c]:.3f}" for c in conditions))
        print(f"   F({k - 1}, {len(per_resp) - k}) = {f_stat:.3f}, p = {p_val:.4g}")
        if p_val < 0.05:
            tukey = pairwise_tukeyhsd(per_resp[col], per_resp["condition"], alpha=0.05)
            print("   Tukey-Kramer post-hoc:")
            for line in str(tukey).splitlines():
                print(f"     {line}")
        else:
            print("   (not significant at alpha=.05 -> no post-hoc run)")

    return per_resp


# ---------------------------------------------------------------------
# 2. Bradley-Terry pairwise-comparison model
# ---------------------------------------------------------------------
def fit_bradley_terry(win_counts, items, n_iter=500, tol=1e-10):
    """Minorization-Maximization (Zermelo/Hunter 2004) fit.

    win_counts[(i, j)] = number of times i beat j.
    Returns strength parameters (sum to 1) and derived win probabilities.
    """
    strength = {item: 1.0 for item in items}
    for _ in range(n_iter):
        new_strength = {}
        max_delta = 0.0
        for i in items:
            numerator = sum(win_counts.get((i, j), 0) for j in items if j != i)
            denom = 0.0
            for j in items:
                if j == i:
                    continue
                n_ij = win_counts.get((i, j), 0) + win_counts.get((j, i), 0)
                if n_ij:
                    denom += n_ij / (strength[i] + strength[j])
            new_strength[i] = numerator / denom if denom > 0 else strength[i]
            max_delta = max(max_delta, abs(new_strength[i] - strength[i]))
        total = sum(new_strength.values())
        strength = {k: v / total for k, v in new_strength.items()}
        if max_delta < tol:
            break
    return strength


def run_bradley_terry(df, conditions, seed=2026):
    print("\n" + "=" * 72)
    print("2. BRADLEY-TERRY PAIRWISE-COMPARISON MODEL")
    print("=" * 72)
    print("Contest = one individual duel: a random respondent from condition A vs. a")
    print("random respondent from condition B, on the same scenario. Whoever made the")
    print("correct decision on that scenario wins the duel; both-correct/both-wrong")
    print("ties split 0.5/0.5. This uses each person's actual outcome, not the group")
    print("mean, so a 'weaker' condition still wins plenty of individual duels.")

    rng = np.random.default_rng(seed)
    pairs = [(a, b) for i, a in enumerate(conditions) for b in conditions[i + 1:]]

    win_counts = {}
    per_scenario_summary = []
    for scenario_id, scen_df in df.groupby("scenario_id"):
        by_cond = {
            c: scen_df.loc[scen_df["condition"] == c, "decision_correct"].to_numpy()
            for c in conditions
        }
        per_scenario_summary.append(
            f"  scenario {scenario_id}: " + ", ".join(f"{c}={by_cond[c].mean():.3f}" for c in conditions)
        )
        for a, b in pairs:
            arr_a, arr_b = by_cond[a].copy(), by_cond[b].copy()
            rng.shuffle(arr_a)
            rng.shuffle(arr_b)
            n = min(len(arr_a), len(arr_b))
            a_win = np.sum(arr_a[:n] & ~arr_b[:n])
            b_win = np.sum(arr_b[:n] & ~arr_a[:n])
            tie = n - a_win - b_win
            win_counts[(a, b)] = win_counts.get((a, b), 0) + a_win + 0.5 * tie
            win_counts[(b, a)] = win_counts.get((b, a), 0) + b_win + 0.5 * tie

    print("\nPer-scenario decision accuracy by condition (for reference):")
    print("\n".join(per_scenario_summary))

    strength = fit_bradley_terry(win_counts, conditions)
    print("\nFitted Bradley-Terry strengths (sum to 1, higher = wins more often):")
    for c in sorted(strength, key=strength.get, reverse=True):
        print(f"  {c:16s} strength = {strength[c]:.4f}")

    print("\nImplied head-to-head win probabilities P(row beats column):")
    header = "                " + "".join(f"{c:>16s}" for c in conditions)
    print(header)
    for a in conditions:
        cells = []
        for b in conditions:
            if a == b:
                cells.append(f"{'--':>16s}")
            else:
                p = strength[a] / (strength[a] + strength[b])
                cells.append(f"{p:16.3f}")
        print(f"{a:16s}" + "".join(cells))

    return strength


# ---------------------------------------------------------------------
# 3. Logistic regression: "high AI follower"
# ---------------------------------------------------------------------
INDIVIDUAL_DIFFERENCE_COLUMNS = ["financial_literacy", "need_for_cognition", "tech_disposition"]


def run_logistic(df):
    print("\n" + "=" * 72)
    print("3. LOGISTIC REGRESSION — 'HIGH AI FOLLOWER'")
    print("=" * 72)

    predictors = [c for c in INDIVIDUAL_DIFFERENCE_COLUMNS if c in df.columns]
    missing = [c for c in INDIVIDUAL_DIFFERENCE_COLUMNS if c not in df.columns]
    if missing:
        print(f"Note: {', '.join(missing)} not in this export — dropped from the model, "
              f"kept: {', '.join(predictors) or '(none)'}.")

    agg = {"agree_rate": ("agree_with_ai", "mean"), "condition": ("condition", "first")}
    agg.update({c: (c, "first") for c in predictors})
    per_resp = df.groupby("respondent_id", observed=True).agg(**agg).reset_index()

    median_rate = per_resp["agree_rate"].median()
    per_resp["high_ai_follower"] = (per_resp["agree_rate"] > median_rate).astype(int)
    print(f"Median agreement rate = {median_rate:.3f} (split point for the binary DV)")
    print(f"high_ai_follower = 1 for {per_resp['high_ai_follower'].sum()} / {len(per_resp)} respondents")

    formula = "high_ai_follower ~ " + " + ".join(predictors + ["C(condition)"])
    model = smf.logit(formula, data=per_resp).fit(disp=False)

    print("\n" + str(model.summary()))

    print("\nOdds ratios (exp(coef)) with 95% CI:")
    conf = model.conf_int()
    conf["OR"] = model.params
    conf.columns = ["2.5%", "97.5%", "coef"]
    odds = np.exp(conf[["coef", "2.5%", "97.5%"]])
    odds.columns = ["OR", "OR_2.5%", "OR_97.5%"]
    odds["p"] = model.pvalues
    print(odds.round(3))

    return model


# ---------------------------------------------------------------------
# 4. Mixed-effects model (random intercept per respondent)
# ---------------------------------------------------------------------
def run_mixed_effects(df):
    print("\n" + "=" * 72)
    print("4. MIXED-EFFECTS MODEL (random intercept per respondent)")
    print("=" * 72)
    print("DV: trust_composite. Fixed effect: condition. Random intercept: respondent_id.")
    print("(Each respondent contributes multiple scenario-level observations, so a plain")
    print(" OLS/ANOVA across all rows would treat those as independent — this doesn't.)")

    model = smf.mixedlm(
        "trust_composite ~ C(condition)",
        data=df,
        groups=df["respondent_id"],
    ).fit(reml=True, method="powell")

    print("\n" + str(model.summary()))

    resid_var = model.scale
    re_var = float(model.cov_re.iloc[0, 0])
    icc = re_var / (re_var + resid_var)
    print(f"\nRandom-intercept variance (between respondents): {re_var:.4f}")
    print(f"Residual variance (within respondent, across scenarios): {resid_var:.4f}")
    print(f"Intraclass correlation (ICC): {icc:.3f}  "
          f"-> {icc:.1%} of variance in trust sits at the respondent level")

    return model


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DATA_PATH
    df, conditions, trust_items = load_data(path)
    print(f"Loaded {len(df)} observations from {df['respondent_id'].nunique()} respondents ({path}).")
    print(f"Conditions: {conditions}")
    print(f"Trust items: {trust_items} -> trust_composite recomputed as their mean.")

    run_anova(df, conditions)
    run_bradley_terry(df, conditions)
    run_logistic(df)
    run_mixed_effects(df)
