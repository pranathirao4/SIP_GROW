"""
Enriched Dataset Builder & Classifier for Groww SIP Retention Project.
Consolidates all sources:
1. Google Play Store reviews for Groww (406 reviews)
2. Apple App Store reviews for Groww (338 reviews)
3. Apify Reddit scrape & historical deep Reddit batches
4. YouTube personal finance comments
5. TradingQ&A posts

Applies:
- Spam and promotional content filtering
- Deduplication by normalized text fingerprint
- Tagging into: PERSONAL_EXPERIENCE, QUESTION, ADVICE, NEWS_OR_MARKET, OFF_TOPIC
- Extraction of: action, reason, tenure, Groww specificity, age, income, source of money, influence
- Clean URL generation for citations
"""

import os
import sys
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# REGEX & CLASSIFICATION PATTERNS
# -------------------------------------------------------------------------

FIRST_PERSON_PATTERNS = [
    r"\bi\b", r"\bmy\b", r"\bme\b", r"\bmyself\b", r"\bi've\b", r"\bi'm\b", r"\bi'd\b",
    r"\bwe\b", r"\bour\b", r"\bmine\b"
]

ACTION_PATTERNS = {
    "stopped": [
        r"\bstop(?:ped|ping)?\b", r"\bcancel(?:led|ing|lation)?\b", r"\bdiscontinued\b",
        r"\bclose[d]?\b", r"\bquit\b", r"\bredeem(?:ed|ing)?\b", r"\bterminate[d]?\b"
    ],
    "paused": [
        r"\bpause[d]?\b", r"\bpausing\b", r"\bskip(?:ped|ping)?\b", r"\bhold\b", r"\bon hold\b"
    ],
    "reduced": [
        r"\breduc(?:ed|ing)\b", r"\bdecreas(?:ed|ing)\b", r"\blower(?:ed|ing)\b",
        r"\bcut down\b", r"\bsmaller amount\b", r"\bhalved\b"
    ],
    "started": [
        r"\bstart(?:ed|ing)?\b", r"\bbegan\b", r"\binitiat(?:ed|ing)\b", r"\bnew to sip\b",
        r"\bfirst sip\b", r"\bfirst time\b", r"\bcreated sip\b", r"\bjust started\b"
    ],
    "continued": [
        r"\bcontinu(?:ed|ing)\b", r"\bkept\b", r"\bmaintaining\b", r"\bholding\b",
        r"\bstill investing\b", r"\bnever stopped\b", r"\bsticking\b", r"\bdca\b"
    ]
}

REASON_PATTERNS = [
    ("AutoPay & Bank Bounce Penalty", [
        r"\bbounce\b", r"\bpenalty\b", r"\bpenalties\b", r"₹?\s*450", r"₹?\s*500", r"₹?\s*590",
        r"\bcharges?\b", r"\bdeducted\b", r"\bbank fee\b", r"\binsufficient balance\b"
    ]),
    ("Mandate & UPI Setup Failure", [
        r"\bmandate\b", r"\bautopay failed\b", r"\botm\b", r"\bnach\b", r"\bapproval pending\b",
        r"\bauthorization\b", r"\bsetup failed\b", r"\bbank rejected\b"
    ]),
    ("Salary Delay & Debit Date Mismatch", [
        r"\bsalary delay\b", r"\bsalary not credited\b", r"\b1st of month\b", r"\b5th of month\b",
        r"\bdebit date\b", r"\bbefore salary\b", r"\bcash crunch\b", r"\bmismatch\b"
    ]),
    ("Market Drawdown & Loss Anxiety", [
        r"\bloss\b", r"\blosses\b", r"\bnegative return\b", r"\bnegative xirr\b", r"\bred portfolio\b",
        r"\bfalling\b", r"\bcrash\b", r"\bmarket fall\b", r"\bpanic\b", r"\blosing money\b", r"\bdown \d+%\b"
    ]),
    ("Hidden Pause Button / Hard Cancel UX", [
        r"\bpause button\b", r"\bunable to pause\b", r"\bno pause option\b", r"\bcouldn't find pause\b",
        r"\bforced to cancel\b", r"\bhidden pause\b", r"\boptions not available\b"
    ]),
    ("Emergency Liquidity & Expense Shocks", [
        r"\bemergency\b", r"\bmedical\b", r"\bwedding\b", r"\brent\b", r"\bemi\b", r"\bloan\b",
        r"\bunexpected expense\b", r"\bjob loss\b", r"\blaid off\b", r"\bneeded money\b", r"\bneeded cash\b"
    ]),
    ("Finfluencer Hype & Unrealistic Expectations", [
        r"\bfinfluencer\b", r"\byoutube\b", r"\bhype\b", r"\bexpected 20%\b", r"\bdisappointed\b",
        r"\bregret\b", r"\bquick money\b", r"\bguaranteed return\b"
    ]),
    ("App Glitches & Support Frustration", [
        r"\bcustomer support\b", r"\bticket\b", r"\bno response\b", r"\bglitch\b", r"\bapp crashed\b",
        r"\bnot updating\b", r"\bwrong nav\b", r"\bdelay in allocation\b"
    ])
]

