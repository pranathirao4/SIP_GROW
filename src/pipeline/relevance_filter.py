"""
Stage C: 5-Tier Relevance Filtering & Human Review Queue
Evaluates cleaned records against operational relevance tiers:
  Tier 1: Directly Relevant (Stopping, pausing, cancelling, reducing SIPs)
  Tier 2: Indirectly Relevant (Beginner psychology, negative XIRR disillusionment, anxiety)
  Tier 3: In-App & Mandate Friction (Auto-pay failures, bounce penalties, UI traps)
  Tier 4: General Investing (No retention connection)
  Tier 5: Noise / Spam / Unusable
Routes borderline records (confidence 0.40 - 0.60) to the Review Queue.
"""

import sys
import json
import re
from pathlib import Path

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')

TIER_PATTERNS = {
    "Tier 1: Directly Relevant": [
        r"\b(?:stop|stopped|stopping|cancel|cancelled|cancelling|pause|paused|pausing|discontinue|discontinued|reduce|reduced|skip|skipped)\s+(?:\w+\s+){0,4}(?:sips?|instalments?|investments?)\b",
        r"\bsips?\s+(?:\w+\s+){0,3}(?:cancellation|cancelled|cancel|cancelling|stopped|stop|stopping|paused|pause|pausing|discontinue|bounce|failed|failure|rejection)\b",
        r"\b(?:should\s+i|how\s+to|planning\s+to)\s+(?:stop|pause|cancel)\s+(?:my\s+)?sip\b",
        r"\bmissed\s+(?:an?\s+)?(?:sip|instalment|payment|debit)\b",
        r"\bfailed\s+(?:sip|instalment|debit|auto-?debit)\b",
        r"\bpause\s+vs\s+cancel\b",
        r"\bamc\s+sip\b",
        r"\bquit\s+(?:the\s+)?(?:step-?up\s+)?sip\b"
    ],
    "Tier 2: Indirectly Relevant": [
        r"\bfirst\s+time\s+(?:sip|investor|investment)\b",
        r"\bbeginner\s+(?:investor|mistake|mutual\s+fund|sip)\b",
        r"\bnegative\s+(?:returns?|xirr)\b",
        r"\bportfolio\s+in\s+red\b",
        r"\bdisappointing\s+returns?\b",
        r"\bmarket\s+(?:fall|crash|drop|correction)\b",
        r"\bpanic\b",
        r"\banxiety\b",
        r"\bregret\b",
        r"\bstudents?\b",
        r"\bpocket\s+money\b",
        r"\birregular\s+income\b",
        r"\bfreelanc(?:e|er|ing)\b",
        r"\bjob\s+loss\b",
        r"\blaid\s+off\b",
        r"\bemergency\s+fund\b",
        r"\baffordability\b",
        r"\bcannot\s+afford\b",
        r"\bno\s+money\b",
        r"\bcollege\s+fees\b",
        r"\bfinancial\s+crisis\b"
    ],
    "Tier 3: In-App & Mandate Friction": [
        r"\bauto\s*pay\b",
        r"\be-?mandate\b",
        r"\bmandates?\s+(?:fail|failed|reject|rejected|problem|issue|pending)\b",
        r"\bbank\s+(?:bounce|penalty|ecs|nach)\s+charges?\b",
        r"\brs\.?\s*4(?:00|50|72|90)\b",
        r"\bunits\s+not\s+(?:allocated|credited|allotted)\b",
        r"\bmoney\s+deducted\b",
        r"\bpause\s+(?:button|option|feature)\b",
        r"\bhow\s+to\s+pause\b",
        r"\bgroww\s+(?:app|issue|bug|problem|service)\b",
        r"\bpayment\s+failed\b"
    ]
}


