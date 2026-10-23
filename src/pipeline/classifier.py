"""
Stage D: Multi-Layered Behavioral & Causal Classification Pipeline
Distinguishes between:
  1. What the user explicitly stated (Surface Statement)
  2. The observable behaviour (Action taken)
  3. The underlying problem (Cognitive / structural friction)
  4. The hypothesised causal mechanism (Why this occurs)
  5. The resulting consequence / churn nature (Voluntary vs Involuntary)
  6. The potential connection to 12-month SIP retention
"""

import sys
import json
import re
from urllib.parse import urlparse
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


def clean_root_url(url: str) -> str:
    """Normalize URL to its root thread/page to accurately count unique conversations."""
    if not url:
        return "unknown_conversation"
    try:
        parsed = urlparse(url)
        # For Reddit: strip trailing comment IDs to get thread URL
        path = parsed.path
        if "reddit.com" in parsed.netloc:
            m = re.match(r'(/r/[^/]+/comments/[a-z0-9]+)', path)
            if m:
                return f"https://www.reddit.com{m.group(1)}"
        elif "tradingqna.com" in parsed.netloc:
            m = re.match(r'(/t/[^/]+/\d+)', path)
            if m:
                return f"https://tradingqna.com{m.group(1)}"
        elif "youtube.com" in parsed.netloc:
            # video base
            video_id = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id.group(1)}"
        return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip('/')
    except Exception:
        return url