TENURE_PATTERNS = [
    ("Months 1-3", [r"\b(?:1|2|3|one|two|three)\s*months?\b", r"\bfirst month\b", r"\brecently started\b"]),
    ("Months 4-6", [r"\b(?:4|5|6|four|five|six)\s*months?\b", r"\bhalf a year\b"]),
    ("Months 7-12", [r"\b(?:7|8|9|10|11|12)\s*months?\b", r"\bfirst year\b", r"\bwithin a year\b", r"\b1\s*year\b"]),
    ("> 1 Year", [r"\b[2-9]\s*years?\b", r"\bseveral years\b", r"\blong term\b"])
]

AGE_PATTERNS = [
    ("College / Student", [r"\bcollege\b", r"\bstudent\b", r"\buniversity\b", r"\bstudying\b"]),
    ("Early Career (20-25)", [r"\b2[0-5]\s*(?:yo|y\/o|years old)\b", r"\bfirst job\b", r"\bfresh graduate\b"]),
    ("Young Professional (26-32)", [r"\b(?:2[6-9]|3[0-2])\s*(?:yo|y\/o|years old)\b"]),
    ("Family / Senior (35+)", [r"\b(?:3[5-9]|[4-6]\d)\s*(?:yo|y\/o|years old)\b", r"\bmarried\b", r"\bkids\b", r"\bchildren\b"])
]

INCOME_PATTERNS = [
    ("Salary Delay / Tight Cashflow", [r"\bsalary delayed\b", r"\blate salary\b", r"\bpaycheck to paycheck\b", r"\btight budget\b"]),
    ("Irregular / Freelance", [r"\bfreelance\b", r"\birregular income\b", r"\bvariable income\b", r"\bbusiness loss\b"]),
    ("Burdened by EMIs & Rent", [r"\bemi\b", r"\brent\b", r"\bloan payment\b", r"\bhome loan\b"]),
    ("Stable Salaried", [r"\blpa\b", r"\bsalaried\b", r"\bcorporate\b", r"\bmonthly salary\b"])
]

INFLUENCE_PATTERNS = [
    ("Finfluencer / Social Media", [r"\bfinfluencer\b", r"\byoutube\b", r"\binstagram\b", r"\breel\b", r"\btwitter\b"]),
    ("Friends / Colleagues", [r"\bfriend\b", r"\bfriends\b", r"\bcolleague\b", r"\bcolleagues\b", r"\boffice\b", r"\bpeer\b"]),
    ("Parents / Family", [r"\bfather\b", r"\bparents\b", r"\bfamily\b", r"\brelative\b"]),
    ("Self-Research / In-App Ad", [r"\bself\b", r"\bad\b", r"\bgroww ad\b", r"\btelevision\b"])
]

SPAM_KEYWORDS = [
    "join telegram", "t.me/", "whatsapp", "call me for tips", "guaranteed profit",
    "dm for calls", "crypto pump", "binance", "free demat account open link"
]


def is_spam_or_promo(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in SPAM_KEYWORDS) or len(text.strip()) < 15


def clean_text_hash(text: str) -> str:
    cleaned = re.sub(r'\s+', ' ', text.lower()).strip()
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()


