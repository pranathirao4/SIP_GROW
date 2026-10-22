"""
App Review Collector for Groww AI SIP Retention Discovery Agent.
Fetches real user reviews from Google Play Store and Apple App Store
focusing on auto-pay failures, mandate issues, and SIP cancellations.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
import requests
from google_play_scraper import Sort, reviews

# Ensure stdout uses UTF-8 in Windows environments
sys.stdout.reconfigure(encoding='utf-8')

GROWW_PLAYSTORE_APP_ID = "com.nextbillion.groww"
GROWW_APPSTORE_APP_ID = "1404871703"

RELEVANT_KEYWORDS = [
    "sip", "mandate", "auto-pay", "autopay", "deducted",
    "bounce", "cancelled", "cancel", "pause", "xirr",
    "penalty", "failed", "stopped"
]


def collect_playstore_reviews(app_id=GROWW_PLAYSTORE_APP_ID, count=400):
    """Fetch recent reviews from Google Play Store."""
    print(f"Fetching Google Play Store reviews for '{app_id}'...")
    try:
        result, _ = reviews(
            app_id,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=count
        )
        print(f"  Retrieved {len(result)} total Play Store reviews.")
        return result
    except Exception as e:
        print(f"[ERROR] Play Store scraping failed: {e}")
        return []


def collect_appstore_reviews(app_id=GROWW_APPSTORE_APP_ID):
    """Fetch customer reviews from Apple App Store RSS feed."""
    print(f"Fetching Apple App Store reviews for ID '{app_id}'...")
    url = f"https://itunes.apple.com/in/rss/customerreviews/id={app_id}/json"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code != 200:
            print(f"[WARN] Apple App Store RSS returned HTTP {resp.status_code}")
            return []
        data = resp.json()
        entries = data.get("feed", {}).get("entry", [])
        # The first entry in the feed is often app metadata, subsequent entries are reviews
        review_entries = entries[1:] if len(entries) > 1 else []
        print(f"  Retrieved {len(review_entries)} iOS reviews.")
        return review_entries
    except Exception as e:
        print(f"[ERROR] App Store scraping failed: {e}")
        return []


def run_review_collector(output_path="data/raw/app_reviews.json"):
    """Run multi-store review collector and filter for SIP/payment signals."""
    print("=== Starting App Store Review Collector ===")
    print(f"• Target Apps: Groww (Android: {GROWW_PLAYSTORE_APP_ID} | iOS: {GROWW_APPSTORE_APP_ID})")
    print(f"• Output Path: {output_path}\n")

    normalized_records = []

    # 1. Google Play Store
    play_reviews = collect_playstore_reviews(count=200)
    for r in play_reviews:
        content = r.get("content", "")
        # Filter for reviews mentioning keywords or low star ratings
        has_kw = any(kw in content.lower() for kw in RELEVANT_KEYWORDS)
        if has_kw or r.get("score", 5) <= 2:
            record_id = f"PLAYSTORE-{len(normalized_records)+1:05d}"
            published = r.get("at")
            pub_iso = published.isoformat() if isinstance(published, datetime) else str(published)

            record = {
                "record_id": record_id,
                "source": "google_play_store",
                "raw_id": r.get("reviewId"),
                "url": f"https://play.google.com/store/apps/details?id={GROWW_PLAYSTORE_APP_ID}",
                "title": f"Play Store {r.get('score')}★ Review",
                "raw_text": content.strip(),
                "author": r.get("userName", "Anonymous"),
                "rating": r.get("score", 0),
                "thumbs_up": r.get("thumbsUpCount", 0),
                "published_at": pub_iso,
                "has_retention_keyword": has_kw,
                "scraped_at": datetime.utcnow().isoformat()
            }
            normalized_records.append(record)

    # 2. Apple App Store
    ios_reviews = collect_appstore_reviews()
    for r in ios_reviews:
        title = r.get("title", {}).get("label", "")
        content = r.get("content", {}).get("label", "")
        full_text = f"{title}. {content}".strip()
        rating_str = r.get("im:rating", {}).get("label", "0")
        try:
            rating = int(rating_str)
        except ValueError:
            rating = 0

        has_kw = any(kw in full_text.lower() for kw in RELEVANT_KEYWORDS)
        if has_kw or rating <= 2:
            record_id = f"APPSTORE-{len(normalized_records)+1:05d}"
            record = {
                "record_id": record_id,
                "source": "apple_app_store",
                "raw_id": r.get("id", {}).get("label", ""),
                "url": f"https://apps.apple.com/in/app/groww-stocks-mutual-funds/id={GROWW_APPSTORE_APP_ID}",
                "title": title,
                "raw_text": content,
                "author": r.get("author", {}).get("name", {}).get("label", "Anonymous"),
                "rating": rating,
                "thumbs_up": 0,
                "published_at": r.get("updated", {}).get("label", datetime.utcnow().isoformat()),
                "has_retention_keyword": has_kw,
                "scraped_at": datetime.utcnow().isoformat()
            }
            normalized_records.append(record)

    # Save to output file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized_records, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(normalized_records)} filtered app reviews to: {output_path}")

    # Print preview
    print("\n--- Sample App Reviews Preview ---")
    for sample in normalized_records[:3]:
        print(f"[{sample['record_id']}] {sample['source']} ({sample['rating']}★)")
        print(f"  Title: {sample['title']}")
        print(f"  Text: {sample['raw_text'][:120]}...\n")

    return normalized_records


if __name__ == "__main__":
    run_review_collector()
