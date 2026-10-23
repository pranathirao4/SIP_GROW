"""
Deep Multi-Source Collector for Groww SIP Retention Discovery Engine.
Collects qualitative conversations across:
1. Reddit (via Apify trudax/reddit-scraper-lite across r/personalfinanceindia, r/IndiaInvestments, r/IndianStockMarket)
2. TradingQ&A (via public Discourse JSON API across Batches A-I)
3. Google Play Store & Apple App Store (1,000+ reviews for Groww)
Preserves original text, titles, dates, source URLs, author metadata, and engagement metrics.
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

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "trudax~reddit-scraper-lite"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# KEYWORD BATCHES AS SPECIFIED BY RESEARCH REQUIREMENTS
# -------------------------------------------------------------
BATCHES = {
    "Batch_A_Groww_Specific": [
        "Groww SIP experience", "Groww SIP not working", "Groww SIP status pending",
        "Groww SIP instalment not deducted", "Groww SIP mandate rejected", "Groww autopay not working",
        "Groww SIP cancelled automatically", "Groww SIP order failed", "Groww pause SIP option",
        "Groww cancel SIP process", "Groww customer support SIP complaint", "Groww portfolio showing wrong returns"
    ],
    "Batch_B_First_Time_Investors": [
        "first time SIP investor experience", "started SIP for the first time", "new investor mutual fund confusion",
        "first month of SIP investment", "what I wish I knew before starting SIP", "mistakes I made as a first time investor",
        "how I chose my first SIP", "first time investor afraid to lose money", "started SIP because friends suggested",
        "influencer convinced me to start SIP", "started SIP without understanding mutual funds"
    ],
    "Batch_C_Reasons_Stopping_Reducing": [
        "stopped mutual fund investment after job loss", "paused SIP due to financial emergency",
        "cancel SIP after salary reduction", "stopped investing to pay loan EMI", "reduced SIP contribution amount",
        "temporarily stopped mutual fund investments", "restarted SIP after stopping", "why I discontinued mutual fund SIP",
        "stopped SIP after unexpected expenses", "SIP affordability after rent and EMI", "stopped SIP due to low returns",
        "lost confidence in mutual fund investment", "irregular salary stopped monthly investing"
    ],
    "Batch_D_Returns_Confidence": [
        "mutual fund returns lower than expected", "SIP not giving expected returns", "negative returns after months of SIP",
        "checking mutual fund returns daily anxiety", "SIP investment not growing", "first market correction as investor India",
        "panic selling mutual funds experience", "confused about XIRR mutual funds", "difference between invested amount and current value"
    ],
    "Batch_E_Cash_Flow_Affordability": [
        "monthly SIP date salary date mismatch", "SIP debit before salary credited", "missed SIP due to low bank balance",
        "monthly expenses affect SIP investment", "rent and EMI affecting investments", "variable salary monthly SIP",
        "freelancer monthly investment difficulties", "SIP amount too high for monthly budget", "credit card debt versus SIP investment"
    ],
    "Batch_F_Habits_Post_Start": [
        "forgot monthly SIP instalment", "SIP autopay gives peace of mind", "how often check mutual fund portfolio",
        "SIP debit notification not received", "confused by SIP transaction history", "restart SIP after missed instalments",
        "managing multiple mutual fund SIPs"
    ],
    "Batch_G_External_Influence": [
        "asked friends whether to stop SIP", "family advice on mutual fund losses", "YouTube advice about stopping SIP",
        "Reddit advice on SIP in loss", "finfluencer advice mutual fund investment", "searched Google after SIP losses",
        "stopped SIP after friend's experience", "new investor relying on online communities"
    ],
    "Batch_H_Groww_Vs_Others": [
        "Groww versus Zerodha Coin mutual funds experience", "Groww versus Kuvera SIP", "Groww versus INDmoney mutual funds",
        "switched from Groww to another investment app", "left Groww mutual funds reasons", "Groww app review mutual fund investor",
        "Groww SIP customer service experience", "Groww portfolio tracking compared to other apps"
    ],
    "Batch_I_Why_Continue": [
        "continued SIP for one year experience", "why I continued my SIP during market fall", "long term SIP investing experience India",
        "what helped me stay invested", "monthly SIP habit success story", "stayed invested through market volatility",
        "automatic investment helped me stay consistent", "restarted SIP after financial difficulty"
    ]
}


# =============================================================
# 1. TRADINGQ&A COLLECTOR (Batch Expansion)
# =============================================================
def collect_tradingqna_expansion():
    print("\n=======================================================")
    print("▶ STARTING TRADINGQ&A EXPANSION COLLECTOR (Discourse API)")
    print("=======================================================")
    base_url = "https://tradingqna.com"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
    
    # Flatten selected search queries
    all_queries = []
    for b_name, q_list in BATCHES.items():
        all_queries.extend(q_list[:3]) # Top 3 per batch to be comprehensive yet fast
    
    seen_ids = set()
    records = []
    
    for idx, q in enumerate(all_queries):
        encoded = urllib.parse.quote(q)
        url = f"{base_url}/search.json?q={encoded}"
        print(f"[{idx+1}/{len(all_queries)}] TradingQ&A query: '{q}'...", end=" ", flush=True)
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                topics = data.get("topics", [])
                posts = {p["id"]: p for p in data.get("posts", [])}
                count_added = 0
                for t in topics:
                    tid = t.get("id")
                    if tid in seen_ids:
                        continue
                    seen_ids.add(tid)
                    post_id = t.get("first_post_id") or (t.get("post_stream", {}).get("posts", [{}])[0].get("id"))
                    post_obj = posts.get(post_id, {})
                    body = post_obj.get("cooked", "") or t.get("excerpt", "") or t.get("title", "")
                    
                    records.append({
                        "source": "tradingqna",
                        "topic_id": tid,
                        "title": t.get("title", ""),
                        "url": f"{base_url}/t/{t.get('slug', 'topic')}/{tid}",
                        "raw_text": body,
                        "created_at": t.get("created_at"),
                        "views": t.get("views", 0),
                        "reply_count": t.get("posts_count", 0),
                        "search_query": q
                    })
                    count_added += 1
                print(f"found {len(topics)} topics (+{count_added} new).")
            else:
                print(f"HTTP {r.status_code}")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error: {e}")
            
    out_file = RAW_DATA_DIR / "tradingqna_expanded.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(records)} TradingQ&A expanded records to {out_file}\n")
    return records


# =============================================================
# 2. GOOGLE PLAY STORE & APPLE APP STORE COLLECTOR (1,000 Reviews)
# =============================================================
def collect_reviews_expansion():
    print("\n=======================================================")
    print("▶ STARTING GROWW APP STORE & PLAY STORE EXPANSION")
    print("=======================================================")
    from google_play_scraper import Sort, reviews
    
    records = []
    
    # 1. Google Play Store (1,000 reviews for Groww)
    print("Fetching up to 1,000 newest reviews from Google Play Store ('com.nextbillion.groww')...", flush=True)
    try:
        ps_results, _ = reviews(
            "com.nextbillion.groww",
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=1000
        )
        print(f"  Retrieved {len(ps_results)} total Play Store reviews. Filtering for SIP & retention keywords...", flush=True)
        
        keywords = ["sip", "mandate", "autopay", "auto-pay", "deduct", "bounce", "cancel", "pause", "xirr", "fail", "wrong return", "penalty", "support", "ticket", "delay", "withdraw", "stop"]
        filtered_count = 0
        for r in ps_results:
            content = r.get("content", "")
            if any(k in content.lower() for k in keywords):
                records.append({
                    "source": "google_play_store",
                    "review_id": r.get("reviewId"),
                    "title": f"Play Store Review by {r.get('userName', 'User')}",
                    "raw_text": content,
                    "url": "https://play.google.com/store/apps/details?id=com.nextbillion.groww",
                    "rating": r.get("score"),
                    "thumbs_up": r.get("thumbsUpCount", 0),
                    "created_at": r.get("at").isoformat() if hasattr(r.get("at"), "isoformat") else str(r.get("at"))
                })
                filtered_count += 1
        print(f"  ✓ {filtered_count} high-signal SIP/retention reviews filtered from Google Play Store.")
    except Exception as e:
        print(f"  [ERROR] Google Play Store fetch error: {e}")

    # 2. Apple App Store RSS reviews for Groww (1404871703)
    print("Fetching Apple App Store reviews for Groww (ID: 1404871703)...", flush=True)
    try:
        url = "https://itunes.apple.com/in/rss/customerreviews/id=1404871703/json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code == 200:
            entries = resp.json().get("feed", {}).get("entry", [])
            ios_added = 0
            for item in entries[1:]:
                body = item.get("content", {}).get("label", "")
                title = item.get("title", {}).get("label", "")
                full_text = f"{title}\n{body}"
                records.append({
                    "source": "apple_app_store",
                    "review_id": item.get("id", {}).get("label"),
                    "title": title or "iOS User Review",
                    "raw_text": full_text,
                    "url": "https://apps.apple.com/in/app/groww-stocks-mutual-fund/id1404871703",
                    "rating": int(item.get("im:rating", {}).get("label", 0)) if "im:rating" in item else None,
                    "created_at": datetime.now().isoformat()
                })
                ios_added += 1
            print(f"  ✓ Added {ios_added} Apple App Store reviews.")
    except Exception as e:
        print(f"  [ERROR] Apple App Store fetch error: {e}")

    out_file = RAW_DATA_DIR / "app_reviews_expanded.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(records)} verified app reviews to {out_file}\n")
    return records


# =============================================================
# 3. APIFY REDDIT EXPANSION (Top Priority, Cheapest Scraper)
# =============================================================
def run_apify_reddit_expansion():
    print("\n=======================================================")
    print("▶ STARTING APIFY REDDIT EXPANSION (trudax/reddit-scraper-lite)")
    print("=======================================================")
    if not APIFY_TOKEN:
        print("[ERROR] APIFY_TOKEN missing in .env")
        return []

    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    
    # We group queries into 3 targeted community batches
    batches_to_run = [
        {
            "community": "personalfinanceindia",
            "searches": [
                "Groww SIP",
                "Groww autopay not working",
                "Groww cancel SIP",
                "first time SIP investor",
                "SIP date salary date mismatch",
                "paused SIP financial emergency",
                "negative returns months SIP",
                "confused about XIRR",
                "why I continued my SIP",
                "forgot monthly SIP instalment"
            ],
            "max_items": 80
        },
        {
            "community": "IndiaInvestments",
            "searches": [
                "Groww versus Zerodha Coin",
                "Groww SIP mandate rejected",
                "Groww portfolio wrong returns",
                "what I wish I knew before starting SIP",
                "stopped investing to pay loan EMI",
                "missed SIP due to low bank balance",
                "conflicting SIP advice online",
                "how I made investing a habit",
                "panic selling mutual funds"
            ],
            "max_items": 80
        },
        {
            "community": "IndianStockMarket",
            "searches": [
                "Groww SIP order failed",
                "Groww pause SIP option",
                "first month of SIP investment",
                "reduced SIP contribution amount",
                "SIP not giving expected returns",
                "switched from Groww to another app",
                "stayed invested through market volatility"
            ],
            "max_items": 60
        }
    ]

    all_reddit_items = []
    
    for b in batches_to_run:
        comm = b["community"]
        searches = b["searches"]
        max_items = b["max_items"]
        
        print(f"\n--- Scraping r/{comm} ({max_items} max items) ---")
        print(f"Queries: {', '.join(searches[:4])}...")
        
        run_input = {
            "searches": searches,
            "searchCommunityName": comm,
            "searchPosts": True,
            "searchComments": True,
            "skipCommunity": True,
            "maxItems": max_items,
            "sort": "relevance",
            "includeMediaLinks": True,
            "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}
        }
        
        try:
            r = requests.post(f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs", headers=headers, json=run_input, timeout=15)
            if r.status_code != 201:
                print(f"[WARN] Failed to trigger run for r/{comm}: HTTP {r.status_code}")
                continue
                
            run_data = r.json()["data"]
            run_id = run_data["id"]
            ds_id = run_data["defaultDatasetId"]
            print(f"Run started: {run_id}. Polling progress...", flush=True)
            
            start_t = time.time()
            while True:
                time.sleep(6)
                elapsed = int(time.time() - start_t)
                sr = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}", headers=headers, timeout=10)
                status = sr.json()["data"]["status"]
                print(f"  [{elapsed}s] r/{comm}: {status}", flush=True)
                if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
                    break
                if elapsed > 180: # Safeguard
                    print("  Timeout reached (180s), stopping poll...")
                    break
                    
            if status == "SUCCEEDED":
                dr = requests.get(f"https://api.apify.com/v2/datasets/{ds_id}/items", headers=headers, timeout=20)
                items = dr.json()
                print(f"✓ Fetched {len(items)} items from r/{comm}!")
                for it in items:
                    it["collected_from_community"] = comm
                all_reddit_items.extend(items)
            else:
                print(f"  [WARN] Run ended with status: {status}")
                
        except Exception as e:
            print(f"[ERROR] r/{comm} error: {e}")

    out_file = RAW_DATA_DIR / "reddit_batches_deep.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_reddit_items, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved total {len(all_reddit_items)} Reddit items to {out_file}\n")
    return all_reddit_items


if __name__ == "__main__":
    t_records = collect_tradingqna_expansion()
    r_records = collect_reviews_expansion()
    reddit_records = run_apify_reddit_expansion()
    print("=======================================================")
    print("COLLECTION COMPLETED:")
    print(f"• TradingQ&A Expanded: {len(t_records)} discussions")
    print(f"• Groww Play Store/App Store: {len(r_records)} reviews")
    print(f"• Reddit via Apify: {len(reddit_records)} discussions/comments")
    print("=======================================================")