def tag_item(text: str, source: str) -> str:
    """
    Tags every item as exactly ONE of:
    PERSONAL_EXPERIENCE, QUESTION, ADVICE, NEWS_OR_MARKET, OFF_TOPIC
    """
    t_lower = text.lower()
    src_lower = source.lower()

    # Off-topic check (crypto, intraday, unrelated)
    if any(ot in t_lower for ot in ["bitcoin", "ethereum", "crypto", "option buying", "nifty expiry hero zero", "cricket"]):
        if "sip" not in t_lower and "mutual fund" not in t_lower:
            return "OFF_TOPIC"

    # App reviews (Play Store, App Store) are almost always direct personal accounts
    if "play_store" in src_lower or "app_store" in src_lower:
        return "PERSONAL_EXPERIENCE"

    # Check for student research survey posts
    if "research" in t_lower and any(w in t_lower for w in ["survey", "thesis", "google form", "fill this form"]):
        return "OFF_TOPIC"

    # Macro News
    if any(n in t_lower for n in ["fii inflow", "fii outflow", "rbi repo rate", "sensex crosses", "nifty hits all-time", "gdp growth india"]):
        if not any(re.search(p, t_lower) for p in FIRST_PERSON_PATTERNS):
            return "NEWS_OR_MARKET"

    # Personal decision questions (e.g. "should I stop my SIP?", "my portfolio is -8%, what should I do?")
    if any(re.search(p, t_lower) for p in FIRST_PERSON_PATTERNS):
        if any(w in t_lower for w in ["should i stop", "should i cancel", "should i pause", "my sip is in loss", "i am losing", "my autopay"]):
            return "PERSONAL_EXPERIENCE"

        # Check if first person discusses an action
        has_action = False
        for act, patterns in ACTION_PATTERNS.items():
            if any(re.search(p, t_lower) for p in patterns):
                has_action = True
                break
        if has_action:
            return "PERSONAL_EXPERIENCE"

    # Generic Advice / Educational Guides
    if any(w in t_lower for w in ["rule of 72", "steps to invest", "why you should never", "compounding secret", "guide for beginners"]):
        return "ADVICE"

    # Generic Questions
    if "?" in text or any(t_lower.startswith(q) for q in ["what is", "how does", "is it safe", "can someone", "where can i"]):
        return "QUESTION"

    # General Advice / Opinions default
    if any(kw in t_lower for kw in ["sip", "mutual fund", "groww"]):
        return "ADVICE"

    return "OFF_TOPIC"


def extract_attributes(text: str, source: str) -> dict:
    """Extract action, reason, tenure, groww mention, and demographic signals."""
    t_lower = text.lower()
    src_lower = source.lower()

    # 1. Action
    action = "continued"
    for act, patterns in ACTION_PATTERNS.items():
        if any(re.search(p, t_lower) for p in patterns):
            action = act
            break

    # 2. Reason
    reasons = []
    for r_name, patterns in REASON_PATTERNS:
        if any(re.search(p, t_lower) for p in patterns):
            reasons.append(r_name)
    primary_reason = reasons[0] if reasons else "General portfolio rebalancing / Unspecified"

    # 3. Tenure
    tenure = "Not mentioned"
    for t_name, patterns in TENURE_PATTERNS:
        if any(re.search(p, t_lower) for p in patterns):
            tenure = t_name
            break

    # 4. Groww specificity
    is_groww = "groww" in t_lower or "play_store" in src_lower or "app_store" in src_lower

    # 5. Age
    age = "Not mentioned"
    for a_name, patterns in AGE_PATTERNS:
        if any(re.search(p, t_lower) for p in patterns):
            age = a_name
            break

    # 6. Income
    income = "Not mentioned"
    for i_name, patterns in INCOME_PATTERNS:
        if any(re.search(p, t_lower) for p in patterns):
            income = i_name
            break

    # 7. Influence
    influence = "Not mentioned"
    for inf_name, patterns in INFLUENCE_PATTERNS:
        if any(re.search(p, t_lower) for p in patterns):
            influence = inf_name
            break

    # 8. Verbatim quote
    # Pick a concise sentence from the text
    sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s.strip()) > 20]
    quote = sentences[0] if sentences else text[:150]

    return {
        "observable_behaviour": f"Action: {action.title()} SIP",
        "action": action,
        "trigger_context": primary_reason,
        "underlying_problem": primary_reason,
        "tenure_stage": tenure,
        "is_groww": is_groww,
        "age_signal": age,
        "income_signal": income,
        "influence_signal": influence,
        "verbatim_quote": quote[:250]
    }


