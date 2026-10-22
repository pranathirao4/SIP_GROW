"""
TradingQ&A Collector for Groww AI SIP Retention Discovery Agent.
Queries TradingQ&A (Discourse forum) for Indian retail investor discussions
regarding SIP debit failures, mandate bounce penalties, and cancellations.
Requires no API keys, zero cost.
"""

import sys
import json
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
import requests

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://tradingqna.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

TARGET_QUERIES = [
    "SIP cancelled",
    "SIP mandate failed",
    "SIP stop vs pause",
    "auto debit SIP penalty",
    "SIP instalment bounce",
    "discontinue SIP",
    "SIP negative returns"
]


def collect_tradingqna_discussions(queries=None, output_path="data/raw/tradingqna.json"):
    """Scrape discussions from TradingQ&A via native Discourse search API."""
    queries = queries or TARGET_QUERIES
    print("=== Starting TradingQ&A Collector ===")
    print(f"• Target Queries: {len(queries)} search terms")
    print(f"• Mechanism: Discourse Public JSON API (100% Free, Zero Key)")
    print(f"• Output Path: {output_path}\n")

    seen_topic_ids = set()
    normalized_records = []

    for q in queries:
        encoded_q = urllib.parse.quote(q)
        search_url = f"{BASE_URL}/search.json?q={encoded_q}"
        print(f"Searching: '{q}' ...", end=" ", flush=True)

        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"[WARN] HTTP {resp.status_code}")
                continue

            data = resp.json()
            topics = data.get("topics", [])
            posts = {p["id"]: p for p in data.get("posts", [])}
            print(f"Found {len(topics)} topics")

            for topic in topics:
                t_id = topic.get("id")
                if t_id in seen_topic_ids:
                    continue
                seen_topic_ids.add(t_id)

                slug = topic.get("slug", "")
                topic_url = f"{BASE_URL}/t/{slug}/{t_id}"

                # Match post text snippet if available
                blurb = ""
                for p in posts.values():
                    if p.get("topic_id") == t_id:
                        blurb = p.get("blurb", "")
                        break

                record_id = f"TQNA-{len(normalized_records)+1:05d}"
                record = {
                    "record_id": record_id,
                    "source": "tradingqna",
                    "raw_id": str(t_id),
                    "url": topic_url,
                    "title": topic.get("title", "").strip(),
                    "raw_text": blurb.strip(),
                    "author": topic.get("last_poster_username", "unknown"),
                    "published_at": topic.get("created_at"),
                    "views": topic.get("views", 0),
                    "posts_count": topic.get("posts_count", 0),
                    "like_count": topic.get("like_count", 0),
                    "query_matched": q,
                    "scraped_at": datetime.utcnow().isoformat()
                }
                normalized_records.append(record)

            time.sleep(1)  # Respectful rate limiting

        except Exception as e:
            print(f"[ERROR] Query '{q}' failed: {e}")

    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized_records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(normalized_records)} unique TradingQ&A records to: {output_path}")

    # Print preview
    print("\n--- Sample TradingQ&A Records Preview ---")
    for sample in normalized_records[:3]:
        print(f"[{sample['record_id']}] {sample['title']}")
        print(f"  URL: {sample['url']}")
        print(f"  Views: {sample['views']} | Posts: {sample['posts_count']}")
        print(f"  Snippet: {sample['raw_text'][:120]}...\n")

    return normalized_records


if __name__ == "__main__":
    collect_tradingqna_discussions()
