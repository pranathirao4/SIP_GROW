"""
Apify Reddit Collector for Groww AI SIP Retention Discovery Agent.
Collects qualitative investor discussions across target Indian investing subreddits.
"""

import os
import sys
import json
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "trudax~reddit-scraper-lite"

# Target subreddits and search terms directly aligned with 12-month retention
SUBREDDITS = [
    "IndiaInvestments",
    "personalfinanceindia",
    "IndianStockMarket"
]

KEYWORDS = [
    "stopped SIP",
    "cancelled SIP",
    "paused SIP",
    "SIP cancellation reasons",
    "failed SIP instalment",
    "SIP mandate problem",
    "SIP negative returns",
    "SIP affordability",
    "first time SIP investment problems"
]


def build_search_urls(subreddits, keywords):
    """Build Reddit search URLs for each community and query."""
    urls = []
    for sub in subreddits:
        for kw in keywords:
            encoded_kw = urllib.parse.quote(kw)
            url = f"https://www.reddit.com/r/{sub}/search/?q={encoded_kw}&restrict_sr=1&sort=relevance"
            urls.append({"url": url})
    return urls


def run_apify_reddit_collector(max_items=150, output_path="data/raw/reddit_pilot.json"):
    """Trigger Apify actor run, monitor status, and save the raw dataset."""
    if not APIFY_TOKEN:
        print("[ERROR] APIFY_TOKEN not found in .env. Please set it before running.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    start_urls = build_search_urls(SUBREDDITS, KEYWORDS)
    print(f"=== Starting Reddit Collector (Apify Pilot) ===")
    print(f"• Target Subreddits: {', '.join(SUBREDDITS)}")
    print(f"• Queries Configured: {len(KEYWORDS)} keywords ({len(start_urls)} search endpoints)")
    print(f"• Max Item Limit: {max_items} records (Cost Cap: ~$0.60)")
    print(f"• Output Path: {output_path}\n")

    run_input = {
        "startUrls": start_urls,
        "skipComments": True,
        "skipCommunity": True,
        "maxItems": max_items,
        "includeMediaLinks": True,
        "sort": "relevance"
    }

    print("Submitting actor run to Apify Cloud...")
    run_res = requests.post(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
        headers=headers,
        json=run_input
    )

    if run_res.status_code != 201:
        print(f"[ERROR] Failed to start Apify actor. Status: {run_res.status_code}")
        print(run_res.text)
        sys.exit(1)

    run_data = run_res.json()["data"]
    run_id = run_data["id"]
    print(f"Actor run started successfully! Run ID: {run_id}")
    print("Monitoring live status (this typically takes 30-60 seconds)...")

    # Poll status until finished
    start_time = time.time()
    while True:
        time.sleep(5)
        status_res = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers=headers
        )
        status_data = status_res.json()["data"]
        status = status_data["status"]
        elapsed = int(time.time() - start_time)
        print(f"  [{elapsed}s elapsed] Status: {status}", flush=True)

        if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            dataset_id = status_data["defaultDatasetId"]
            break

    if status != "SUCCEEDED":
        print(f"[ERROR] Apify run ended with status: {status}")
        sys.exit(1)

    print(f"\nRun succeeded! Fetching dataset from Apify (Dataset ID: {dataset_id})...")
    dataset_res = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
        headers=headers
    )
    raw_items = dataset_res.json()
    print(f"Retrieved {len(raw_items)} raw records from Apify.")

    # Standardize records according to architecture schema
    normalized_records = []
    subreddit_counts = {}

    for idx, item in enumerate(raw_items, 1):
        record_id = f"REDDIT-{idx:05d}"
        community = item.get("communityName") or item.get("parsedCommunityName") or "Unknown"
        subreddit_counts[community] = subreddit_counts.get(community, 0) + 1

        standard_record = {
            "record_id": record_id,
            "source": f"reddit/{community}",
            "raw_id": item.get("id") or item.get("parsedId"),
            "url": item.get("url") or item.get("link"),
            "title": item.get("title", "").strip(),
            "raw_text": item.get("body", "").strip(),
            "author": item.get("username", "[deleted]"),
            "published_at": item.get("createdAt"),
            "upvotes": item.get("upVotes", 0),
            "upvote_ratio": item.get("upVoteRatio", 0.0),
            "comment_count": item.get("numberOfComments", 0),
            "content_type": item.get("contentType", "text"),
            "scraped_at": item.get("scrapedAt", datetime.utcnow().isoformat())
        }
        normalized_records.append(standard_record)

    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized_records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(normalized_records)} normalized records to: {output_path}")

    # Print summary statistics
    print("\n--- Summary Breakdown by Community ---")
    for sub, count in sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {sub}: {count} records")

    print("\n--- Sample Scraped Records Preview ---")
    for sample in normalized_records[:3]:
        print(f"[{sample['record_id']}] {sample['title']}")
        print(f"  Subreddit: {sample['source']} | Upvotes: {sample['upvotes']} | Comments: {sample['comment_count']}")
        print(f"  URL: {sample['url']}")
        preview_body = sample['raw_text'][:120].replace('\n', ' ') if sample['raw_text'] else "(No body text / title only)"
        print(f"  Snippet: {preview_body}...\n")

    return normalized_records


if __name__ == "__main__":
    run_apify_reddit_collector()
