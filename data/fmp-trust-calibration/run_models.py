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
    python3 run_models.py

Requires numpy / pandas / scipy / statsmodels.
"""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd

DATA_PATH = "trust_calibration_synthetic.csv"


def load_data():
    df = pd.read_csv(DATA_PATH)
    df["agree_with_ai"] = df["agree_with_ai"].astype(str).str.lower() == "true"
    df["ai_correct"] = df["ai_correct"].astype(str).str.lower() == "true"
    df["condition"] = pd.Categorical(df["condition"], categories=["none", "surface", "counterfactual"])
    # "Good decision": followed the AI when it was right, didn't when it was wrong.
    df["decision_correct"] = df["agree_with_ai"] == df["ai_correct"]
    return df


# ---------------------------------------------------------------------
# 1. One-way ANOVA + Tukey-Kramer
# ---------------------------------------------------------------------
def run_anova(df):
    print("\n" + "=" * 72)
    print("1. ONE-WAY ANOVA + TUKEY-KRAMER POST-HOC")
    print("=" * 72)

    per_resp = df.groupby(["respondent_id", "condition"], observed=True).agg(
        trust_mean=("trust_composite", "mean"),
        agree_rate=("agree_with_ai", "mean"),
        accuracy=("decision_correct", "mean"),
        rt_mean=("response_time_sec", "mean"),
    ).reset_index()

    outcomes = {
        "trust_mean": "Mean trust composite (1-7)",
        "agree_rate": "Rate of agreeing with the AI",
        "accuracy": "Decision accuracy (agreed iff AI correct)",
        "rt_mean": "Mean response time (s)",
    }

    for col, label in outcomes.items():
        groups = [per_resp.loc[per_resp["condition"] == c, col].values for c in ["none", "surface", "counterfactual"]]
        f_stat, p_val = stats.f_oneway(*groups)
        means = {c: g.mean() for c, g in zip(["none", "surface", "counterfactual"], groups)}
        print(f"\n-- {label} --")
        print(f"   means: none={means['none']:.3f}  surface={means['surface']:.3f}  counterfactual={means['counterfactual']:.3f}")
        print(f"   F(2, {len(per_resp) - 3}) = {f_stat:.3f}, p = {p_val:.4g}")
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


def run_bradley_terry(df, seed=2026):
    print("\n" + "=" * 72)
    print("2. BRADLEY-TERRY PAIRWISE-COMPARISON MODEL")
    print("=" * 72)
    print("Contest = one individual duel: a random respondent from condition A vs. a")
    print("random respondent from condition B, on the same scenario. Whoever made the")
    print("correct decision on that scenario wins the duel; both-correct/both-wrong")
    print("ties split 0.5/0.5. This uses each person's actual outcome, not the group")
    print("mean, so a 'weaker' condition still wins plenty of individual duels.")

    conditions = ["none", "surface", "counterfactual"]
    rng = np.random.default_rng(seed)

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
        for a, b in [("none", "surface"), ("none", "counterfactual"), ("surface", "counterfactual")]:
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
def run_logistic(df):
    print("\n" + "=" * 72)
    print("3. LOGISTIC REGRESSION — 'HIGH AI FOLLOWER'")
    print("=" * 72)

    per_resp = df.groupby("respondent_id", observed=True).agg(
        agree_rate=("agree_with_ai", "mean"),
        financial_literacy=("financial_literacy", "first"),
        need_for_cognition=("need_for_cognition", "first"),
        tech_disposition=("tech_disposition", "first"),
        condition=("condition", "first"),
    ).reset_index()

    median_rate = per_resp["agree_rate"].median()
    per_resp["high_ai_follower"] = (per_resp["agree_rate"] > median_rate).astype(int)
    print(f"Median agreement rate = {median_rate:.3f} (split point for the binary DV)")
    print(f"high_ai_follower = 1 for {per_resp['high_ai_follower'].sum()} / {len(per_resp)} respondents")

    model = smf.logit(
        "high_ai_follower ~ financial_literacy + need_for_cognition + tech_disposition + C(condition)",
        data=per_resp,
    ).fit(disp=False)

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
    print("(Each respondent contributes 10 scenario-level observations, so a plain")
    print(" OLS/ANOVA on all 6,780 rows would treat those as independent — this doesn't.)")

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
    df = load_data()
    print(f"Loaded {len(df)} observations from {df['respondent_id'].nunique()} respondents.")

    run_anova(df)
    run_bradley_terry(df)
    run_logistic(df)
    run_mixed_effects(df)
