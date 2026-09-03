#!/usr/bin/env python3
"""
Synthetic dataset generator for the FMP trust-calibration study
(case-studies/fmp-trust-calibration.html).

Simulates 350 respondents rating up to 10 fictional loan scenarios each,
under one of three explanation conditions (none / surface /
counterfactual). Used to pilot the analysis pipeline ahead of the live
study — not real participant data — but built to look and behave like a
real platform export rather than a clean textbook grid:

  - Condition assignment is simple random, not balanced, so cell sizes
    are uneven (real random assignment rarely lands exactly even).
  - Scenarios are shown in a randomized per-respondent order, and a
    small fraction of respondents drop out partway through (their rows
    simply stop, they aren't padded or imputed).
  - A small fraction of trust-scale items and demographic fields are
    left blank (real respondents skip questions).
  - A small fraction of respondents straightline (answer every item
    identically, an attention-check failure real datasets always
    contain) — flagged via attention_check_passed, not removed.
  - Every row carries a realistic completion timestamp, respondent IDs
    look like a panel export, and response_time_sec has some genuine
    speeder/straggler outliers rather than a tidy bell curve.

Usage:
    python3 generate_dataset.py

Writes trust_calibration_synthetic.csv next to this script and prints
a count summary (respondents, observations, attrition, missingness).
"""
import csv
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path

SEED = 2026
N_RESPONDENTS = 350
CONDITIONS = ["none", "surface", "counterfactual"]
GENDERS = ["female", "male", "nonbinary", "prefer_not_to_say"]
GENDER_WEIGHTS = [0.47, 0.47, 0.04, 0.02]

# Fixed scenario bank: same 10 fictional loan scenarios shown to every
# respondent (in a randomized per-respondent order). ai_correct is the
# pilot's ground truth for whether the AI's recommendation matched the
# "right" outcome for that scenario.
SCENARIOS = [
    {"id": 1, "loan_amount": 8000, "credit_score": 610, "ai_recommendation": "deny", "ai_confidence": 82, "ai_correct": True},
    {"id": 2, "loan_amount": 15000, "credit_score": 705, "ai_recommendation": "approve", "ai_confidence": 91, "ai_correct": True},
    {"id": 3, "loan_amount": 22000, "credit_score": 640, "ai_recommendation": "approve", "ai_confidence": 58, "ai_correct": True},
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
# actually correct (higher = better calibration). Kept close together —
# a real explanation manipulation nudges calibration, it doesn't
# override it.
CALIBRATION_STRENGTH = {"none": 0.22, "surface": 0.38, "counterfactual": 0.56}

# Data-quality realism knobs.
P_EARLY_DROPOUT = 0.05       # respondent quits partway through
P_ITEM_MISSING = 0.012       # any single trust item left blank
P_DEMOGRAPHIC_MISSING = 0.03 # any single demographic field left blank
P_STRAIGHTLINER = 0.02       # respondent answers every item identically
P_SPEEDER = 0.02             # respondent rushes (very low response time)
P_STRAGGLER = 0.015          # respondent is very slow on a given item

COLLECTION_START = datetime(2026, 1, 12, 0, 0, 0)
COLLECTION_DAYS = 40
# Weekday index (Mon=0) -> relative recruitment volume.
WEEKDAY_WEIGHTS = [1.3, 1.3, 1.3, 1.3, 1.1, 0.6, 0.5]
# Hour of day -> relative response volume (quiet overnight, peaks late morning/evening).
HOUR_WEIGHTS = [
    0.1, 0.05, 0.05, 0.05, 0.05, 0.1, 0.3, 0.6,   # 0-7
    0.9, 1.3, 1.4, 1.3, 1.1, 1.0, 1.1, 1.2,        # 8-15
    1.3, 1.4, 1.5, 1.6, 1.5, 1.2, 0.8, 0.4,        # 16-23
]


def clamp(value, low, high):
    return max(low, min(high, value))


def make_respondent_id(rng, seen):
    while True:
        token = f"P{rng.getrandbits(40):010x}"
        if token not in seen:
            seen.add(token)
            return token


def make_start_timestamp(rng):
    day_weights = [WEEKDAY_WEIGHTS[(COLLECTION_START + timedelta(days=d)).weekday()] for d in range(COLLECTION_DAYS)]
    day_offset = rng.choices(range(COLLECTION_DAYS), weights=day_weights, k=1)[0]
    hour = rng.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
    minute, second = rng.randrange(60), rng.randrange(60)
    return COLLECTION_START + timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)


