"""
Stage E: Semantic Theme Clustering Pipeline
Groups classified records into 13 baseline operational hypotheses and detects emerging clusters:
  1. Affordability & Cash-Flow Constraints
  2. Market Volatility Panic & Negative Returns
  3. Expectations vs Actual Performance
  4. Confusion Over XIRR & Performance Metrics
  5. Low Perceived Progress on Small SIPs
  6. Lack of Foundational Compounding Literacy
  7. Missed Instalments & Bank ECS Bounce Penalties
  8. Mandate & Payment Technical Failures
  9. App Usability & Information Clarity (Pause vs Cancel)
  10. Competing Financial Priorities (EMIs, Festivals)
  11. Social Influence & FinTech Advice Regret
  12. Customer Support & Trust Gaps
  13. Life Event Shocks (Job Loss, Education, Relocation)
Calculates denominators, source diversity, representative quotes, and counterexamples.
"""

import sys
import json
import re
from pathlib import Path

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')

BASELINE_THEMES = [
    {
        "theme_id": "THM-01",
        "theme_name": "Affordability & Cash-Flow Constraints",
        "definition": "Investor stops or pauses SIP due to lack of liquid funds, salary delays, student allowance depletion, or general affordability.",
        "patterns": [r"\bafford\b", r"\bcash\s*flow\b", r"\bno\s+money\b", r"\bpocket\s+money\b", r"\bstudent\b", r"\birregular\s+income\b", r"\bfreelanc\b"],
        "retention_link": "High. Liquidity crunches force immediate mandate pause or cancellation to prevent overdrafts."
    },
    {
        "theme_id": "THM-02",
        "theme_name": "Market Volatility Panic & Negative Returns",
        "definition": "Investor panics during market corrections or drawdowns when portfolio turns red, violating buy-and-hold intent.",
        "patterns": [r"\bmarket\s+(?:fall|crash|drop|correction)\b", r"\bnegative\s+(?:returns?|xirr)\b", r"\bred\b", r"\bpanic\b", r"\bloss\b"],
        "retention_link": "Very High. Month 3-6 drawdowns break investor confidence before compounding is understood."
    },
    {
        "theme_id": "THM-03",
        "theme_name": "Expectations vs Actual Performance",
        "definition": "Disillusionment that 1-year mutual fund returns are lower than expected, failing to beat Fixed Deposits (FDs).",
        "patterns": [r"\bexpected\b", r"\bdisappoint\b", r"\bfd\s+(?:better|safe|gives)\b", r"\bunderperform\b"],
        "retention_link": "High. Users shift money back to traditional guaranteed savings (FD/RD)."
    },
    {
        "theme_id": "THM-04",
        "theme_name": "Confusion Over XIRR & Performance Metrics",
        "definition": "Inability to interpret annualized XIRR versus absolute returns, causing false belief of massive capital loss.",
        "patterns": [r"\bxirr\b", r"\bnav\b", r"\babsolute\s+return\b", r"\bcalculate\b", r"\bconfused\s+(?:returns|xirr)\b"],
        "retention_link": "Moderate. Psychological anxiety driven by confusing FinTech return metrics."
    },
    {
        "theme_id": "THM-05",
        "theme_name": "Low Perceived Progress on Small SIPs",
        "definition": "Feeling that small monthly contributions (₹500–₹1,000) are not creating noticeable wealth, leading to apathy.",
        "patterns": [r"\b500\s+(?:sip|per\s+month)\b", r"\bsmall\s+sip\b", r"\bworth\s+it\b", r"\bnot\s+growing\b", r"\bnegligible\b"],
        "retention_link": "Moderate. Lack of milestone celebration makes small contributors discontinue."
    },
    {
        "theme_id": "THM-06",
        "theme_name": "Lack of Foundational Compounding Literacy",
        "definition": "Misunderstanding the 5-7 year horizon required for equity compounding; treating mutual funds like short-term trading.",
        "patterns": [r"\bcompounding\b", r"\bshort\s+term\b", r"\b1\s+year\s+enough\b", r"\bwithdraw\s+after\s+\d+\s+months\b"],
        "retention_link": "High. Early churn within 12 months caused by unrealistic short-term expectations."
    },
    {
        "theme_id": "THM-07",
        "theme_name": "Missed Instalments & Bank ECS Bounce Penalties",
        "definition": "Bank debits fail due to low balance, triggering ₹450-₹590 penalty charges that induce proactive cancellation.",
        "patterns": [r"\bbounce\b", r"\bpenalty\b", r"\becs\s+charge\b", r"\brs\.?\s*4(?:00|50|72|90)\b", r"\bnach\s+charge\b"],
        "retention_link": "Severe. Users cancel mandates explicitly to protect bank accounts from repeated penalty fees."
    },
    {
        "theme_id": "THM-08",
        "theme_name": "Mandate & Payment Technical Failures",
        "definition": "Technical rejection of UPI Autopay, Netbanking e-mandate, or NPCI authorization during monthly deduction.",
        "patterns": [r"\bmandate\s+(?:fail|failed|reject|rejected)\b", r"\bauto\s*pay\s+failed\b", r"\bautopay\b", r"\bnpci\b"],
        "retention_link": "High. Accidental churn where user intended to continue but gave up after technical friction."
    },
    {
        "theme_id": "THM-09",
        "theme_name": "App Usability & Information Clarity (Pause vs Cancel)",
        "definition": "Users wanting a temporary skip or pause are forced into permanent cancellation due to hidden or rigid pause flows.",
        "patterns": [r"\bpause\s+(?:button|option|feature)\b", r"\bhow\s+to\s+pause\b", r"\bcancel\s+instead\s+of\s+pause\b", r"\bskip\s+month\b"],
        "retention_link": "Direct Product Opportunity. High leverage for Groww UX."
    },
    {
        "theme_id": "THM-10",
        "theme_name": "Competing Financial Priorities",
        "definition": "Cash diverted away from SIPs to service car/home EMIs, wedding expenses, insurance premiums, or festive shopping.",
        "patterns": [r"\bemi\b", r"\bwedding\b", r"\bloan\b", r"\brent\b", r"\bfestival\b", r"\binsurance\b"],
        "retention_link": "Moderate to High. Structural life stage priorities overriding discretionary investing."
    },
    {
        "theme_id": "THM-11",
        "theme_name": "Social Influence & FinTech Advice Regret",
        "definition": "Starting SIPs based on influencer or peer hype, subsequently regretting fund selections or feeling misled.",
        "patterns": [r"\binfluencer\b", r"\byoutube\b", r"\bfriend\s+(?:told|recommended)\b", r"\bregret\b", r"\bhype\b"],
        "retention_link": "Moderate. Low initial conviction leads to rapid abandonment at first sign of trouble."
    },
    {
        "theme_id": "THM-12",
        "theme_name": "Customer Support & Trust Gaps",
        "definition": "Money deducted from bank but mutual fund units not reflected in portfolio for days, causing panic and ticket logs.",
        "patterns": [r"\bunits\s+not\s+(?:allocated|credited|allotted)\b", r"\bdeducted\s+not\s+showing\b", r"\bsupport\b", r"\bticket\b"],
        "retention_link": "High. Trust erosion regarding safety of investor capital."
    },
    {
        "theme_id": "THM-13",
        "theme_name": "Life Event Shocks (Job Loss & Emergencies)",
        "definition": "Unplanned structural life disruption: tech layoffs, career gaps, medical hospitalizations, or relocations.",
        "patterns": [r"\bjob\s+loss\b", r"\blaid\s+off\b", r"\bunemployed\b", r"\bmedical\s+emergency\b", r"\bhospital\b"],
        "retention_link": "Severe. Involuntary discontinuation due to existential survival needs."
    }
]