def classify_record(record):
    """Extract multi-dimensional behavioral metadata, underlying causal mechanisms, and verbatim citations."""
    title = record.get("title", "")
    raw_text = record.get("raw_text", "")
    text = f"{title}\n{raw_text}".lower()
    url = record.get("url", "")
    root_conv_url = clean_root_url(url)

    # 1. Investor Stage
    stage = "Unknown"
    if re.search(r"\b(?:first\s+time|beginner|new\s+to\s+invest|started\s+my\s+first|novice|noob|first\s+month|first\s+sip)\b", text):
        stage = "First-Time Investor"
    elif re.search(r"\b(?:considering|thinking\s+of\s+starting|should\s+i\s+start|planning\s+to\s+sip)\b", text):
        stage = "Considering"
    elif re.search(r"\b(?:stopped|cancelled|discontinued|exited|deleted\s+mandate)\b", text):
        stage = "Discontinued / Cancelled"
    elif re.search(r"\b(?:paused|pausing|skipped|skip\s+instalment|temporarily\s+stop)\b", text):
        stage = "Paused / Interrupted"
    elif re.search(r"\b(?:continuing|investing\s+since|past\s+\d+\s+years|regular\s+sip|continued|stayed\s+invested)\b", text):
        stage = "Continuing / Retained"

    # 2. Observable Behaviour
    behaviour = "Unspecified Behaviour"
    if re.search(r"\b(?:cancel|cancelled|cancelling|delete\s+autopay)\b", text):
        behaviour = "Hard Cancelled SIP Mandate"
    elif re.search(r"\b(?:stop|stopped|stopping|discontinue)\b", text):
        behaviour = "Stopped Monthly Contribution"
    elif re.search(r"\b(?:pause|paused|pausing|skip|skipped|skip\s+month)\b", text):
        behaviour = "Temporarily Paused / Skipped"
    elif re.search(r"\b(?:reduce|reduced|reducing|lowered)\s+(?:amount|sip|contribution)\b", text):
        behaviour = "Reduced Contribution Amount"
    elif re.search(r"\b(?:fail|failed|failure|rejected|bounce|bounced)\b", text):
        behaviour = "Encountered Debit Failure / Mandate Rejection"
    elif re.search(r"\b(?:continued|still\s+investing|did\s+not\s+stop|stayed\s+invested|12\s+months)\b", text):
        behaviour = "Maintained Active SIP"
    elif re.search(r"\b(?:started|invested|first\s+investment)\b", text):
        behaviour = "Started Initial SIP"

    # 3. Context & Trigger Event
    triggers = []
    if re.search(r"\b(?:bounce|penalty|ecs|charge|450|bank\s+fee|overdraft|penalty\s+charges)\b", text):
        triggers.append("Bank ECS / NACH Bounce Penalty Risk")
    if re.search(r"\b(?:salary\s+delay|late\s+salary|salary\s+date|paycheck|salary\s+credited\s+late|mismatch)\b", text):
        triggers.append("Salary Date vs SIP Debit Mismatch")
    if re.search(r"\b(?:job\s+loss|laid\s+off|layoff|unemployed|unemployment)\b", text):
        triggers.append("Income Disruption / Job Loss")
    if re.search(r"\b(?:emergency|medical|hospital|urgent\s+money|family\s+responsibility)\b", text):
        triggers.append("Unplanned Emergency Expense Shock")
    if re.search(r"\b(?:negative|red|market\s+fall|crash|drawdown|loss|correction|xirr\s+negative)\b", text):
        triggers.append("Early Portfolio Drawdown & Negative XIRR")
    if re.search(r"\b(?:student|college|fees|pocket\s+money|no\s+money|allowance)\b", text):
        triggers.append("Student Allowance Depletion / Low Discretionary Cash")
    if re.search(r"\b(?:freelanc|irregular|variable|commission|variable\s+salary)\b", text):
        triggers.append("Irregular / Freelance Cash-Flow Timing")
    if re.search(r"\b(?:groww\s+(?:autopay|mandate|status|bug|error|glitch)|pending\s+status|order\s+failed)\b", text):
        triggers.append("Groww Mandate Sync / App Technical Failure")
    if re.search(r"\b(?:pause\s+(?:button|option|feature)|cannot\s+find\s+pause|no\s+pause)\b", text):
        triggers.append("Inability to Locate Pause Feature")
    if re.search(r"\b(?:loan|emi|credit\s+card|rent|wedding|festiv)\b", text):
        triggers.append("Competing High-Priority Expenses (EMI/Rent)")

    primary_trigger = triggers[0] if triggers else "Unspecified Financial Disruption"

    # 4. Underlying Problem & Hypothesised Mechanism
    # Differentiating surface complaints from cognitive, behavioral, or technical root problems
    underlying_problem = "General Allocation Adjustment"
    hypothesised_mechanism = "Investor reassessing monthly savings allocation."
    churn_nature = "Voluntary Decision"

    if "Bank ECS / NACH Bounce Penalty Risk" in triggers or "Salary Date vs SIP Debit Mismatch" in triggers:
        underlying_problem = "Asymmetrical Bank Penalty Threat Overriding Investment Conviction"
        hypothesised_mechanism = (
            "When delayed salary leaves bank account balance below SIP amount, the impending ₹450-₹590 bank penalty "
            "creates asymmetric loss. The rational self-defense response is proactive hard mandate cancellation, "
            "as users lack confidence in whether skipping a single debit triggers a penalty."
        )
        churn_nature = "Involuntary / Self-Defense Churn"
    elif "Inability to Locate Pause Feature" in triggers:
        underlying_problem = "UI Hierarchy & Information Invisibility (Pause vs Cancel Confusion)"
        hypothesised_mechanism = (
            "User has a temporary 1-3 month liquidity squeeze and intends to take a temporary break, "
            "but because 'Cancel SIP' is prominent while 'Pause SIP' is buried or restricted, they default to hard cancellation."
        )
        churn_nature = "Involuntary / Usability Trap"
    elif "Groww Mandate Sync / App Technical Failure" in triggers:
        underlying_problem = "Opaque Mandate Processing & Bank API Sync Latency"
        hypothesised_mechanism = (
            "UPI Autopay rejection or delayed status updates leave user uncertain if money was lost or deducted. "
            "The perceived fragility of the platform leads to abandonment before reaching month 12."
        )
        churn_nature = "Involuntary Technical Churn"
    elif "Early Portfolio Drawdown & Negative XIRR" in triggers:
        underlying_problem = "Compounding Time-Horizon Misalignment & Loss Aversion"
        hypothesised_mechanism = (
            "First-time investors unconsciously anchor mutual funds to bank Fixed Deposits (guaranteed monthly appreciation). "
            "Encountering negative returns in months 3-6 triggers psychological loss aversion before the benefits of rupee-cost averaging are grasped."
        )
        churn_nature = "Voluntary / Cognitive Expectation Mismatch"
    elif "Student Allowance Depletion / Low Discretionary Cash" in triggers or "Irregular / Freelance Cash-Flow Timing" in triggers:
        underlying_problem = "Rigidity of Fixed-Date Monthly Commitments Against Variable Cash Flows"
        hypothesised_mechanism = (
            "Inflexible monthly deduction schedules penalize variable earners. When cash is tight, the all-or-nothing "
            "commitment causes complete stoppage rather than downward contribution adjustment."
        )
        churn_nature = "Structural Affordability Squeeze"
    elif "Unplanned Emergency Expense Shock" in triggers or "Income Disruption / Job Loss" in triggers:
        underlying_problem = "Lack of Liquidity Buffer / Emergency Reserve Separation"
        hypothesised_mechanism = (
            "Beginner started SIP without a dedicated liquid emergency fund. At the first income disruption or shock, "
            "investments are liquidated and mandates cancelled to secure immediate survival liquidity."
        )
        churn_nature = "Survival Necessity"

    # 5. Potential Connection to 12-Month SIP Retention
    retention_connection = (
        "Directly disrupts the 12-month active SIP milestone. Involuntary mandate cancellations rarely re-activate "
        "spontaneously, converting temporary liquidity or technical hiccups into permanent user drop-off."
    )

    # 6. Extract Supporting Verbatim Quote
    keywords_to_quote = ["sip", "stop", "stopped", "cancel", "pause", "failed", "deducted", "penalty", "bounce", "negative", "loss", "autopay", "groww"]
    combined_body = f"{title}. {raw_text}".strip()
    verbatim_quote = extract_best_quote(combined_body, keywords_to_quote)

    confidence = 0.88 if len(triggers) > 0 and behaviour != "Unspecified Behaviour" else 0.72

    return {
        "root_conversation_url": root_conv_url,
        "investor_stage": stage,
        "observable_behaviour": behaviour,
        "trigger_context": primary_trigger,
        "all_triggers": triggers,
        "underlying_problem": underlying_problem,
        "hypothesised_mechanism": hypothesised_mechanism,
        "churn_nature": churn_nature,
        "retention_connection": retention_connection,
        "verbatim_quote": verbatim_quote,
        "classification_confidence": confidence
    }


