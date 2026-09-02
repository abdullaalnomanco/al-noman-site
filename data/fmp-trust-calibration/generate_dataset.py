#!/usr/bin/env python3
"""
Synthetic dataset generator for the FMP trust-calibration study
(case-studies/fmp-trust-calibration.html).

Simulates 678 respondents each rating the same 10 fictional loan
scenarios under one of three explanation conditions (none / surface /
counterfactual), producing 6,780 long-form observations. Used to pilot
the analysis pipeline ahead of the live study — not real participant
data.

Usage:
    python3 generate_dataset.py

Writes trust_calibration_synthetic.csv next to this script and prints
a count summary (used to cross-check the numbers quoted in the case
study: n = 678, 6,780 observations).
"""
import csv
import random
import statistics
from pathlib import Path

SEED = 2026
N_RESPONDENTS = 678
CONDITIONS = ["none", "surface", "counterfactual"]
GENDERS = ["female", "male", "nonbinary", "prefer_not_to_say"]
GENDER_WEIGHTS = [0.47, 0.47, 0.04, 0.02]

# Fixed scenario bank: same 10 fictional loan scenarios shown to every
# respondent. ai_correct is the pilot's ground truth for whether the
# AI's recommendation matched the "right" outcome for that scenario.
SCENARIOS = [
    {"id": 1, "loan_amount": 8000, "credit_score": 610, "ai_recommendation": "deny", "ai_confidence": 82, "ai_correct": True},
    {"id": 2, "loan_amount": 15000, "credit_score": 705, "ai_recommendation": "approve", "ai_confidence": 91, "ai_correct": True},
    {"id": 3, "loan_amount": 22000, "credit_score": 640, "ai_recommendation": "approve", "ai_confidence": 58, "ai_correct": False},
    {"id": 4, "loan_amount": 5000, "credit_score": 590, "ai_recommendation": "deny", "ai_confidence": 74, "ai_correct": True},
    {"id": 5, "loan_amount": 30000, "credit_score": 720, "ai_recommendation": "approve", "ai_confidence": 88, "ai_correct": True},
    {"id": 6, "loan_amount": 12000, "credit_score": 655, "ai_recommendation": "deny", "ai_confidence": 63, "ai_correct": False},
    {"id": 7, "loan_amount": 9000, "credit_score": 680, "ai_recommendation": "approve", "ai_confidence": 77, "ai_correct": True},
    {"id": 8, "loan_amount": 18000, "credit_score": 600, "ai_recommendation": "approve", "ai_confidence": 55, "ai_correct": False},
    {"id": 9, "loan_amount": 7000, "credit_score": 730, "ai_recommendation": "approve", "ai_confidence": 94, "ai_correct": True},
    {"id": 10, "loan_amount": 25000, "credit_score": 620, "ai_recommendation": "deny", "ai_confidence": 69, "ai_correct": True},
]

TRUST_ITEMS = [f"t{i}" for i in range(1, 13)]  # Jian et al. (2000), 12 items, 1-7 Likert

# How strongly each condition lets trust track whether the AI was
# actually correct (higher = better calibration).
CALIBRATION_STRENGTH = {"none": 0.15, "surface": 0.45, "counterfactual": 0.85}


def clamp(value, low, high):
    return max(low, min(high, value))


def make_respondent(rng, respondent_id, condition):
    return {
        "respondent_id": f"R{respondent_id:03d}",
        "age": clamp(round(rng.gauss(34, 11)), 18, 75),
        "gender": rng.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0],
        "financial_literacy": clamp(round(rng.gauss(3.1, 1.0)), 1, 5),
        "condition": condition,
    }


def make_trust_items(rng, base_trust):
    items = {}
    for key in TRUST_ITEMS:
        value = clamp(round(rng.gauss(base_trust, 0.7)), 1, 7)
        items[key] = value
    return items


def calibration_label(ai_correct, trust_composite, threshold=4.0):
    trusts_it = trust_composite >= threshold
    if trusts_it and not ai_correct:
        return "over-trust"
    if not trusts_it and ai_correct:
        return "under-trust"
    return "calibrated"


def generate_rows():
    rng = random.Random(SEED)

    # Assign respondents to conditions as evenly as possible.
    condition_cycle = CONDITIONS * (N_RESPONDENTS // len(CONDITIONS) + 1)
    condition_cycle = condition_cycle[:N_RESPONDENTS]
    rng.shuffle(condition_cycle)

    rows = []
    for i in range(1, N_RESPONDENTS + 1):
        respondent = make_respondent(rng, i, condition_cycle[i - 1])
        strength = CALIBRATION_STRENGTH[respondent["condition"]]

        for scenario in SCENARIOS:
            # Baseline trust leans on the AI's stated confidence; the
            # explanation condition determines how much that trust
            # actually shifts toward the ground-truth correctness.
            confidence_pull = (scenario["ai_confidence"] - 50) / 50 * 1.5
            correctness_pull = (1.5 if scenario["ai_correct"] else -1.5) * strength
            base_trust = clamp(4.0 + confidence_pull + correctness_pull + rng.gauss(0, 0.4), 1, 7)

            items = make_trust_items(rng, base_trust)
            trust_composite = round(statistics.mean(items.values()), 2)

            agree_prob = clamp((trust_composite - 1) / 6, 0.03, 0.97)
            agree_with_ai = rng.random() < agree_prob

            row = {
                **respondent,
                "scenario_id": scenario["id"],
                "loan_amount": scenario["loan_amount"],
                "applicant_credit_score": scenario["credit_score"],
                "ai_recommendation": scenario["ai_recommendation"],
                "ai_confidence": scenario["ai_confidence"],
                "ai_correct": scenario["ai_correct"],
                **items,
                "trust_composite": trust_composite,
                "agree_with_ai": agree_with_ai,
                "response_time_sec": round(clamp(rng.gauss(14, 5), 3, 45), 1),
                "calibration_label": calibration_label(scenario["ai_correct"], trust_composite),
            }
            rows.append(row)

    return rows


def write_csv(rows, path):
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_counts(rows):
    respondents = {row["respondent_id"] for row in rows}
    by_condition = {}
    by_label = {}
    for row in rows:
        by_condition[row["condition"]] = by_condition.get(row["condition"], 0) + 1
        by_label[row["calibration_label"]] = by_label.get(row["calibration_label"], 0) + 1

    print(f"respondents: {len(respondents)}")
    print(f"observations: {len(rows)}")
    print(f"observations per respondent: {len(rows) // len(respondents)}")
    print("condition counts (observations):")
    for cond, n in sorted(by_condition.items()):
        print(f"  {cond}: {n} ({n // 10} respondents)")
    print("calibration label counts:")
    for label, n in sorted(by_label.items()):
        print(f"  {label}: {n} ({n / len(rows):.1%})")


if __name__ == "__main__":
    rows = generate_rows()
    out_path = Path(__file__).parent / "trust_calibration_synthetic.csv"
    write_csv(rows, out_path)
    print(f"wrote {out_path}")
    print_counts(rows)