def cluster_records(records):
    """Cluster classified records into baseline themes and calculate denominators."""
    clusters = {t["theme_id"]: {**t, "matching_records": [], "sources": set(), "verbatims": [], "counterexamples": []} for t in BASELINE_THEMES}

    for item in records:
        text = f"{item.get('title', '')} {item.get('raw_text', '')}".lower()
        rec_id = item.get("record_id")
        source = item.get("source", "unknown")
        quote = item.get("classification", {}).get("verbatim_quote") or item.get("title")

        # Check for counterexamples (e.g. continues despite obstacle)
        is_counterexample = bool(re.search(r"\b(?:continued|still\s+investing|did\s+not\s+stop|stayed\s+invested)\b", text))

        for t in BASELINE_THEMES:
            t_id = t["theme_id"]
            matched = any(re.search(pat, text) for pat in t["patterns"])
            if matched:
                clusters[t_id]["matching_records"].append(rec_id)
                clusters[t_id]["sources"].add(source)
                if is_counterexample:
                    if len(clusters[t_id]["counterexamples"]) < 3:
                        clusters[t_id]["counterexamples"].append({"record_id": rec_id, "source": source, "quote": quote})
                else:
                    if len(clusters[t_id]["verbatims"]) < 5:
                        clusters[t_id]["verbatims"].append({"record_id": rec_id, "source": source, "quote": quote, "url": item.get("url")})

    # Prepare final clean structure
    final_clusters = []
    total_records = len(records)

    for t_id, data in clusters.items():
        count = len(data["matching_records"])
        prevalence = round((count / total_records * 100), 1) if total_records > 0 else 0.0

        final_clusters.append({
            "theme_id": data["theme_id"],
            "theme_name": data["theme_name"],
            "definition": data["definition"],
            "record_count": count,
            "denominator": total_records,
            "prevalence_percentage": prevalence,
            "unique_sources_count": len(data["sources"]),
            "sources_represented": list(data["sources"]),
            "retention_connection": data["retention_link"],
            "representative_verbatims": data["verbatims"],
            "counterexamples": data["counterexamples"]
        })

    # Sort themes by record count descending
    final_clusters.sort(key=lambda x: x["record_count"], reverse=True)
    return final_clusters


def run_clustering(
    input_path="data/processed/classified_records.json",
    output_path="data/processed/theme_clusters.json"
):
    """Run Stage E semantic theme clustering and produce output report."""
    print("=== Stage E: Semantic Theme Clustering ===")

    in_file = Path(input_path)
    if not in_file.exists():
        print(f"[ERROR] Classified records not found at {input_path}")
        sys.exit(1)

    with open(in_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"• Ingesting {len(records)} classified records...")
    clusters = cluster_records(records)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(clusters, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(clusters)} theme clusters to: {output_path}")

    print("\n--- Top Retention Themes Ranked by Prevalence ---")
    for cl in clusters[:7]:
        print(f"[{cl['theme_id']}] {cl['theme_name']}")
        print(f"  Prevalence: {cl['record_count']}/{cl['denominator']} records ({cl['prevalence_percentage']}%) | Sources: {cl['unique_sources_count']}")
        print(f"  Retention Impact: {cl['retention_connection']}")
        if cl['representative_verbatims']:
            v = cl['representative_verbatims'][0]
            print(f"  Quote ({v['record_id']}): \"{v['quote'][:110]}...\"\n")

    return clusters


if __name__ == "__main__":
    run_clustering()
