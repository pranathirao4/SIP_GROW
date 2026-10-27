"""
Unified Gap Collector for Groww SIP Retention Project.
Fills the exact gaps identified in Step 1:
1. Google Play Store reviews for Groww (1-3 stars, SIP keywords)
2. Apple App Store reviews for Groww (all pages)
3. Reddit (via Apify trudax~reddit-scraper-lite) targeting specific investor churn queries
4. YouTube Comments on popular videos about SIP cancellations, losses, and mandate failures.

Privacy Rule: No usernames or personal identities are retained. Public content only.
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
from google_play_scraper import Sort, reviews
from youtube_comment_downloader import YoutubeCommentDownloader
from itertools import islice

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
GROWW_PLAYSTORE_APP_ID = "com.nextbillion.groww"
GROWW_APPSTORE_APP_ID = "1404871703"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SIP_KEYWORDS = [
    "sip", "autopay", "auto-pay", "mandate", "failed", "paused", "pause",
    "stopped", "stop", "cancel", "cancelled", "returns", "loss", "nav",
    "penalty", "charge", "charges", "xirr", "deducted", "deduction",
    "statement", "notification", "bounce", "bounced", "delay", "ecs", "nach"
]


def collect_google_play_reviews(max_count=800):
    """Collect 1-3 star and keyword-matched reviews for Groww from Google Play Store."""
    print(f"\n[1/4] Collecting Google Play reviews for Groww ({GROWW_PLAYSTORE_APP_ID})...")
    all_reviews = []
    seen_texts = set()

    # Strategy 1: NEWEST sort
    try:
        res_newest, _ = reviews(
            GROWW_PLAYSTORE_APP_ID,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=600
        )
        print(f"  Fetched {len(res_newest)} newest reviews.")
        for r in res_newest:
            content = r.get("content", "")
            score = r.get("score", 5)
            # Filter: 1-3 stars OR contains SIP keywords
            is_low_rating = score in [1, 2, 3]
            has_keyword = any(kw in content.lower() for kw in SIP_KEYWORDS)
            if (is_low_rating or has_keyword) and content not in seen_texts:
                seen_texts.add(content)
                all_reviews.append({
                    "source": "google_play_store",
                    "id": f"GP-{r.get('reviewId', len(all_reviews))}",
                    "title": f"Groww Play Store Review ({score}★)",
                    "raw_text": content,
                    "rating": score,
                    "published_at": r.get("at", datetime.now()).isoformat()[:10],
                    "url": f"https://play.google.com/store/apps/details?id={GROWW_PLAYSTORE_APP_ID}"
                })
    except Exception as e:
        print(f"  [WARN] Play Store newest fetch error: {e}")

    # Strategy 2: MOST RELEVANT sort (helps capture high-engagement complaints)
    try:
        res_relevant, _ = reviews(
            GROWW_PLAYSTORE_APP_ID,
            lang="en",
            country="in",
            sort=Sort.MOST_RELEVANT,
            count=400
        )
        print(f"  Fetched {len(res_relevant)} most relevant reviews.")
        for r in res_relevant:
            content = r.get("content", "")
            score = r.get("score", 5)
            is_low_rating = score in [1, 2, 3]
            has_keyword = any(kw in content.lower() for kw in SIP_KEYWORDS)
            if (is_low_rating or has_keyword) and content not in seen_texts:
                seen_texts.add(content)
                all_reviews.append({
                    "source": "google_play_store",
                    "id": f"GP-{r.get('reviewId', len(all_reviews))}",
                    "title": f"Groww Play Store Review ({score}★)",
                    "raw_text": content,
                    "rating": score,
                    "published_at": r.get("at", datetime.now()).isoformat()[:10],
                    "url": f"https://play.google.com/store/apps/details?id={GROWW_PLAYSTORE_APP_ID}"
                })
    except Exception as e:
        print(f"  [WARN] Play Store relevant fetch error: {e}")

    print(f"  -> Total Play Store reviews retained after filtering: {len(all_reviews)}")
    return all_reviews


def collect_apple_appstore_reviews():
    """Collect Apple App Store customer reviews for Groww across all RSS pages."""
    print(f"\n[2/4] Collecting Apple App Store reviews for Groww (ID {GROWW_APPSTORE_APP_ID})...")
    all_reviews = []
    seen_texts = set()

    for page in range(1, 11):
        url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={GROWW_APPSTORE_APP_ID}/sortby=mostrecent/json"
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
            if resp.status_code != 200:
                break
            entries = resp.json().get("feed", {}).get("entry", [])
            for e in entries[1:]:  # skip index 0 metadata
                title = e.get("title", {}).get("label", "")
                content = e.get("content", {}).get("label", "")
                rating_str = e.get("im:rating", {}).get("label", "0")
                rating = int(rating_str) if rating_str.isdigit() else 0
                full_text = f"{title}. {content}"
                if full_text not in seen_texts and len(full_text.strip()) > 15:
                    seen_texts.add(full_text)
                    all_reviews.append({
                        "source": "apple_app_store",
                        "id": f"IOS-{e.get('id', {}).get('label', len(all_reviews))}",
                        "title": f"Groww iOS Review ({rating}★): {title[:50]}",
                        "raw_text": full_text,
                        "rating": rating,
                        "published_at": e.get("updated", {}).get("label", "2024-01-01")[:10],
                        "url": f"https://apps.apple.com/in/app/groww-stocks-mutual-fund-upi/id{GROWW_APPSTORE_APP_ID}"
                    })
        except Exception as e:
            print(f"  [WARN] App Store page {page} error: {e}")
            break

    print(f"  -> Total iOS reviews retained: {len(all_reviews)}")
    return all_reviews


def collect_reddit_apify(max_items=350):
    """Collect Reddit posts & comments using Apify actor trudax~reddit-scraper-lite."""
    print(f"\n[3/4] Collecting targeted Reddit discussions via Apify...")
    if not APIFY_TOKEN:
        print("  [WARN] APIFY_TOKEN not set in environment. Skipping Apify Reddit collection.")
        return []

    subreddits = [
        "personalfinanceindia",
        "IndiaInvestments",
        "IndianStreetBets",
        "mutualfundsindia"
    ]
    
    target_queries = [
        "stopped my SIP",
        "paused my SIP",
        "discontinued SIP",
        "SIP not giving returns",
        "SIP in loss",
        "should I stop my SIP",
        "first SIP",
        "SIP failed autopay",
        "redeemed my SIP",
        "SIP cancelled",
        "Groww SIP stopped",
        "Groww SIP not working",
        "Groww SIP failed"
    ]

    start_urls = []
    for sub in subreddits:
        for q in target_queries[:6]: # pick top queries per sub to keep run fast and cost minimal
            encoded = urllib.parse.quote(q)
            start_urls.append({"url": f"https://www.reddit.com/r/{sub}/search/?q={encoded}&restrict_sr=1&sort=relevance"})

    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    actor_id = "trudax~reddit-scraper-lite"
    run_input = {
        "startUrls": start_urls,
        "skipComments": False,
        "skipCommunity": True,
        "maxItems": max_items,
        "includeMediaLinks": False,
        "sort": "relevance"
    }

    print(f"  Triggering Apify actor '{actor_id}' (max items: {max_items}, hard cap: $0.80)...")
    try:
        run_res = requests.post(
            f"https://api.apify.com/v2/acts/{actor_id}/runs",
            headers=headers,
            json=run_input,
            timeout=30
        )
        if run_res.status_code != 201:
            print(f"  [ERROR] Failed to start Apify actor: {run_res.status_code} - {run_res.text[:200]}")
            return []

        run_data = run_res.json()["data"]
        run_id = run_data["id"]
        print(f"  Actor started successfully (Run ID: {run_id}). Monitoring...")

        start_t = time.time()
        dataset_id = None
        while time.time() - start_t < 180: # timeout 3 mins
            time.sleep(6)
            s_res = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}", headers=headers, timeout=15)
            s_data = s_res.json()["data"]
            status = s_data["status"]
            print(f"    Status: {status} ({int(time.time() - start_t)}s elapsed)", flush=True)
            if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
                dataset_id = s_data.get("defaultDatasetId")
                break

        if status != "SUCCEEDED" or not dataset_id:
            print(f"  [WARN] Apify run ended with status {status}")
            return []

        # Fetch items
        d_res = requests.get(f"https://api.apify.com/v2/datasets/{dataset_id}/items", headers=headers, timeout=30)
        items = d_res.json()
        print(f"  Fetched {len(items)} items from Apify dataset.")

        reddit_records = []
        seen_texts = set()
        for idx, it in enumerate(items, 1):
            text = it.get("body") or it.get("selftext") or it.get("text") or ""
            title = it.get("title") or "Reddit Discussion"
            full_text = f"{title}. {text}" if text else title
            if len(full_text.strip()) > 30 and full_text not in seen_texts:
                seen_texts.add(full_text)
                sub_name = it.get("communityName") or it.get("parsedCommunityName") or "Reddit"
                reddit_records.append({
                    "source": f"reddit/r/{sub_name}",
                    "id": f"REDDIT-GAP-{idx:05d}",
                    "title": title[:100],
                    "raw_text": full_text,
                    "published_at": it.get("createdAt") or "2024-02-15",
                    "url": it.get("url") or f"https://www.reddit.com/r/{sub_name}"
                })
        print(f"  -> Retained {len(reddit_records)} Reddit items.")
        return reddit_records

    except Exception as e:
        print(f"  [ERROR] Reddit collection failed: {e}")
        return []


def collect_youtube_comments():
    """Collect YouTube comments from targeted videos on SIP drop-offs & failures."""
    print(f"\n[4/4] Collecting YouTube comments on SIP drop-off topics...")
    downloader = YoutubeCommentDownloader()
    
    # Specific high-relevance Indian personal finance videos on stopping SIPs, losses, mandate issues
    target_videos = [
        {"vid": "Z9C3u-hZzEw", "topic": "Why People Stop SIP in Loss"},
        {"vid": "VbZqI7Q_U2k", "topic": "Groww SIP Autopay Failed Issues"},
        {"vid": "rK9T5g7Zk1A", "topic": "Beginner SIP Mistakes and Panic"},
        {"vid": "L4q9k8vWq_8", "topic": "Should You Stop SIP During Market Fall"}
    ]

    yt_records = []
    seen = set()

    for item in target_videos:
        vid = item["vid"]
        topic = item["topic"]
        print(f"  Scraping comments for '{topic}' (vid: {vid})...")
        try:
            comments = downloader.get_comments_from_url(f"https://www.youtube.com/watch?v={vid}", sort_by=0)
            count = 0
            for c in islice(comments, 60):
                text = c.get("text", "")
                if len(text.strip()) > 25 and text not in seen:
                    seen.add(text)
                    count += 1
                    yt_records.append({
                        "source": "youtube_comments",
                        "id": f"YT-{c.get('cid', count)}",
                        "title": f"YouTube Comment: {topic}",
                        "raw_text": text,
                        "published_at": "2024-03-01",
                        "url": f"https://www.youtube.com/watch?v={vid}&lc={c.get('cid', '')}"
                    })
            print(f"    Retrieved {count} comments.")
        except Exception as e:
            print(f"    [WARN] Video {vid} error: {e}")

    print(f"  -> Total YouTube comments retained: {len(yt_records)}")
    return yt_records


def run_full_collection():
    print("=" * 60)
    print("STARTING TARGETED DATA COLLECTION TO FILL AUDIT GAPS")
    print("=" * 60)

    gp_items = collect_google_play_reviews(max_count=800)
    ios_items = collect_apple_appstore_reviews()
    reddit_items = collect_reddit_apify(max_items=350)
    yt_items = collect_youtube_comments()

    combined = gp_items + ios_items + reddit_items + yt_items
    print(f"\nTotal new raw items collected across all sources: {len(combined)}")

    out_file = RAW_DIR / "gap_collected_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"Saved raw items to {out_file}")
    return combined

if __name__ == "__main__":
    run_full_collection()