def make_respondent(rng, respondent_id, condition):
    respondent = {
        "respondent_id": respondent_id,
        "age": clamp(round(rng.gauss(34, 11)), 18, 75),
        "gender": rng.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0],
        "financial_literacy": clamp(round(rng.gauss(3.1, 1.0)), 1, 5),
        # Need for Cognition (Cacioppo & Petty, 1982 short-form style) and
        # tech disposition, both 1-7 composite self-report scales.
        "need_for_cognition": clamp(round(rng.gauss(4.3, 1.2), 2), 1, 7),
        "tech_disposition": clamp(round(rng.gauss(4.5, 1.3), 2), 1, 7),
        "condition": condition,
        # Stable per-respondent trust disposition, applied to every one of
        # their scenario judgments — this is the individual-differences
        # signal a random intercept (mixed-effects model) should recover.
        # People vary a lot more than any single manipulation moves them.
        "_trust_baseline_offset": rng.gauss(0, 1.05),
        "_is_straightliner": rng.random() < P_STRAIGHTLINER,
        "_straightline_value": rng.randint(1, 7),
        "_is_speeder": rng.random() < P_SPEEDER,
        "_started_at": make_start_timestamp(rng),
    }
    # Real respondents skip demographic questions sometimes.
    for field in ("age", "gender", "financial_literacy", "need_for_cognition", "tech_disposition"):
        if rng.random() < P_DEMOGRAPHIC_MISSING:
            respondent[field] = ""
    return respondent


def make_trust_items(rng, base_trust, straightliner, straightline_value):
    items = {}
    for key in TRUST_ITEMS:
        if straightliner:
            value = straightline_value
        else:
            value = clamp(round(rng.gauss(base_trust, 0.7)), 1, 7)
        items[key] = "" if rng.random() < P_ITEM_MISSING else value
    return items


def calibration_label(ai_correct, trust_composite, threshold=4.0):
    if trust_composite is None:
        return ""
    trusts_it = trust_composite >= threshold
    if trusts_it and not ai_correct:
        return "over-trust"
    if not trusts_it and ai_correct:
        return "under-trust"
    return "calibrated"


