"""
Stage B: Data Cleaning & Deduplication Pipeline
Unifies records from Reddit, TradingQ&A, and App Reviews.
Performs text normalization, hash-based deduplication, and cross-post detection.
"""

import sys
import json
import re
import hashlib
from pathlib import Path

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')


def normalize_text(text: str) -> str:
    """Normalize whitespace, encoding artifacts, and linebreaks without altering meaning."""
    if not text:
        return ""
    # Replace non-breaking spaces and zero-width spaces
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    # Normalize common smart quotes and dashes
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = text.replace("—", "-").replace("–", "-")
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple inline spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def compute_hash(text: str) -> str:
    """Generate MD5 hash of normalized lowercase text for exact duplicate detection."""
    clean_sample = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    return hashlib.md5(clean_sample.encode('utf-8')).hexdigest()


def run_cleaner(
    reddit_path="data/raw/reddit_pilot.json",
    reddit_ext_path="data/raw/reddit_comprehensive.json",
    tradingqna_path="data/raw/tradingqna.json",
    reviews_path="data/raw/app_reviews.json",
    output_path="data/processed/cleaned_records.json"
):
    """Run full cleaning and deduplication across all available raw sources."""
    print("=== Stage B: Data Cleaning & Deduplication ===")

    raw_records = []

    # 1. Load Reddit pilot records
    r_file = Path(reddit_path)
    if r_file.exists():
        with open(r_file, "r", encoding="utf-8") as f:
            r_data = json.load(f)
            print(f"• Loaded {len(r_data)} records from {reddit_path}")
            raw_records.extend(r_data)
    else:
        print(f"• [INFO] {reddit_path} not found yet (will include once collected).")

    # 1b. Load Reddit extended scenario records
    r_ext_file = Path(reddit_ext_path)
    if r_ext_file.exists():
        with open(r_ext_file, "r", encoding="utf-8") as f:
            r_ext_data = json.load(f)
            print(f"• Loaded {len(r_ext_data)} records from {reddit_ext_path}")
            raw_records.extend(r_ext_data)

    # 2. Load TradingQ&A records
    t_file = Path(tradingqna_path)
    if t_file.exists():
        with open(t_file, "r", encoding="utf-8") as f:
            t_data = json.load(f)
            print(f"• Loaded {len(t_data)} records from {tradingqna_path}")
            raw_records.extend(t_data)

    # 3. Load App Reviews
    rev_file = Path(reviews_path)
    if rev_file.exists():
        with open(rev_file, "r", encoding="utf-8") as f:
            rev_data = json.load(f)
            print(f"• Loaded {len(rev_data)} records from {reviews_path}")
            raw_records.extend(rev_data)

    print(f"\nTotal raw inputs to process: {len(raw_records)} records")

    seen_hashes = {}
    cleaned_records = []
    duplicate_count = 0
    empty_count = 0
    source_breakdown = {}

    for item in raw_records:
        title = normalize_text(item.get("title", ""))
        raw_text = normalize_text(item.get("raw_text", ""))

        # Combined text representation for analysis
        combined_text = f"{title}\n\n{raw_text}".strip() if title else raw_text

        # Filter out empty records
        if not combined_text or len(combined_text) < 15:
            empty_count += 1
            continue

        # Check for duplicates using title + body hash
        content_hash = compute_hash(combined_text)
        if content_hash in seen_hashes:
            duplicate_count += 1
            continue

        seen_hashes[content_hash] = item.get("record_id")

        rec_num = len(cleaned_records) + 1
        system_id = f"REC-{rec_num:05d}"
        source = item.get("source", "unknown")
        source_breakdown[source] = source_breakdown.get(source, 0) + 1

        cleaned_records.append({
            "record_id": system_id,
            "original_id": item.get("record_id"),
            "source": source,
            "url": item.get("url", ""),
            "title": title,
            "raw_text": raw_text,
            "combined_text": combined_text,
            "author": item.get("author", "anonymous"),
            "published_at": item.get("published_at"),
            "upvotes_or_likes": item.get("upvotes") or item.get("like_count") or item.get("thumbs_up") or 0,
            "comments_or_replies": item.get("comment_count") or item.get("posts_count") or 0,
            "dedup_hash": content_hash
        })

    # Save cleaned output
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)

    print("\n--- Cleaning & Deduplication Summary ---")
    print(f"• Total Raw Ingested: {len(raw_records)}")
    print(f"• Empty/Short Records Removed: {empty_count}")
    print(f"• Exact/Near Duplicates Removed: {duplicate_count}")
    print(f"• Cleaned Unique Records Produced: {len(cleaned_records)}")
    print(f"• Saved To: {output_path}")

    print("\n--- Source Breakdown ---")
    for s, c in sorted(source_breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {s}: {c} records")

    return cleaned_records


if __name__ == "__main__":
    run_cleaner()