def score_record_relevance(record):
    """Compute relevance tier, score, confidence, and human review flag."""
    text = f"{record.get('title', '')} {record.get('raw_text', '')}".lower()

    tier_matches = {tier: 0 for tier in TIER_PATTERNS}
    matched_phrases = []

    for tier, patterns in TIER_PATTERNS.items():
        for pat in patterns:
            found = re.findall(pat, text)
            if found:
                tier_matches[tier] += len(found)
                matched_phrases.extend(found)

    # Calculate scores
    t1 = tier_matches["Tier 1: Directly Relevant"]
    t2 = tier_matches["Tier 2: Indirectly Relevant"]
    t3 = tier_matches["Tier 3: In-App & Mandate Friction"]

    assigned_tier = "Tier 5: Noise / Spam"
    score = 0.1
    confidence = 0.5
    rationale = "No strong retention or SIP discontinuation keywords found."

    if t1 > 0:
        assigned_tier = "Tier 1: Directly Relevant"
        score = min(0.85 + (t1 * 0.05), 1.0)
        confidence = 0.90
        rationale = f"Explicitly mentions stopping, cancelling, or pausing SIP ({t1} occurrences)."
    elif t3 > 0:
        assigned_tier = "Tier 3: In-App & Mandate Friction"
        score = min(0.70 + (t3 * 0.05), 0.95)
        confidence = 0.85
        rationale = f"Mentions auto-pay, e-mandates, bank bounce charges, or app friction ({t3} occurrences)."
    elif t2 > 0:
        assigned_tier = "Tier 2: Indirectly Relevant"
        score = min(0.55 + (t2 * 0.05), 0.85)
        confidence = 0.75
        rationale = f"Mentions beginner psychology, student/irregular income, or volatility shock ({t2} occurrences)."
    else:
        # Check if mention general mutual fund words without retention link
        if "sip" in text or "mutual fund" in text or "portfolio" in text:
            assigned_tier = "Tier 4: General Investing"
            score = 0.35
            confidence = 0.70
            rationale = "General investing conversation with no clear retention or drop-off link."

    # Borderline review flag
    review_required = (0.40 <= score <= 0.60) or (t1 == 0 and t2 == 1 and t3 == 0)

    return {
        "tier": assigned_tier,
        "score": round(score, 2),
        "confidence": round(confidence, 2),
        "rationale": rationale,
        "matched_keywords": list(set(matched_phrases))[:6],
        "human_review_required": review_required
    }


def run_relevance_filter(
    input_path="data/processed/cleaned_records.json",
    relevant_output="data/processed/relevant_records.json",
    review_output="data/processed/review_queue.json"
):
    """Classify records and separate relevant records from review queue and noise."""
    print("=== Stage C: 5-Tier Relevance Filtering ===")

    in_file = Path(input_path)
    if not in_file.exists():
        print(f"[ERROR] Cleaned dataset not found at {input_path}")
        sys.exit(1)

    with open(in_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"• Ingesting {len(records)} cleaned records...")

    relevant_records = []
    review_queue = []
    tier_counts = {}

    for item in records:
        rel = score_record_relevance(item)
        item["relevance"] = rel

        tier = rel["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        if rel["human_review_required"]:
            review_queue.append({
                "record_id": item["record_id"],
                "source": item["source"],
                "url": item["url"],
                "title": item["title"],
                "snippet": item["raw_text"][:200] if item["raw_text"] else item["title"],
                "tier": rel["tier"],
                "score": rel["score"],
                "confidence": rel["confidence"],
                "rationale": rel["rationale"],
                "matched_keywords": rel["matched_keywords"]
            })

        # Keep Tiers 1, 2, and 3 as relevant for downstream analysis
        if tier in ["Tier 1: Directly Relevant", "Tier 2: Indirectly Relevant", "Tier 3: In-App & Mandate Friction"]:
            relevant_records.append(item)

    # Save relevant records
    out_rel = Path(relevant_output)
    out_rel.parent.mkdir(parents=True, exist_ok=True)
    with open(out_rel, "w", encoding="utf-8") as f:
        json.dump(relevant_records, f, indent=2, ensure_ascii=False)

    # Save review queue
    out_rev = Path(review_output)
    with open(out_rev, "w", encoding="utf-8") as f:
        json.dump(review_queue, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(relevant_records)} relevant records to: {relevant_output}")
    print(f"Saved {len(review_queue)} borderline records to Review Queue: {review_output}")

    print("\n--- Relevance Tier Breakdown ---")
    for t, c in sorted(tier_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {t}: {c} records")

    return relevant_records, review_queue


if __name__ == "__main__":
    run_relevance_filter()
