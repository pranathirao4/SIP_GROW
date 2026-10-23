"""
Stage E: Behavioral Mechanism & Causal Clustering Pipeline
Groups classified records into 13 behavioral root-cause clusters.
Calculates:
  - Exact record counts and prevalence percentage
  - Independent unique conversation counts (deduplicated by root thread)
  - Multi-source verbatims with verified URLs
  - Counterexamples (users who experienced the friction but continued their SIP)
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
        "theme_name": "Cash-Flow Volatility & Inflexible Fixed Commitments",
        "underlying_mechanism": "Rigid monthly fixed deduction dates penalize variable earners (freelancers, students, gig workers). When cash is tight, the all-or-nothing commitment causes complete stoppage rather than contribution reduction.",
        "patterns": [r"\bafford\b", r"\bcash\s*flow\b", r"\bno\s+money\b", r"\bpocket\s+money\b", r"\bstudent\b", r"\birregular\s+(?:income|salary)\b", r"\bfreelanc\b", r"\bvariable\s+salary\b"],
        "retention_link": "High. Liquidity crunches force immediate mandate pause or cancellation to prevent overdrafts."
    },
    {
        "theme_id": "THM-02",
        "theme_name": "Compounding Horizon Misalignment & Drawdown Panic",
        "underlying_mechanism": "First-time investors anchor mutual funds to guaranteed bank Fixed Deposits. Observing negative returns in months 3-6 triggers loss aversion and panic selling before rupee-cost averaging can compound.",
        "patterns": [r"\bmarket\s+(?:fall|crash|drop|correction|volatility)\b", r"\bnegative\s+(?:returns?|xirr)\b", r"\bred\b", r"\bpanic\b", r"\bloss\b", r"\bchecking\s+(?:returns?|portfolio)\s+daily\b"],
        "retention_link": "Very High. Month 3-6 drawdowns break investor confidence before compounding is understood."
    },
    {
        "theme_id": "THM-03",
        "theme_name": "Unrealistic Return Expectations vs Traditional FDs",
        "underlying_mechanism": "Disillusionment when 1-year mutual fund performance lags behind marketing hype or fails to drastically beat safe Fixed Deposits.",
        "patterns": [r"\bexpected\b", r"\bdisappoint\b", r"\bfd\s+(?:better|safe|gives)\b", r"\bunderperform\b", r"\bguaranteed\b"],
        "retention_link": "High. Users shift money back to traditional guaranteed savings (FD/RD)."
    },
    {
        "theme_id": "THM-04",
        "theme_name": "Confusion Over XIRR & Capital Accounting",
        "underlying_mechanism": "Inability to interpret annualized XIRR versus absolute returns, creating a false impression of catastrophic capital loss when NAV drops.",
        "patterns": [r"\bxirr\b", r"\bnav\b", r"\babsolute\s+return\b", r"\bcalculate\b", r"\bconfused\s+(?:returns?|xirr)\b", r"\bdifference\s+between\s+invested\b"],
        "retention_link": "Moderate. Psychological anxiety driven by confusing FinTech return metrics."
    },
    {
        "theme_id": "THM-05",
        "theme_name": "Low Perceived Progress on Micro-SIPs (Milestone Deficit)",
        "underlying_mechanism": "Small contributors (₹500-₹1,000) see negligible absolute growth in early quarters, feeling their contributions are insignificant.",
        "patterns": [r"\b500\s+(?:sip|per\s+month)\b", r"\bsmall\s+sip\b", r"\bworth\s+it\b", r"\bnot\s+growing\b", r"\bnegligible\b"],
        "retention_link": "Moderate. Lack of milestone celebration makes small contributors discontinue."
    },
    {
        "theme_id": "THM-06",
        "theme_name": "Foundational Compounding Literacy Gap",
        "underlying_mechanism": "Misunderstanding the 5-7 year horizon required for equity compounding; treating mutual funds like short-term trading bets.",
        "patterns": [r"\bcompounding\b", r"\bshort\s+term\b", r"\b1\s+year\s+enough\b", r"\bwithdraw\s+after\s+\d+\s+months\b", r"\b12\s+months\b", r"\bhabit\b"],
        "retention_link": "High. Early churn within 12 months caused by unrealistic short-term expectations."
    },
    {
        "theme_id": "THM-07",
        "theme_name": "Asymmetric Bank ECS / NACH Bounce Penalty Shield",
        "underlying_mechanism": "When delayed salary leaves bank account balance below SIP amount, the impending ₹450-₹590 bank penalty creates asymmetric loss. Users cancel mandates proactively in self-defense.",
        "patterns": [r"\bbounce\b", r"\bpenalty\b", r"\becs\s+charge\b", r"\brs\.?\s*4(?:00|50|72|90)\b", r"\bnach\s+charge\b", r"\bsalary\s+(?:date\s+)?mismatch\b", r"\bdebit\s+before\s+salary\b"],
        "retention_link": "Severe. Users cancel mandates explicitly to protect bank accounts from repeated penalty fees."
    },
    {
        "theme_id": "THM-08",
        "theme_name": "UPI Autopay & Mandate Technical Sync Failures",
        "underlying_mechanism": "Technical rejections of UPI Autopay, bank server timeouts, or pending deduction statuses lead investors to assume their SIP is cancelled or broken, causing accidental abandonment.",
        "patterns": [r"\bmandate\s+(?:fail|failed|reject|rejected|problem|issue|pending)\b", r"\bauto\s*pay\b", r"\bautopay\b", r"\bnpci\b", r"\bstatus\s+pending\b", r"\border\s+failed\b"],
        "retention_link": "High. Accidental churn where user intended to continue but gave up after technical friction."
    },
    {
        "theme_id": "THM-09",
        "theme_name": "UI Hierarchy Trap: Pause Invisibility vs Hard Cancellation",
        "underlying_mechanism": "Users facing temporary 1-3 month liquidity crunches default to hard cancellation because 'Cancel SIP' is prominent while 'Pause SIP' is buried or restricted.",
        "patterns": [r"\bpause\b", r"\bpaused\b", r"\bpausing\b", r"\bhow\s+to\s+pause\b", r"\bcancel\s+(?:or|vs|instead\s+of)\s+pause\b", r"\bskip\s+(?:month|instalment)?\b", r"\btemporar(?:y|ily)\s+stop\b"],
        "retention_link": "Direct Product Opportunity. High leverage for Groww UX."
    },
    {
        "theme_id": "THM-10",
        "theme_name": "Competing Fixed Commitments (EMIs, Rent & Debt)",
        "underlying_mechanism": "Cash diverted away from SIPs to service urgent non-discretionary liabilities like home/car loans, credit card debt, or rent.",
        "patterns": [r"\bemi\b", r"\bwedding\b", r"\bloan\b", r"\brent\b", r"\bfestival\b", r"\binsurance\b", r"\bcredit\s+card\s+debt\b"],
        "retention_link": "Moderate to High. Structural life stage priorities overriding discretionary investing."
    },
    {
        "theme_id": "THM-11",
        "theme_name": "Social Finfluencer Hype Regret & Conviction Deficit",
        "underlying_mechanism": "Starting SIPs based on peer pressure or social media hype without foundational understanding. At the first sign of difficulty, low conviction leads to rapid abandonment.",
        "patterns": [r"\binfluencer\b", r"\byoutube\b", r"\bfriend\s+(?:told|recommended|suggested)\b", r"\bregret\b", r"\bhype\b", r"\bfinfluencer\b"],
        "retention_link": "Moderate. Low initial conviction leads to rapid abandonment at first sign of trouble."
    },
    {
        "theme_id": "THM-12",
        "theme_name": "Processing Lag & Capital Safety Trust Erosion",
        "underlying_mechanism": "Money deducted from bank but mutual fund units not reflected in portfolio for days, causing panic and erosion of trust regarding capital safety.",
        "patterns": [r"\bunits\s+not\s+(?:allocated|credited|allotted)\b", r"\bdeducted\s+not\s+showing\b", r"\bsupport\b", r"\bticket\b", r"\bwrong\s+returns?\b", r"\bcomplaint\b"],
        "retention_link": "High. Trust erosion regarding safety of investor capital."
    },
    {
        "theme_id": "THM-13",
        "theme_name": "Emergency Reserve Depletion & Life Shocks",
        "underlying_mechanism": "Unplanned structural shocks (layoffs, medical emergencies) force liquidation of mutual funds to survive because no liquid emergency fund was built beforehand.",
        "patterns": [r"\bjob\s+loss\b", r"\blaid\s+off\b", r"\bunemployed\b", r"\bmedical\s+emergency\b", r"\bhospital\b", r"\bemergency\s+expense\b"],
        "retention_link": "Severe. Involuntary discontinuation due to existential survival needs."
    }
]


def cluster_records(records):
    """Cluster classified records by behavioral mechanism and calculate prevalence & unique conversation counts."""
    clusters = {
        t["theme_id"]: {
            **t,
            "matching_records": [],
            "unique_conversations": set(),
            "sources": set(),
            "verbatims": [],
            "counterexamples": []
        }
        for t in BASELINE_THEMES
    }

    for item in records:
        text = f"{item.get('title', '')} {item.get('raw_text', '')}".lower()
        rec_id = item.get("record_id")
        source = item.get("source", "unknown")
        root_url = item.get("classification", {}).get("root_conversation_url") or item.get("url") or "conv"
        quote = item.get("classification", {}).get("verbatim_quote") or item.get("title")

        # Check for counterexamples (e.g. continues despite obstacle)
        is_counterexample = bool(re.search(r"\b(?:continued|still\s+investing|did\s+not\s+stop|stayed\s+invested|restarted)\b", text))

        for t in BASELINE_THEMES:
            t_id = t["theme_id"]
            matched = any(re.search(pat, text) for pat in t["patterns"])
            if matched:
                clusters[t_id]["matching_records"].append(rec_id)
                clusters[t_id]["unique_conversations"].add(root_url)
                clusters[t_id]["sources"].add(source)
                if is_counterexample:
                    if len(clusters[t_id]["counterexamples"]) < 4:
                        clusters[t_id]["counterexamples"].append({
                            "record_id": rec_id,
                            "source": source,
                            "url": item.get("url"),
                            "quote": quote
                        })
                else:
                    if len(clusters[t_id]["verbatims"]) < 6:
                        clusters[t_id]["verbatims"].append({
                            "record_id": rec_id,
                            "source": source,
                            "url": item.get("url"),
                            "quote": quote
                        })

    # Prepare final clean structure
    final_clusters = []
    total_records = len(records)
    all_conversations = set(r.get("classification", {}).get("root_conversation_url") for r in records if r.get("classification", {}).get("root_conversation_url"))
    total_unique_convs = len(all_conversations) if all_conversations else total_records

    for t_id, data in clusters.items():
        count = len(data["matching_records"])
        conv_count = len(data["unique_conversations"])
        prevalence = round((count / total_records * 100), 1) if total_records > 0 else 0.0

        final_clusters.append({
            "theme_id": data["theme_id"],
            "theme_name": data["theme_name"],
            "underlying_mechanism": data["underlying_mechanism"],
            "record_count": count,
            "unique_conversations_count": conv_count,
            "total_records_denominator": total_records,
            "total_conversations_denominator": total_unique_convs,
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
    """Run Stage E behavioral mechanism clustering and produce output report."""
    print("=== Stage E: Behavioral Mechanism & Causal Clustering ===")

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

    print(f"\nSaved {len(clusters)} behavioral theme clusters to: {output_path}")

    print("\n--- Top Retention Themes Ranked by Prevalence ---")
    for cl in clusters[:7]:
        print(f"[{cl['theme_id']}] {cl['theme_name']}")
        print(f"  Prevalence: {cl['record_count']}/{cl['total_records_denominator']} records across {cl['unique_conversations_count']} unique conversations ({cl['prevalence_percentage']}%)")
        print(f"  Underlying Mechanism: {cl['underlying_mechanism'][:110]}...")
        if cl['representative_verbatims']:
            v = cl['representative_verbatims'][0]
            print(f"  Quote ({v['record_id']}): \"{v['quote'][:100]}...\"\n")

    return clusters


if __name__ == "__main__":
    run_clustering()
