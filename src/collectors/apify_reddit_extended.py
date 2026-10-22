"""
Apify Reddit Extended Collector: 360° Scenario Scraper
Fetches 100 records across r/personalfinanceindia and r/IndiaInvestments
covering students, irregular income, job loss, emergencies, and mandate penalties.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "trudax~reddit-scraper-lite"

BATCHES = [
    {
        "community": "personalfinanceindia",
        "searches": [
            "student SIP",
            "job loss SIP",
            "irregular income",
            "freelance SIP",
            "stop SIP emergency",
            "cannot afford SIP",
            "checking portfolio daily anxiety",
            "SIP negative return"
        ],
        "target_count": 50
    },
    {
        "community": "IndiaInvestments",
        "searches": [
            "stop SIP",
            "pause SIP instead of cancel",
            "salary delay SIP",
            "bank bounce charge SIP",
            "first time SIP mistake",
            "discontinue SIP",
            "emergency fund SIP"
        ],
        "target_count": 50
    }
]


def run_batch(community, searches, max_items, headers):
    """Run Apify actor for a specific community and search queries."""
    print(f"\n--- Scraping Community: r/{community} (Target: {max_items} items) ---")
    print(f"• Queries: {', '.join(searches)}")

    run_input = {
        "searches": searches,
        "searchCommunityName": community,
        "searchPosts": True,
        "searchComments": True,
        "skipCommunity": True,
        "maxItems": max_items,
        "sort": "relevance",
        "includeMediaLinks": True
    }

    res = requests.post(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
        headers=headers,
        json=run_input
    )

    if res.status_code != 201:
        print(f"[ERROR] Failed to start Apify run: {res.status_code} - {res.text}")
        return []

    run_data = res.json()["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]
    print(f"Actor run started: {run_id} | Polling progress...")

    start_time = time.time()
    while True:
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        status_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}", headers=headers)
        status = status_res.json()["data"]["status"]
        print(f"  [{elapsed}s] r/{community} status: {status}", flush=True)

        if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            break

    if status == "SUCCEEDED":
        items_res = requests.get(f"https://api.apify.com/v2/datasets/{dataset_id}/items", headers=headers)
        items = items_res.json()
        print(f"  Successfully fetched {len(items)} items from r/{community}!")
        return items
    else:
        print(f"  [WARN] Run ended with status {status}")
        return []


def run_extended_reddit_collector(output_path="data/raw/reddit_comprehensive.json"):
    if not APIFY_TOKEN:
        print("[ERROR] APIFY_TOKEN missing in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    print("=== Starting 360° Reddit Scenario Scraper (Apify) ===")
    print("Scenarios: Students, Irregular/Freelance Income, Job Loss, Emergencies, Mandate Bounces\n")

    all_items = []
    seen_urls = set()

    for batch in BATCHES:
        raw_items = run_batch(
            community=batch["community"],
            searches=batch["searches"],
            max_items=batch["target_count"],
            headers=headers
        )
        for it in raw_items:
            url = it.get("url") or it.get("link") or ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_items.append(it)

    print(f"\nTotal raw unique items retrieved across all batches: {len(all_items)}")

    normalized = []
    sub_counts = {}

    for idx, item in enumerate(all_items, 1):
        record_id = f"REDDIT-EXT-{idx:05d}"
        community = item.get("communityName") or item.get("parsedCommunityName") or "Unknown"
        sub_counts[community] = sub_counts.get(community, 0) + 1

        title = item.get("title", "").strip()
        body = item.get("body", "").strip()

        normalized.append({
            "record_id": record_id,
            "source": f"reddit/{community}",
            "raw_id": item.get("id") or item.get("parsedId"),
            "url": item.get("url") or item.get("link"),
            "title": title,
            "raw_text": body,
            "author": item.get("username", "[deleted]"),
            "published_at": item.get("createdAt"),
            "upvotes": item.get("upVotes", 0),
            "upvote_ratio": item.get("upVoteRatio", 0.0),
            "comment_count": item.get("numberOfComments", 0),
            "content_type": item.get("dataType", "post"),
            "scraped_at": datetime.now().isoformat()
        })

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(normalized)} normalized scenario records to: {output_path}")
    print("\n--- Breakdown by Community ---")
    for s, c in sub_counts.items():
        print(f"  • {s}: {c} records")

    print("\n--- Sample Scenario Records Preview ---")
    for s in normalized[:3]:
        print(f"[{s['record_id']}] {s['title']}")
        print(f"  Community: {s['source']} | Upvotes: {s['upvotes']}")
        print(f"  URL: {s['url']}")
        snip = s['raw_text'][:120].replace('\n', ' ') if s['raw_text'] else "(Title only)"
        print(f"  Snippet: {snip}...\n")

    return normalized


if __name__ == "__main__":
    run_extended_reddit_collector()