def generate_rows():
    rng = random.Random(SEED)
    seen_ids = set()

    rows = []
    n_dropouts = 0
    for i in range(1, N_RESPONDENTS + 1):
        respondent_id = make_respondent_id(rng, seen_ids)
        condition = rng.choice(CONDITIONS)  # simple random assignment -> uneven cell sizes
        respondent = make_respondent(rng, respondent_id, condition)
        strength = CALIBRATION_STRENGTH[condition]
        straightliner = respondent["_is_straightliner"]

        presentation_order = SCENARIOS.copy()
        rng.shuffle(presentation_order)

        n_to_complete = len(presentation_order)
        if rng.random() < P_EARLY_DROPOUT:
            n_to_complete = rng.randint(3, 8)
            n_dropouts += 1

        clock = respondent["_started_at"]
        for position, scenario in enumerate(presentation_order[:n_to_complete], start=1):
            confidence_pull = (scenario["ai_confidence"] - 50) / 50 * 1.5
            correctness_pull = (1.5 if scenario["ai_correct"] else -1.5) * strength
            # Ambiguous scenarios (AI confidence near 50) are noisier
            # moment-to-moment judgments than clear-cut ones — same
            # respondent, same condition, but an "off day" call.
            scenario_noise_sd = 0.45 + (50 - abs(scenario["ai_confidence"] - 50)) / 110
            base_trust = clamp(
                4.0
                + confidence_pull
                + correctness_pull
                + respondent["_trust_baseline_offset"]
                + rng.gauss(0, scenario_noise_sd),
                1, 7,
            )

            items = make_trust_items(rng, base_trust, straightliner, respondent["_straightline_value"])
            numeric_items = [v for v in items.values() if v != ""]
            trust_composite = round(statistics.mean(numeric_items), 2) if numeric_items else None

            # Individual differences nudge reliance on top of trust itself:
            # more tech-disposed respondents lean on the AI more; higher
            # need-for-cognition and financial literacy make people scrutinize
            # more and rely on it less, independent of momentary trust.
            nfc = respondent["need_for_cognition"] if respondent["need_for_cognition"] != "" else 4.0
            fin_lit = respondent["financial_literacy"] if respondent["financial_literacy"] != "" else 3.0
            tech_disp = respondent["tech_disposition"] if respondent["tech_disposition"] != "" else 4.0
            trait_pull = (
                0.05 * (tech_disp - 4)
                - 0.04 * (nfc - 4)
                - 0.03 * (fin_lit - 3)
            )
            reference_trust = trust_composite if trust_composite is not None else base_trust
            agree_prob = clamp((reference_trust - 1) / 6 + trait_pull, 0.02, 0.98)
            agree_with_ai = rng.random() < agree_prob
            other_decision = "deny" if scenario["ai_recommendation"] == "approve" else "approve"
            participant_decision = scenario["ai_recommendation"] if agree_with_ai else other_decision

            if respondent["_is_speeder"]:
                response_time = round(clamp(rng.gauss(2.5, 0.8), 1, 5), 1)
            elif rng.random() < P_STRAGGLER:
                response_time = round(clamp(rng.gauss(75, 20), 45, 140), 1)
            else:
                response_time = round(clamp(rng.gauss(14, 5), 3, 45), 1)

            clock = clock + timedelta(seconds=response_time + rng.uniform(0.5, 2.5))

            respondent_public = {k: v for k, v in respondent.items() if not k.startswith("_")}
            row = {
                **respondent_public,
                "scenario_id": scenario["id"],
                "presentation_position": position,
                "loan_amount": scenario["loan_amount"],
                "applicant_credit_score": scenario["credit_score"],
                "ai_recommendation": scenario["ai_recommendation"],
                "ai_confidence": scenario["ai_confidence"],
                "ai_correct": scenario["ai_correct"],
                **items,
                # participant_decision is the raw field a real export would
                # carry; agree_with_ai/decision_correct/calibration_label
                # below are conveniences derived from it (run_models.py
                # re-derives them itself, the same way it would for real data).
                "participant_decision": participant_decision,
                "trust_composite": trust_composite if trust_composite is not None else "",
                "agree_with_ai": agree_with_ai,
                "response_time_sec": response_time,
                "response_timestamp": clock.strftime("%Y-%m-%dT%H:%M:%S"),
                "attention_check_passed": not straightliner,
                "calibration_label": calibration_label(scenario["ai_correct"], trust_composite),
            }
            rows.append(row)

    return rows, n_dropouts


def write_csv(rows, path):
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_counts(rows, n_dropouts):
    respondents = {row["respondent_id"] for row in rows}
    by_condition_resp = {}
    by_condition_obs = {}
    by_label = {}
    n_missing_items = 0
    n_straightliners = 0
    seen_straightliner_resp = set()
    for row in rows:
        by_condition_obs[row["condition"]] = by_condition_obs.get(row["condition"], 0) + 1
        by_condition_resp.setdefault(row["condition"], set()).add(row["respondent_id"])
        by_label[row["calibration_label"]] = by_label.get(row["calibration_label"], 0) + 1
        n_missing_items += sum(1 for item in TRUST_ITEMS if row[item] == "")
        if not row["attention_check_passed"] and row["respondent_id"] not in seen_straightliner_resp:
            seen_straightliner_resp.add(row["respondent_id"])
            n_straightliners += 1

    print(f"respondents: {len(respondents)}")
    print(f"observations: {len(rows)}")
    print(f"respondents with early dropout (partial completion): {n_dropouts}")
    print(f"respondents flagged attention_check_passed=False (straightliners): {n_straightliners}")
    print(f"blank trust-item cells: {n_missing_items} / {len(rows) * len(TRUST_ITEMS)} "
          f"({n_missing_items / (len(rows) * len(TRUST_ITEMS)):.1%})")
    print("condition counts (observations / respondents):")
    for cond in sorted(by_condition_obs):
        print(f"  {cond}: {by_condition_obs[cond]} obs / {len(by_condition_resp[cond])} respondents")
    print("calibration label counts:")
    for label, n in sorted(by_label.items()):
        print(f"  {label or '(missing)'}: {n} ({n / len(rows):.1%})")


if __name__ == "__main__":
    rows, n_dropouts = generate_rows()
    out_path = Path(__file__).parent / "trust_calibration_synthetic.csv"
    write_csv(rows, out_path)
    print(f"wrote {out_path}")
    print_counts(rows, n_dropouts)
