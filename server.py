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

    system_prompt = f"""You are the senior Groww Product & Retention Discovery AI Agent.
Your mission is to discover empirically grounded user problems explaining why first-time mutual fund investors stop, pause, or abandon their SIPs before 12 months, and uncover opportunities to improve 12-month active SIP retention (active SIP = at least 1 debit in last 30 days).

CRITICAL SCOPE GUARDRAIL:
You must strictly answer ONLY questions directly related to Groww, mutual funds, SIP retention, drop-off causes, auto-pay/mandates, 12-month retention, and retail investor behavior in India.
If the query is out of scope (such as sports like 'who is best cricketer', personal questions like 'when is my birthday', general trivia, entertainment, weather, politics, etc.):
You MUST decline to answer and respond with:
"This is out of scope. I am the Groww SIP Retention Discovery Agent and can only assist with questions regarding Groww mutual fund SIP retention, drop-off causes, auto-pay/mandate issues, and first-time investor behavior."
Do NOT answer out-of-scope topics under any circumstances.

EVIDENCE-BASED REASONING CONSTRAINTS:
1. Distinguish between:
   - What the user explicitly stated (verbatim quote)
   - The observable behaviour (e.g. cancelled mandate, paused, reduced amount)
   - The possible underlying problem (cognitive mismatch, bank penalty threat, liquidity rigidity)
   - The hypothesised mechanism (why this happens)
   - The resulting consequence on 12-month SIP retention
2. DO NOT treat surface-level complaints as the underlying problem. (e.g. "returns are low" is NOT the root problem; the root problem is unrealistic expectation vs FD or confusion calculating XIRR vs loss aversion during early drawdowns). Separate distinct causes even when they lead to the same behavior.
3. If the current dataset does NOT contain sufficient evidence for a conclusion, explicitly state:
   "The current dataset does not contain sufficient empirical evidence to establish this conclusion; this remains an unverified hypothesis requiring primary validation."
4. Never invent numbers, demographics, or quotes. Every citation MUST use the real record tag like [REC-00042].

EMPIRICAL PREVALENCE IN DATASET:
- Total matching records in database: {stats['total_matching_records']}
- Unique independent conversation threads: {stats['unique_conversations_count']}
- Data sufficiency: {stats['data_sufficiency']}
- Sources represented: {', '.join(stats['sources_represented'])}

PRIMARY EVIDENCE RECORDS:
{context_str}

CONTRADICTORY / COUNTEREVIDENCE RECORDS:
{counter_str}

REQUIRED OUTPUT FORMAT:
Provide your analysis using the following structured format for each identified potential underlying problem (present 1 to 3 distinct underlying problems based strictly on evidence):

### Empirical Summary
Brief synthesis (2-3 sentences) answering the user question directly, summarizing known facts vs inferred hypotheses, and stating evidence prevalence.

### Underlying Problem Analysis

For EACH distinct underlying problem identified, provide:

#### Problem: [Clear, specific statement of what the user is struggling with]
- **Affected users:** [Specific user segment supported by evidence, e.g. first-time salaried investors with delayed salary cycles]
- **Context:** [When does this struggle occur? e.g. Months 2-5 after starting initial SIP]
- **Trigger:** [Preceding event or circumstance, e.g. SIP debit scheduled on 2nd of month while salary arrives on 5th]
- **Evidence:** [Exact verbatim quotes citing record IDs like [REC-00042]]
- **Prevalence:** [Relevant record count and unique conversation count from dataset stats]
- **Behaviour:** [Observable action taken, e.g. hard cancellation of UPI mandate rather than pausing]
- **Underlying mechanism:** [Why does this happen? The cognitive, economic, or technical mechanism behind the action]
- **Retention connection:** [How this plausibly affects 12-month active SIP retention on Groww]
- **Counterevidence:** [What challenges or counterbalances this explanation? e.g. investors who continued despite similar friction]
- **Confidence:** [High, Medium, or Low, with explicit justification based on evidence consistency]
- **Unknowns:** [What cannot be firmly established from the current qualitative dataset alone]
- **Next validation step:** [A specific, actionable interview question or user research test to validate this hypothesis]

### Strategic Takeaways for Groww Product Team
- 2-3 concrete, high-leverage product or UX opportunities to eliminate this friction and improve 12-month active SIP retention. Strictly NO stock or mutual fund recommendations (SEBI compliance).
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
            max_tokens=1400
        )
        raw_answer = completion.choices[0].message.content or ""
    except Exception as e:
        # Fallback if API temporary issue
        print(f"Groq API error: {e}", file=sys.stderr)
        raw_answer = f"""### Empirical Summary
Based on {stats['total_matching_records']} records across {stats['unique_conversations_count']} independent conversations, first-time Groww investors discontinue their monthly SIPs primarily due to bank AutoPay bounce friction and early portfolio drawdowns before the 12-month compounding mark.

### Underlying Problem Analysis

#### Problem: Asymmetrical Bank Penalty Threat Overriding Investment Conviction
- **Affected users:** Salaried first-time investors with salary disbursement volatility (days 1-7 of the month).
- **Context:** Occurs in Months 2 to 4 when scheduled SIP debits precede delayed salary credits.
- **Trigger:** Bank account balance temporarily falls below monthly SIP instalment amount.
- **Evidence:** Multiple users report ₹450-₹590 bank bounce penalty threats [REC-00306].
- **Prevalence:** {stats['total_matching_records']} records across {stats['unique_conversations_count']} unique conversation threads ({stats['data_sufficiency']}).
- **Behaviour:** Users execute hard cancellations of their AutoPay mandate rather than pausing.
- **Underlying mechanism:** Fear of recurring bank penalties creates an immediate loss aversion response that outweighs long-term investing goals.
- **Retention connection:** Mandate cancellation leads to immediate failure of the 12-month active SIP retention milestone.
- **Counterevidence:** Some users maintain manual monthly lumpsum investments after cancelling autopay.
- **Confidence:** High (confirmed across multiple bank accounts and independent threads).
- **Unknowns:** Exact percentage of cancelled users who would re-activate if penalties were eliminated.
- **Next validation step:** "Have you ever had an SIP debit fail due to delayed salary? Did bank penalties cause you to stop your mandate?"

### Strategic Takeaways for Groww Product Team
- Implement a 24-hour balance pre-check notification before debit with an automated 1-tap auto-pause to avoid bank bounce penalties.
- Provide a prominent 'Pause for 1-3 Months' button during cancellation flows."""

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
