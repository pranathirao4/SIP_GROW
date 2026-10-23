import json
import re
import urllib.parse
from itertools import islice
import requests
from youtube_comment_downloader import YoutubeCommentDownloader

def find_youtube_videos(query, max_results=3):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        # Extract video IDs: /watch?v=XXXXXXXXXXX
        matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', r.text)
        seen = []
        for vid in matches:
            if vid not in seen:
                seen.append(vid)
            if len(seen) >= max_results:
                break
        return seen
    except Exception as e:
        print(f"Error searching {query}: {e}")
        return []

queries = [
    "Groww SIP cancel kaise kare",
    "Groww autopay not working SIP",
    "Groww mutual fund beginner mistakes India",
    "Groww SIP pause problem",
    "Groww vs Zerodha Coin mutual fund"
]

all_vids = {}
for q in queries:
    vids = find_youtube_videos(q, 2)
    print(f"Query '{q}': found vids {vids}")
    for v in vids:
        all_vids[v] = q

print(f"Total unique videos found: {len(all_vids)}")

downloader = YoutubeCommentDownloader()
records = []

for vid, query in list(all_vids.items())[:6]: # top 6 videos
    print(f"Fetching comments for video {vid} (query: {query})...")
    try:
        comments = downloader.get_comments_from_url(f"https://www.youtube.com/watch?v={vid}", sort_by=0)
        count = 0
        for c in islice(comments, 25): # get up to 25 comments per video
            text = c.get("text", "")
            if len(text.strip()) > 15: # quality filter
                records.append({
                    "source": "youtube_comments",
                    "comment_id": c.get("cid"),
                    "title": f"YouTube Comment on {query}",
                    "raw_text": text,
                    "url": f"https://www.youtube.com/watch?v={vid}&lc={c.get('cid')}",
                    "video_id": vid,
                    "author": c.get("author", "User"),
                    "likes": c.get("votes", 0),
                    "created_at": c.get("time", ""),
                    "search_query": query
                })
                count += 1
        print(f"  ✓ Added {count} comments from video {vid}")
    except Exception as e:
        print(f"  Error fetching {vid}: {e}")

print(f"Total YouTube comments collected: {len(records)}")
with open("data/raw/youtube_comments_expanded.json", "w", encoding="utf-8") as f:
    json.dump(records, f, indent=2, ensure_ascii=False)
print("Saved to data/raw/youtube_comments_expanded.json")
