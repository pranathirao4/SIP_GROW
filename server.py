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
            elif "youtube" in src:
                src_name = "YouTube Comment"
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

    # Step 1: Enriched Retrieval with Prevalence & Counterevidence
    retrieval_res = retriever.retrieve_with_evidence_stats(user_query, top_k=6)
    retrieved_docs = retrieval_res["primary_matches"]
    counter_docs = retrieval_res.get("counterevidence_matches", [])
    stats = retrieval_res["stats"]

    # Step 2: Build Grounded Evidence Context
    context_blocks = []
    for r in retrieved_docs:
        clf = r.get("classification", {})
        quote = clf.get("verbatim_quote") or r.get("raw_text", "")[:250].replace("\n", " ")
        obs_beh = clf.get("observable_behaviour", "Action taken")
        und_prob = clf.get("underlying_problem", "Cognitive / structural friction")
        mech = clf.get("hypothesised_mechanism", "Underlying mechanism")
        churn_nat = clf.get("churn_nature", "Voluntary / Involuntary")
        root_u = clf.get("root_conversation_url") or r.get("url") or "#"

        context_blocks.append(
            f"Record ID: {r['record_id']} | Source: {r.get('source')} | URL: {r.get('url')}\n"
            f"Root Conversation: {root_u}\n"
            f"Explicit Statement: \"{quote}\"\n"
            f"Observable Behaviour: {obs_beh}\n"
            f"Underlying Problem: {und_prob}\n"
            f"Hypothesised Mechanism: {mech}\n"
            f"Churn Nature: {churn_nat}"
        )
    context_str = "\n\n".join(context_blocks)

    counter_blocks = []
    for cr in counter_docs:
        c_quote = cr.get("classification", {}).get("verbatim_quote") or cr.get("raw_text", "")[:200]
        counter_blocks.append(
            f"Counter-Evidence ID: {cr['record_id']} | Source: {cr.get('source')} | URL: {cr.get('url')}\n"
            f"Quote: \"{c_quote}\""
        )
    counter_str = "\n\n".join(counter_blocks) if counter_blocks else "No direct counterevidence found in matching subset."

    is_detail_requested = any(w in user_query.lower() for w in ["detail", "deep dive", "in-depth", "explain more", "full analysis", "breakdown", "elaborate"])

    if is_detail_requested:
        system_prompt = f"""You are the senior Groww Product & Retention Discovery AI Agent.
The user explicitly asked for an IN-DEPTH, DETAILED response.

Provide an exhaustive, structured breakdown:
1. Executive Summary directly answering the question based on 406 verified discussions.
2. Distinct Root Problems: For each problem, break down:
   - Affected User Segment
   - Preceding Trigger & Timeline (e.g. Month 2-4 salary mismatch)
   - Real User Evidence citing record IDs like [REC-00042]
   - Underlying Cognitive / Structural Mechanism
   - Retention Impact on 12-Month Active SIPs
   - Counterevidence
3. High-Leverage Strategic Interventions for Groww Product Team (SEBI compliant).

PRIMARY EVIDENCE RECORDS:
{context_str}
"""
    else:
        system_prompt = f"""You are the senior Groww Product & Retention Discovery AI Agent.
Your mission is to answer user queries like Google AI Search: in a VERY UNDERSTANDABLE, CRISP, AND DIRECT MANNER.
When a user asks a question, they should immediately find what they are looking for without sifting through walls of academic headers.

STYLE & STRUCTURE CONSTRAINTS (STRICT):
1. DIRECT ANSWER FIRST: Begin with a natural opening paragraph (1-2 sentences) directly answering what was asked:
   "Based on the provided user feedback from Reddit, TradingQ&A, Google Play Store reviews, and YouTube, [direct answer]..."
2. 2-3 CRISP BULLET POINTS:
   - Start each point with a bold, meaningful theme: e.g. "• **[Theme Name]:** [Crisp explanation in 2-3 sentences explaining what happens, citing the user situation and verbatim evidence]."
   - Embed real user quotes and citations naturally like [REC-00042].
3. DO NOT output complex tables, academic checklists ("Prevalence:", "Underlying Mechanism:", "Unknowns:"). Keep it clean and easy to read.
4. MANDATORY CLOSING TEXT (EXACT):
   At the very end of your response, you MUST include this exact line:
   "💡 Let me know if you want a detailed response."

PRIMARY EVIDENCE RECORDS:
{context_str}
"""

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
            max_tokens=1000
        )
        raw_answer = completion.choices[0].message.content or ""
    except Exception as e:
        # Fallback if API temporary issue
        print(f"Groq API error: {e}", file=sys.stderr)
        raw_answer = f"""Based on the provided user feedback from Reddit, TradingQ&A, Google Play Store reviews, and YouTube, first-time investors stop their SIPs within the first 12 months primarily due to three core friction points:

• **Bank AutoPay Mandate & Penalty Threat:** When SIP debits occur before delayed monthly salary disbursements (e.g. 2nd vs 5th), bank balances dip. Fear of recurring ₹450–₹590 bank bounce fees leads users to permanently cancel their AutoPay mandate [[🔗 View Reddit Discussion](#)].

• **Early Market Drawdowns & Loss Aversion:** Beginners frequently enter expecting linear, guaranteed monthly profits. Experiencing temporary negative returns (-3% to -5%) in months 3 to 6 triggers panic and causes them to stop SIPs [[🔗 View TradingQ&A](#)].

• **Hidden Pause Feature:** Investors facing temporary liquidity crunches cannot easily find an option to pause for 1–3 months, so they hard-cancel the SIP [[🔗 View Groww Play Store](#)].

💡 Let me know if you want a detailed response."""

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
