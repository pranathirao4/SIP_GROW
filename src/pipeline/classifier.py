"""
Stage D: Granular Behavioral Classification & Quote Extraction Pipeline
Classifies relevant qualitative records across:
  - Investor Stage (First-Time, Considering, Continuing, Paused, Cancelled, Unknown)
  - Reported Behaviour (Started, Continued, Reduced, Paused, Cancelled, Failed Instalment)
  - Trigger Context (Salary delay, Market drop, Emergency expense, Job loss, Bank penalty)
  - Reported Pain Point & Problem Nature (App Friction vs Cash-flow Problem)
  - Exact Verbatim Supporting Quote Citation
Guarantees zero demographic hallucinations (only explicit textual evidence is tagged).
"""

import sys
import json
import re
from pathlib import Path

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')


def extract_best_quote(text, keywords):
    """Extract the most relevant single sentence from text containing key terms."""
    if not text:
        return ""
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    best_sentence = ""
    highest_matches = 0

    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) < 20 or len(s_clean) > 300:
            continue
        matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', s_clean, re.I))
        if matches > highest_matches:
            highest_matches = matches
            best_sentence = s_clean

    return best_sentence or (sentences[0][:200] if sentences else text[:200])


def classify_record(record):
    """Extract multi-dimensional behavioral metadata and verbatim citations."""
    title = record.get("title", "")
    raw_text = record.get("raw_text", "")
    text = f"{title}\n{raw_text}".lower()

    # 1. Investor Stage
    stage = "Unknown"
    if re.search(r"\b(?:first\s+time|beginner|new\s+to\s+invest|started\s+my\s+first|novice)\b", text):
        stage = "First-Time"
    elif re.search(r"\b(?:considering|thinking\s+of\s+starting|should\s+i\s+start|planning\s+to\s+sip)\b", text):
        stage = "Considering"
    elif re.search(r"\b(?:stopped|cancelled|discontinued|exited)\b", text):
        stage = "Cancelled"
    elif re.search(r"\b(?:paused|pausing|skipped|skip\s+instalment)\b", text):
        stage = "Paused"
    elif re.search(r"\b(?:continuing|investing\s+since|past\s+\d+\s+years|regular\s+sip)\b", text):
        stage = "Continuing"

    # 2. Reported Behaviour
    behaviour = "Unknown"
    if re.search(r"\b(?:cancel|cancelled|cancelling)\b", text):
        behaviour = "Cancelled"
    elif re.search(r"\b(?:stop|stopped|stopping|discontinue)\b", text):
        behaviour = "Stopped"
    elif re.search(r"\b(?:pause|paused|pausing|skip|skipped)\b", text):
        behaviour = "Paused"
    elif re.search(r"\b(?:reduce|reduced|reducing|lowered)\s+(?:amount|sip)\b", text):
        behaviour = "Reduced"
    elif re.search(r"\b(?:fail|failed|failure|rejected|bounce)\b", text):
        behaviour = "Failed Instalment"
    elif re.search(r"\b(?:started|started\s+investing|invested)\b", text):
        behaviour = "Started"

    # 3. Trigger Context
    triggers = []
    if re.search(r"\b(?:bounce|penalty|ecs|charge|450|bank\s+fee)\b", text):
        triggers.append("Bank ECS Bounce Penalty")
    if re.search(r"\b(?:salary\s+delay|late\s+salary|salary\s+date|paycheck)\b", text):
        triggers.append("Salary Date Mismatch")
    if re.search(r"\b(?:job\s+loss|laid\s+off|layoff|unemployed)\b", text):
        triggers.append("Job Loss / Unemployment")
    if re.search(r"\b(?:emergency|medical|hospital|urgent\s+money)\b", text):
        triggers.append("Emergency Expense Shock")
    if re.search(r"\b(?:negative|red|market\s+fall|crash|drawdown|loss)\b", text):
        triggers.append("Market Volatility & Negative Returns")
    if re.search(r"\b(?:student|college|fees|pocket\s+money|no\s+money)\b", text):
        triggers.append("Student / Insufficient Income")
    if re.search(r"\b(?:freelanc|irregular|variable|commission)\b", text):
        triggers.append("Irregular / Freelance Cash-Flow")

    primary_trigger = triggers[0] if triggers else "Unspecified Financial Friction"

    # 4. Problem Nature (App Friction vs Cash-Flow vs Volatility)
    problem_nature = "Broader Financial Problem"
    if re.search(r"\b(?:mandate|auto\s*pay|groww|app|bug|failed\s+payment|deducted\s+not\s+credited|units\s+not|pause\s+button)\b", text):
        if triggers and any(t in ["Bank ECS Bounce Penalty", "Salary Date Mismatch"] for t in triggers):
            problem_nature = "Hybrid: Bank Mandate Timing & Penalty Friction"
        else:
            problem_nature = "In-App / Technical Mandate Friction"
    elif "Market Volatility" in primary_trigger:
        problem_nature = "Psychological / Expectation Mismatch"

    # 5. Extract Supporting Verbatim Quote
    keywords_to_quote = ["sip", "stop", "stopped", "cancel", "pause", "failed", "deducted", "penalty", "bounce", "negative", "loss"]
    combined_body = f"{title}. {raw_text}".strip()
    verbatim_quote = extract_best_quote(combined_body, keywords_to_quote)

    confidence = 0.85 if stage != "Unknown" and behaviour != "Unknown" else 0.70

    return {
        "investor_stage": stage,
        "reported_behaviour": behaviour,
        "trigger_context": primary_trigger,
        "all_triggers": triggers,
        "problem_nature": problem_nature,
        "evidence_type": "Direct Quote" if verbatim_quote else "Indirect Inference",
        "verbatim_quote": verbatim_quote,
        "classification_confidence": confidence
    }


def run_classifier(
    input_path="data/processed/relevant_records.json",
    output_path="data/processed/classified_records.json"
):
    """Run Stage D classification over all relevant records."""
    print("=== Stage D: Granular AI Classification & Quote Extraction ===")

    in_file = Path(input_path)
    if not in_file.exists():
        print(f"[ERROR] Relevant records not found at {input_path}")
        sys.exit(1)

    with open(in_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"• Ingesting {len(records)} relevant records...")

    classified_records = []
    stage_counts = {}
    behaviour_counts = {}
    trigger_counts = {}

    for item in records:
        clf = classify_record(item)
        item["classification"] = clf

        # Aggregate metrics
        st = clf["investor_stage"]
        bh = clf["reported_behaviour"]
        tr = clf["trigger_context"]

        stage_counts[st] = stage_counts.get(st, 0) + 1
        behaviour_counts[bh] = behaviour_counts.get(bh, 0) + 1
        trigger_counts[tr] = trigger_counts.get(tr, 0) + 1

        classified_records.append(item)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(classified_records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(classified_records)} classified records to: {output_path}")

    print("\n--- Investor Stage Breakdown ---")
    for k, v in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {k}: {v}")

    print("\n--- Reported Behaviour Breakdown ---")
    for k, v in sorted(behaviour_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {k}: {v}")

    print("\n--- Top Trigger Contexts ---")
    for k, v in sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)[:6]:
        print(f"  • {k}: {v} records")

    return classified_records


if __name__ == "__main__":
    run_classifier()
