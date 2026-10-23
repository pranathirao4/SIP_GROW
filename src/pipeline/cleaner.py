"""
Stage B: Data Cleaning, Normalization & Deduplication Pipeline
Unifies records from Reddit, TradingQ&A, Google Play Store / Apple App Store, and YouTube Comments.
Performs text normalization, hash-based deduplication, URL deduplication, and exports source-specific CSVs.
"""

import sys
import json
import re
import csv
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
    """Generate MD5 hash of normalized lowercase alphanumeric text for duplicate detection."""
    clean_sample = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    return hashlib.md5(clean_sample.encode('utf-8')).hexdigest()


def export_csv(records, filepath: Path, fieldnames=None):
    """Safely export list of dicts to CSV."""
    if not records:
        return
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        fieldnames = ["record_id", "source", "url", "title", "raw_text", "author", "published_at", "upvotes_or_likes", "comments_or_replies"]
    
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    print(f"  ✓ Exported CSV: {filepath.name} ({len(records)} rows)")


def run_cleaner():
    """Run full cleaning and deduplication across all available raw sources."""
    print("\n=======================================================")
    print("▶ STAGE B: DATA CLEANING, DEDUPLICATION & CSV EXPORT")
    print("=======================================================")

    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_dir = base_dir / "data" / "raw"
    processed_dir = base_dir / "data" / "processed"
    exports_dir = base_dir / "data" / "exports"
    processed_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    raw_files = [
        # 1. Reddit files
        ("data/raw/reddit_batches_deep.json", "reddit"),
        ("data/raw/reddit_comprehensive.json", "reddit"),
        ("data/raw/reddit_groww.json", "reddit"),
        ("data/raw/reddit_pilot.json", "reddit"),
        # 2. TradingQ&A files
        ("data/raw/tradingqna_expanded.json", "tradingqna"),
        ("data/raw/tradingqna.json", "tradingqna"),
        ("data/raw/tradingqna_groww.json", "tradingqna"),
        # 3. App Store & Play Store reviews
        ("data/raw/app_reviews_expanded.json", "app_reviews"),
        ("data/raw/app_reviews.json", "app_reviews"),
        # 4. YouTube comments
        ("data/raw/youtube_comments_expanded.json", "youtube_comments")
    ]

    all_raw_items = []

    for rel_path, default_source in raw_files:
        f_path = base_dir / rel_path
        if not f_path.exists():
            continue
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"• Loaded {len(data):4d} records from {rel_path}")
                for item in data:
                    item["_file_source"] = default_source
                all_raw_items.extend(data)
        except Exception as e:
            print(f"[WARN] Error reading {rel_path}: {e}")

    print(f"\nTotal raw inputs collected: {len(all_raw_items)} records")

    seen_hashes = set()
    seen_urls = set()
    cleaned_records = []
    duplicate_count = 0
    empty_count = 0
    source_breakdown = {}

    for item in all_raw_items:
        # Resolve text
        raw_text = (
            item.get("raw_text") or
            item.get("body") or
            item.get("selftext") or
            item.get("text") or
            item.get("content") or
            ""
        )
        
        # Resolve title
        title = item.get("title") or ""
        if not title:
            comm = item.get("communityName") or item.get("searchCommunityName") or ""
            if comm:
                title = f"Reddit Post/Comment in r/{comm}"
            elif item.get("_file_source") == "youtube_comments":
                title = "YouTube Video Comment"
            elif item.get("_file_source") == "app_reviews":
                title = "Groww App User Review"
            else:
                title = "Discussion Forum Thread"

        raw_text = normalize_text(raw_text)
        title = normalize_text(title)

        combined_text = f"{title}\n\n{raw_text}".strip() if title else raw_text

        # Filter out empty or very short records (< 15 characters)
        if not combined_text or len(combined_text) < 15:
            empty_count += 1
            continue

        # Check duplicate URL if present (append review_id / comment_id for generic store pages)
        url = item.get("url") or item.get("permalink") or ""
        if "play.google.com" in url or "apps.apple.com" in url:
            if item.get("review_id"):
                url = f"{url}#{item.get('review_id')}"
        elif "youtube.com" in url:
            if item.get("comment_id"):
                url = f"{url}#{item.get('comment_id')}"

        if url and url in seen_urls:
            duplicate_count += 1
            continue

        # Check duplicate text hash
        content_hash = compute_hash(combined_text)
        if content_hash in seen_hashes:
            duplicate_count += 1
            continue

        seen_hashes.add(content_hash)
        if url:
            seen_urls.add(url)

        # Standardize source
        file_src = item.get("_file_source", "unknown")
        if "reddit" in file_src or "reddit" in str(item.get("source", "")).lower():
            comm = item.get("communityName") or item.get("collected_from_community") or "Reddit"
            final_source = f"reddit/r/{comm}" if not comm.startswith("r/") else f"reddit/{comm}"
        elif "tradingqna" in file_src or "tradingqna" in str(item.get("source", "")).lower():
            final_source = "tradingqna"
        elif "youtube" in file_src:
            final_source = "youtube_comments"
        elif "app" in file_src:
            final_source = item.get("source") or "google_play_store"
        else:
            final_source = item.get("source", "web_forum")

        source_breakdown[final_source] = source_breakdown.get(final_source, 0) + 1

        rec_num = len(cleaned_records) + 1
        system_id = f"REC-{rec_num:05d}"

        # Resolve engagement and author
        upvotes = (
            item.get("upVotes") or
            item.get("upvotes") or
            item.get("like_count") or
            item.get("likes") or
            item.get("thumbs_up") or
            item.get("views") or
            0
        )
        replies = (
            item.get("numberOfReplies") or
            item.get("numberOfComments") or
            item.get("comment_count") or
            item.get("reply_count") or
            item.get("posts_count") or
            0
        )
        author = item.get("username") or item.get("author") or "anonymous"
        published_at = item.get("createdAt") or item.get("created_at") or item.get("published_at") or ""

        cleaned_records.append({
            "record_id": system_id,
            "original_id": str(item.get("id") or item.get("topic_id") or item.get("review_id") or item.get("comment_id") or ""),
            "source": final_source,
            "url": url,
            "title": title,
            "raw_text": raw_text,
            "combined_text": combined_text,
            "author": author,
            "published_at": published_at,
            "upvotes_or_likes": upvotes,
            "comments_or_replies": replies,
            "dedup_hash": content_hash
        })

    # Save cleaned output JSON
    unified_json_path = processed_dir / "cleaned_records.json"
    with open(unified_json_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)

    print("\n--- Cleaning & Deduplication Summary ---")
    print(f"• Total Raw Ingested: {len(all_raw_items)}")
    print(f"• Empty/Short Filtered: {empty_count}")
    print(f"• Exact/Near Duplicates Removed: {duplicate_count}")
    print(f"• Cleaned Unique Records Produced: {len(cleaned_records)}")
    print(f"• Saved To: {unified_json_path}")

    print("\n--- Source Breakdown ---")
    for s, c in sorted(source_breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {s}: {c} records")

    # Export source-specific CSVs as instructed
    print("\n--- Exporting Source-Specific CSV Files ---")
    reddit_records = [r for r in cleaned_records if "reddit" in r["source"].lower()]
    tradingqna_records = [r for r in cleaned_records if "tradingqna" in r["source"].lower()]
    app_review_records = [r for r in cleaned_records if "store" in r["source"].lower() or "app" in r["source"].lower()]
    youtube_records = [r for r in cleaned_records if "youtube" in r["source"].lower()]

    export_csv(reddit_records, exports_dir / "reddit_records.csv")
    export_csv(tradingqna_records, exports_dir / "tradingqna_records.csv")
    export_csv(app_review_records, exports_dir / "app_reviews_records.csv")
    export_csv(youtube_records, exports_dir / "youtube_records.csv")
    export_csv(cleaned_records, exports_dir / "unified_dataset.csv")

    return cleaned_records


if __name__ == "__main__":
    run_cleaner()