def build_dataset():
    print("=" * 60)
    print("STEP 3: CONSOLIDATING, CLEANING, AND TAGGING ALL DATASETS")
    print("=" * 60)

    raw_candidates = []

    # 1. Newly collected gap records (Google Play 406 + iOS 338)
    gap_file = RAW_DIR / "gap_collected_raw.json"
    if gap_file.exists():
        with open(gap_file, "r", encoding="utf-8") as f:
            items = json.load(f)
            raw_candidates.extend(items)
            print(f"Loaded {len(items)} items from gap_collected_raw.json")

    # 2. Existing raw files
    raw_files = [
        "reddit_batches_deep.json",
        "reddit_comprehensive.json",
        "reddit_pilot.json",
        "tradingqna.json",
        "tradingqna_expanded.json",
        "tradingqna_groww.json",
        "youtube_comments_expanded.json"
    ]

    for rf in raw_files:
        p = RAW_DIR / rf
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                items = json.load(f)
                raw_candidates.extend(items)
                print(f"Loaded {len(items)} items from {rf}")

    # 3. Existing cleaned records as fallback
    cleaned_file = PROCESSED_DIR / "cleaned_records.json"
    if cleaned_file.exists():
        with open(cleaned_file, "r", encoding="utf-8") as f:
            items = json.load(f)
            raw_candidates.extend(items)
            print(f"Loaded {len(items)} items from existing cleaned_records.json")

    print(f"\nTotal raw items before deduplication: {len(raw_candidates)}")

    # Deduplicate & Filter Spam
    seen_hashes = set()
    cleaned_records = []
    classified_records = []

    counts_by_tag = {
        "PERSONAL_EXPERIENCE": 0,
        "QUESTION": 0,
        "ADVICE": 0,
        "NEWS_OR_MARKET": 0,
        "OFF_TOPIC": 0
    }

    action_counts = {}
    groww_counts = 0
    tenure_counts = {}

    idx = 1
    for item in raw_candidates:
        text = (item.get("raw_text") or item.get("content") or item.get("body") or "").strip()
        title = (item.get("title") or "").strip()
        full_text = f"{title}. {text}" if title and title not in text else text

        if is_spam_or_promo(full_text):
            continue

        h = clean_text_hash(full_text)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        source = item.get("source", "reddit")
        url = item.get("url") or "#"
        published_at = (item.get("published_at") or item.get("created_at") or "2024-02-15")[:10]

        # Tag
        tag = tag_item(full_text, source)
        counts_by_tag[tag] += 1

        rec_id = f"REC-{idx:05d}"
        idx += 1

        # Extract attributes
        attrs = extract_attributes(full_text, source)
        if attrs["is_groww"]:
            groww_counts += 1
        act = attrs["action"]
        action_counts[act] = action_counts.get(act, 0) + 1
        ten = attrs["tenure_stage"]
        tenure_counts[ten] = tenure_counts.get(ten, 0) + 1

        standard_record = {
            "record_id": rec_id,
            "source": source,
            "title": title[:100] if title else f"Investor Review ({source})",
            "raw_text": full_text,
            "url": url,
            "published_at": published_at,
            "primary_tag": tag,
            "relevance_tier": "Tier 1: Directly Relevant" if tag == "PERSONAL_EXPERIENCE" else "Tier 2: Contextual",
            "classification": {
                "primary_intent": tag,
                "observable_behaviour": attrs["observable_behaviour"],
                "trigger_context": attrs["trigger_context"],
                "underlying_problem": attrs["underlying_problem"],
                "tenure_stage": attrs["tenure_stage"],
                "is_groww": attrs["is_groww"],
                "age_signal": attrs["age_signal"],
                "income_signal": attrs["income_signal"],
                "influence_signal": attrs["influence_signal"],
                "verbatim_quote": attrs["verbatim_quote"]
            }
        }

        cleaned_records.append(standard_record)

        # Classified record for classification map
        classified_records.append({
            "record_id": rec_id,
            "root_conversation_url": url,
            "classification": standard_record["classification"]
        })

    # Save to data/processed
    with open(PROCESSED_DIR / "cleaned_records.json", "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)

    with open(PROCESSED_DIR / "classified_records.json", "w", encoding="utf-8") as f:
        json.dump(classified_records, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully wrote {len(cleaned_records)} cleaned records to {PROCESSED_DIR / 'cleaned_records.json'}")
    print(f"Successfully wrote {len(classified_records)} classified records to {PROCESSED_DIR / 'classified_records.json'}")

    print("\n--- Summary of Tagged Records ---")
    for tag, c in counts_by_tag.items():
        print(f"  {tag}: {c} ({c/len(cleaned_records)*100:.1f}%)")

    print(f"\nTotal USABLE Evidence Records (PERSONAL_EXPERIENCE): {counts_by_tag['PERSONAL_EXPERIENCE']}")
    print(f"Total GROWW-specific records: {groww_counts}")
    print("\nActions Breakdown:")
    for a, c in action_counts.items():
        print(f"  {a}: {c}")

    return cleaned_records

if __name__ == "__main__":
    build_dataset()
