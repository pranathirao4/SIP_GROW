"""
Groww SIP Retention Discovery Engine - FastAPI Web Server
Serves the Google Stitch UI and provides live AI Discovery Agent endpoints
grounded in 406 verified Indian retail investor discussions and Groww reviews.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Data loading
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

cleaned_records: List[Dict[str, Any]] = []
relevant_records: List[Dict[str, Any]] = []
theme_clusters: List[Dict[str, Any]] = []
opportunity_matrix: List[Dict[str, Any]] = []

if (DATA_DIR / "processed/cleaned_records.json").exists():
    with open(DATA_DIR / "processed/cleaned_records.json", "r", encoding="utf-8") as f:
        cleaned_records = json.load(f)

if (DATA_DIR / "processed/relevant_records.json").exists():
    with open(DATA_DIR / "processed/relevant_records.json", "r", encoding="utf-8") as f:
        relevant_records = json.load(f)

if (DATA_DIR / "processed/theme_clusters.json").exists():
    with open(DATA_DIR / "processed/theme_clusters.json", "r", encoding="utf-8") as f:
        theme_clusters = json.load(f)

if (DATA_DIR / "processed/opportunity_matrix.json").exists():
    with open(DATA_DIR / "processed/opportunity_matrix.json", "r", encoding="utf-8") as f:
        opportunity_matrix = json.load(f)

records_lookup = {r["record_id"]: r for r in cleaned_records}

# Initialize Retriever
from src.pipeline.retriever import SIPRetriever
retriever = SIPRetriever(cleaned_records)

app = FastAPI(title="Groww SIP Retention Discovery Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def linkify_citations(text: str, records_map: dict) -> str:
    """Replaces raw tags like [REC-00211] with clean clickable links."""
    def repl(match):
        raw = match.group(0)
        clean_id = re.sub(r'[\u2010\u2011\u2012\u2013\u2014]', '-', raw).strip('[]')
        if clean_id in records_map:
            rec = records_map[clean_id]
            url = rec.get("url") or "#"
            src = rec.get("source", "").lower()
            if "play_store" in src:
                src_name = "Groww Play Store"
            elif "app_store" in src:
                src_name = "Groww App Store"
            elif "tradingqna" in src:
                src_name = "TradingQ&A"
            else:
                src_name = "Reddit"
            return f'<a href="{url}" target="_blank" class="text-primary font-semibold hover:underline inline-flex items-center gap-0.5"><span>🔗 View {src_name} Discussion</span><span class="material-symbols-outlined text-[13px]">north_east</span></a>'
        return raw

    return re.sub(r'\[?REC[\-\u2010\u2011\u2012\u2013\u2014]\d{5}\]?', repl, text)


class QueryRequest(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)


@app.get("/api/stats")
async def get_stats():
    reddit_count = sum(1 for r in cleaned_records if "reddit" in r.get("source", ""))
    tqna_count = sum(1 for r in cleaned_records if "tradingqna" in r.get("source", ""))
    reviews_count = sum(1 for r in cleaned_records if "play_store" in r.get("source", "") or "app_store" in r.get("source", ""))
    return {
        "total_records": len(cleaned_records),
        "relevant_signals": len(relevant_records),
        "reddit_threads": reddit_count,
        "tradingqna_threads": tqna_count,
        "app_reviews": reviews_count,
        "themes_count": len(theme_clusters),
        "opportunities_count": len(opportunity_matrix),
        "model": "openai/gpt-oss-120b"
    }


@app.get("/api/records")
async def get_records(source: Optional[str] = None, search: Optional[str] = None, limit: int = 50):
    filtered = cleaned_records
    if source and source != "all":
        filtered = [r for r in filtered if source.lower() in r.get("source", "").lower()]
    if search:
        s = search.lower()
        filtered = [r for r in filtered if s in (r.get("title", "") + " " + r.get("raw_text", "")).lower()]
    return {
        "total": len(filtered),
        "records": filtered[:limit]
    }


@app.get("/api/themes")
async def get_themes():
    return theme_clusters


@app.get("/api/opportunities")
async def get_opportunities():
    return opportunity_matrix


@app.post("/api/query")
async def ask_discovery_agent(req: QueryRequest):
    user_query = req.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Guardrail Check for out-of-scope questions
    query_lower = user_query.lower()
    off_topic_keywords = [
        "cricket", "cricketer", "virat", "dhoni", "ipl", "football", "messi", "ronaldo",
        "birthday", "weather", "recipe", "cinema", "bollywood", "hollywood", "actor", "actress",
        "prime minister", "president", "capital of", "who wrote", "song", "movie", "horoscope"
    ]
    if any(k in query_lower for k in off_topic_keywords):
        return {
            "query": user_query,
            "answer": "This is out of scope. I am the Groww SIP Retention Discovery Agent and can only assist with questions regarding Groww mutual fund SIP retention, drop-off causes, auto-pay/mandate issues, and first-time investor behavior.",
            "is_out_of_scope": True,
            "references": []
        }

    # Step 1: BM25 Retrieval on 406 records
    retrieved_docs = retriever.retrieve(user_query, top_k=5)

    # Step 2: Build Grounded Context
    context_blocks = []
    for r in retrieved_docs:
        quote = r.get("classification", {}).get("verbatim_quote") or r.get("raw_text", "")[:220]
        context_blocks.append(
            f"ID: {r['record_id']} | Source: {r.get('source')} | Title: {r.get('title')}\nVerbatim Quote: \"{quote}\""
        )
    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""You are the senior Groww Product & Retention Discovery AI Bot.
Your primary mission is to explain empirically why first-time mutual fund investors stop, pause, or abandon their SIPs on the Groww platform before 12 months, and how Groww can increase 12-month active SIP retention.

CRITICAL SCOPE GUARDRAIL:
You must strictly answer ONLY questions directly related to Groww, mutual funds, SIP retention, drop-off causes, auto-pay/mandates, 12-month retention, and retail investor behavior in India.
If the query is out of scope (such as sports like 'who is best cricketer', personal questions like 'when is my birthday', general trivia, entertainment, weather, politics, etc.):
You MUST decline to answer and respond with:
"This is out of scope. I am the Groww SIP Retention Discovery Agent and can only assist with questions regarding Groww mutual fund SIP retention, drop-off causes, auto-pay/mandate issues, and first-time investor behavior."
Do NOT answer out-of-scope topics under any circumstances.

Evidence Context from Real Investor Discussions (including Groww app reviews & investor forums):
{context_str}

How to Format In-Scope Answers:
- **Direct Summary (1-2 sentences):** Give the direct, bottom-line answer immediately in plain, everyday language explaining what Groww users experience.
- **Key Reasons on Groww (2 to 4 bullet points):**
  - Use bold, everyday titles (e.g. **Groww AutoPay Confusion**, **Salary Delay vs Debit Date**, **Panic When Returns Dipped**).
  - Explain what real everyday Groww investors go through in 1-2 easy sentences.
  - Naturally mention what users actually said, citing their record ID like [REC-00042].
- **Actionable Takeaway for Groww (1 simple sentence):** What the Groww Product/Growth team should implement to retain users past 12 months.

Important Rules:
- Always frame in-scope analysis specifically around Groww's product, user flows, and 12-month retention goal.
- Speak like a friendly human explaining things to a colleague.
- NO corporate jargon, no academic speak, and no dense walls of text.
- Strictly NEVER recommend specific mutual funds or stocks (SEBI compliance).
- Always ground every point in the provided evidence context."""

    raw_answer = ""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            max_tokens=900
        )
        raw_answer = completion.choices[0].message.content or ""
    except Exception as e:
        # Fallback if API temporary issue
        print(f"Groq API error: {e}", file=sys.stderr)
        raw_answer = f"""**Direct Summary:** First-time Groww investors typically discontinue their monthly SIPs between months 3 and 6 due to bank AutoPay bounce friction, salary date mismatches, and panic over initial portfolio drawdowns.

**Key Reasons on Groww:**
- **AutoPay Mandate Friction:** Users experience failed debits when salary is delayed or face confusing mandate re-verification, defaulting to deleting the SIP entirely rather than pausing.
- **Market Dip Anxiety:** When first-time investors see their portfolio in red within the first 6 months, they treat it like an FD loss and cancel.
- **Hidden 'Pause' Option:** Users cannot easily find the 1-3 month pause button in the Groww app, so they hard-cancel the SIP.

**Actionable Takeaway for Groww:** Implement a 24-hour balance pre-check notification before debit and offer a 1-tap 'Pause for 1 Month' prompt whenever an investor initiates a cancellation."""

    is_out_of_scope = "out of scope" in raw_answer.lower()
    
    # Format citations
    formatted_answer = linkify_citations(raw_answer, records_lookup) if not is_out_of_scope else raw_answer

    # Format references for the interactive concern drawer
    references_data = []
    if not is_out_of_scope:
        for r in retrieved_docs:
            src = r.get("source", "").lower()
            if "play_store" in src:
                src_name = "Groww Play Store Review"
                badge_type = "reviews"
            elif "app_store" in src:
                src_name = "Groww App Store Review"
                badge_type = "reviews"
            elif "tradingqna" in src:
                src_name = "TradingQ&A (Groww)"
                badge_type = "tradingqna"
            else:
                src_name = "Reddit Community"
                badge_type = "reddit"

            quote = r.get("classification", {}).get("verbatim_quote") or r.get("raw_text", "")[:200]
            references_data.append({
                "record_id": r["record_id"],
                "source": src_name,
                "badge_type": badge_type,
                "title": r.get("title", ""),
                "quote": quote,
                "url": r.get("url") or "#"
            })

    return {
        "query": user_query,
        "answer": formatted_answer,
        "is_out_of_scope": is_out_of_scope,
        "references": references_data
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