def run_classifier(
    input_path="data/processed/relevant_records.json",
    output_path="data/processed/classified_records.json"
):
    """Run Stage D multi-layered causal classification over all relevant records."""
    print("=== Stage D: Multi-Layered Behavioral & Causal Classification ===")

    in_file = Path(input_path)
    if not in_file.exists():
        print(f"[ERROR] Relevant records not found at {input_path}")
        sys.exit(1)

    with open(in_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"• Ingesting {len(records)} relevant records...")

    classified_records = []
    unique_conversations = set()

    for item in records:
        analysis = classify_record(item)
        item["classification"] = analysis
        unique_conversations.add(analysis["root_conversation_url"])
        classified_records.append(item)

    # Save output
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(classified_records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(classified_records)} classified records across {len(unique_conversations)} unique conversations to: {output_path}")

    # Print summary statistics
    problem_counts = {}
    churn_nature_counts = {}
    for r in classified_records:
        prob = r["classification"]["underlying_problem"]
        cn = r["classification"]["churn_nature"]
        problem_counts[prob] = problem_counts.get(prob, 0) + 1
        churn_nature_counts[cn] = churn_nature_counts.get(cn, 0) + 1

    print("\n--- Identified Underlying Problems (Causal Breakdown) ---")
    for p, c in sorted(problem_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {p}: {c} records")

    print("\n--- Churn Nature Distribution ---")
    for cn, c in sorted(churn_nature_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cn}: {c} records")

    return classified_records


if __name__ == "__main__":
    run_classifier()
