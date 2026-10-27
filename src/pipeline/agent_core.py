"""
Agent Core Module for Groww SIP Research Assistant
Handles:
1. Fast hybrid guardrail for off-topic filtering
2. Standalone query rewriting for multi-turn conversational follow-ups
3. Evidence formatting with stable IDs, sources, dates, and links
4. System prompt enforcement for PM case study requirements (feel vs did, review counts, 5-part structure, hard rules)
5. Groq streaming at temperature <= 0.2
"""

import re
import json
import time
from typing import List, Dict, Any, Tuple

def call_groq_with_retry(groq_client: Any, **kwargs) -> Any:
    """Wrapper around groq_client.chat.completions.create with automatic 429 rate-limit backoff."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return groq_client.chat.completions.create(**kwargs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower() or "limit" in err_str.lower():
                wait_sec = 6.0
                match = re.search(r'try again in ([\d\.]+)s', err_str, re.IGNORECASE)
                if match:
                    wait_sec = float(match.group(1)) + 1.0
                time.sleep(wait_sec)
                if attempt == max_retries - 1:
                    raise
            else:
                raise

OFF_TOPIC_MESSAGE = """I can only help with SIP and first-time investor research. Try asking:
'Why do investors pause their SIP in the first 6 months?'"""

EXPLICIT_OFF_TOPIC_TERMS = {
    # Politics & Political Leaders
    "prime minister", "narendra modi", "modi", "rahul gandhi", "bjp", "congress", "aap", "election",
    "elections", "politics", "political", "government", "parliament", "minister", "president",
    "chief minister", "mla", "mp", "lok sabha", "rajya sabha", "trump", "biden", "putin", "politician",
    # Sports & Games
    "cricket", "cricketer", "virat", "rohit", "dhoni", "ipl", "bcci", "football", "messi", "ronaldo",
    "fifa", "tennis", "badminton", "olympics", "world cup", "match", "score", "sport", "sports",
    "fav sport", "favorite sport", "favourite sport",
    # Cinema & Entertainment
    "movie", "movies", "cinema", "film", "films", "actor", "actress", "bollywood", "hollywood",
    "song", "songs", "music", "lyrics", "singer", "singers", "celebrity", "drama", "series", "netflix",
    # Weather & Nature
    "weather", "temperature", "rain", "monsoon", "forecast", "climate", "cyclone",
    # Food & Cooking
    "recipe", "recipes", "cook", "cooking", "food", "dish", "restaurant", "restaurants", "biryani",
    # General Trivia & Academics
    "capital of", "who is", "who was", "who won", "who invented", "history of", "geography of",
    "horoscope", "astrology", "zodiac", "joke", "jokes", "riddle", "riddles", "poem", "poems",
    "essay", "homework", "python code", "javascript code", "write code", "debug code", "calculator",
    "sort an array", "quicksort"
}

DOMAIN_KEYWORDS = {
    "sip", "sips", "groww", "invest", "investor", "investors", "investing", "investment", "investments",
    "mutual", "fund", "funds", "autopay", "auto-pay", "mandate", "mandates", "nach", "otm", "bank", "banks",
    "banking", "penalty", "penalties", "bounce", "bounced", "charge", "charges", "fee", "fees",
    "pause", "paused", "pausing", "stop", "stopped", "stopping", "cancel", "cancelled", "cancelling",
    "cancellation", "drop", "drop-off", "dropoff", "retention", "retain", "churn", "churning",
    "drawdown", "drawdowns", "loss", "losses", "profit", "profits", "return", "returns", "market",
    "nifty", "sensex", "equity", "debt", "elss", "index", "amc", "amcs", "zerodha", "coin", "kuvera",
    "etmoney", "cams", "kfintech", "mf central", "portfolio", "portfolios", "redeem", "redeeming",
    "redemption", "withdraw", "withdrawing", "withdrawal", "salary", "money", "rupee", "rupees",
    "review", "reviews", "rating", "ratings", "play store", "reddit", "app", "ui", "ux", "onboarding",
    "kyc", "pan", "account", "debit", "debits", "debited", "credit", "credited", "volatility",
    "panic", "risk", "behavior", "behaviour", "first-time", "beginner", "beginners", "step-up",
    "lumpsum", "installment", "installments", "tradingqna", "pay", "payment", "payments", "failure",
    "failures", "ecs", "upi", "nav", "folio", "compounding", "wealth", "asset", "saving", "savings",
    "finfluencer", "hype", "nudge", "nudges", "notification"
}

FOLLOW_UP_TRIGGERS = [
    "why", "why?", "how", "how?", "show examples", "examples", "example", "what else",
    "what else?", "what are other reasons", "other reasons", "tell me more", "explain",
    "elaborate", "and?", "what happened next", "which banks", "can you explain", "detail",
    "what should groww do", "solution", "solutions", "how to fix"
]


def is_short_follow_up(query: str) -> bool:
    """Detect if query is a short follow-up needing conversational history."""
    q_clean = query.lower().strip().rstrip('?!.,')
    words = q_clean.split()
    if q_clean in FOLLOW_UP_TRIGGERS or any(q_clean.startswith(tr) for tr in ["why", "how", "what else", "show example", "tell me"]):
        return True
    if len(words) <= 4 and any(w in q_clean for w in ["why", "how", "what", "more", "else", "and", "banks", "examples"]):
        return True
    return False


def check_query_scope(query: str, history: List[Dict[str, str]], groq_client: Any) -> Tuple[bool, str]:
    """
    Fast guardrail check before main model execution.
    Returns (is_in_scope: bool, message: str).
    """
    if not query or not query.strip():
        return False, OFF_TOPIC_MESSAGE

    q_lower = query.lower().strip()
    q_clean = q_lower.rstrip('?!.,')

    # 1. Check if it's a short follow-up in an ongoing conversation
    has_prior_history = bool(history and any(m.get("role") == "user" for m in history))
    if has_prior_history and is_short_follow_up(query):
        # Follow-ups inherit scope from ongoing conversation
        return True, ""

    # 2. Check explicit off-topic terms (politics, sports, recipes, weather, coding, etc.)
    for term in EXPLICIT_OFF_TOPIC_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', q_clean):
            return False, OFF_TOPIC_MESSAGE

    # 3. Check domain anchor terms
    has_domain_term = any(term in q_lower for term in DOMAIN_KEYWORDS)
    if has_domain_term:
        return True, ""

    # 4. If no history and no domain keyword, fast LLM scope check with temperature 0
    if groq_client:
        try:
            check_prompt = (
                "You are an intent classifier for a research tool analyzing Indian mutual fund SIPs, "
                "investor drop-off causes, Groww app experience, and retail investor behavior.\n"
                "Determine if the user query is relevant to mutual funds, SIPs, investor retention, "
                "Groww features, or investment research.\n"
                "Reply ONLY 'IN_SCOPE' or 'OFF_TOPIC'.\n\n"
                f"Query: \"{query}\"\n"
                "Decision:"
            )
            res = call_groq_with_retry(
                groq_client,
                model="qwen/qwen3.8-27b",
                messages=[{"role": "user", "content": check_prompt}],
                max_tokens=6,
                temperature=0.0
            )
            decision = res.choices[0].message.content.strip().upper()
            if "OFF_TOPIC" in decision or "NO" in decision:
                return False, OFF_TOPIC_MESSAGE
            return True, ""
        except Exception:
            # Fallback: if unknown and not containing domain keywords
            if not has_domain_term and not has_prior_history:
                return False, OFF_TOPIC_MESSAGE

    return True, ""


def rewrite_query_with_history(query: str, history: List[Dict[str, str]], groq_client: Any) -> str:
    """
    Rewrites follow-up questions (e.g. 'why?' or 'show examples') into a single standalone
    question capturing conversation context before passing to retrieval.
    """
    if not history or not is_short_follow_up(query):
        return query

    # Find the most recent user queries from history
    past_user_queries = [m["content"].strip() for m in history if m.get("role") == "user" and m.get("content")]
    if not past_user_queries:
        return query

    if not groq_client:
        return f"{past_user_queries[-1]} {query}"

    try:
        recent_context = []
        for m in history[-4:]:
            if m.get("content"):
                role_label = "User" if m["role"] == "user" else "Assistant"
                # Keep snippet short
                recent_context.append(f"{role_label}: {m['content'][:250]}")
        context_str = "\n".join(recent_context)

        rewrite_prompt = (
            "You are a query rewriter for an empirical investor research engine analyzing Indian mutual fund SIPs.\n"
            "Given the recent conversation history, rewrite the user's latest follow-up into a single clear, "
            "standalone search question about SIP and investor behavior.\n"
            "If it is already standalone, return it as-is.\n"
            "Output ONLY the rewritten question. Do not include quotes, preamble, or explanation.\n\n"
            f"Conversation History:\n{context_str}\n\n"
            f"Follow-up: {query}\n"
            "Standalone Question:"
        )

        res = call_groq_with_retry(
            groq_client,
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": rewrite_prompt}],
            max_tokens=50,
            temperature=0.0
        )
        rewritten = res.choices[0].message.content.strip().strip('"').strip("'")
        return rewritten if rewritten else query
    except Exception:
        return f"{past_user_queries[-1]} {query}"


def get_source_label(src: str) -> str:
    """Return clean standard source name."""
    s = str(src).lower()
    if "play_store" in s:
        return "Groww Play Store"
    if "tradingqna" in s:
        return "TradingQ&A"
    if "youtube" in s:
        return "YouTube"
    if "app_store" in s:
        return "Groww App Store"
    return "Reddit"


def format_reviews_for_prompt(records: List[Dict[str, Any]]) -> str:
    """Format retrieved reviews with stable ID, source, date, link, feel vs did."""
    blocks = []
    for idx, r in enumerate(records, 1):
        rec_id = r.get("record_id", f"REC-{idx:05d}")
        src = get_source_label(r.get("source", ""))
        url = r.get("url") or "#"
        dt = (r.get("published_at") or "2024-02-11")[:10]
        
        clf = r.get("classification", {})
        quote = clf.get("verbatim_quote") or r.get("raw_text", "")[:350].replace("\n", " ")
        felt = clf.get("underlying_problem") or "Emotional/cognitive friction"
        did = clf.get("observable_behaviour") or "Action taken regarding SIP"
        
        blocks.append(
            f"Review [{idx}] ID: {rec_id} | Source: {src} | Date: {dt} | Link: [🔗 {src} ↗]({url})\n"
            f"  - What user felt: {felt}\n"
            f"  - What user did: {did}\n"
            f"  - User statement: \"{quote}\""
        )
    return "\n\n".join(blocks)


def build_system_prompt(reviews_context: str, total_reviews_looked_at: int) -> str:
    """Builds the system prompt enforcing all hard rules, counts, feel vs did, and 5-part structure."""
    return f"""You are an empirical research assistant for a Groww Growth Product Manager case study.
Your job is to analyze real user reviews and discussions (Google Play Store, Reddit, TradingQ&A, YouTube) about mutual fund SIPs and first-time retail investors in India to find WHY investors pause, reduce, or stop their SIPs.

CRITICAL HARD RULES YOU MUST OBEY:
1. EVIDENCE BOUNDARY: Answer ONLY from the provided reviews. Never invent quotes, numbers, or IDs. If the provided reviews do not contain enough evidence to answer the question, state honestly that the evidence does not answer the question or that evidence is thin.
2. CITATIONS: After EVERY claim, theme, or observation, cite the specific review with its clickable link using this format: [🔗 Source ↗](url). Keep all review link references intact.
3. PHRASING COUNTS: Always phrase review counts as "X of the {total_reviews_looked_at} reviews I looked at" (e.g. "3 of the {total_reviews_looked_at} reviews I looked at"). NEVER say "X% of all users" or "most Indians". If fewer than 5 reviews support a point, explicitly say: "The evidence is thin on this point."
4. SEPARATE FEELINGS FROM ACTIONS: Strictly keep what users FEEL (loss aversion, anxiety over bank bounce charges, regret, confusion) separate from what they DID (paused SIP, stopped mandate, reduced installment, continued investing).
5. NO FINANCIAL ADVICE: NEVER recommend, rank, or name specific funds, stocks, or AMCs as investment advice. If asked, decline and explain that you provide qualitative research on investor retention, not financial advice.
6. NO FEAR OR FOMO NUDGES: NEVER suggest fear, FOMO, or urgency-based nudges (e.g., 'Hurry, you will lose money'). If asked, decline and offer a calm, helpful, transparent alternative.
7. USER SEGMENTS: If asked about segments (age, income stability, source of money, who influenced them), ONLY compare groups if the loaded reviews explicitly mention those details. Otherwise say the data does not show it.
8. SOLUTIONS: If asked for solutions, give 2-3 ideas, each tied directly to an identified root cause and supported by review evidence.
9. LANGUAGE STYLE: Use simple, plain English, short sentences, and no jargon.

MANDATORY OUTPUT STRUCTURE (Keep each section concise so that all 5 parts are ALWAYS fully generated):

**Short answer**
(1-2 clear, direct sentences answering the user's question)

**What users are saying**
(2-3 short bullet points, max 2 sentences each):
- **[Theme]:** (X of the {total_reviews_looked_at} reviews I looked at). Users felt [feeling] and [action taken]. [🔗 Source ↗](url)

**Why it is happening (root cause)**
My interpretation: (1-2 simple sentences on the underlying root cause)

**Confidence**
(State "High", "Medium", or "Low", with one concise sentence giving the reason)

**What to ask next**
(1-2 relevant, concise follow-up questions)

REVIEWS YOU MUST USE (Total looked at: {total_reviews_looked_at}):
{reviews_context}
"""


def linkify_citations(text: str, records_map: dict) -> str:
    """Ensure any [REC-XXXXX] or raw citation tags are converted to clickable markdown links."""
    def repl(match):
        raw = match.group(0)
        clean_id = re.sub(r'[\u2010\u2011\u2012\u2013\u2014]', '-', raw).strip('[]')
        if clean_id in records_map:
            rec = records_map[clean_id]
            url = rec.get("url") or "#"
            src_label = get_source_label(rec.get("source", ""))
            return f"[🔗 {src_label} ↗]({url})"
        return raw

    return re.sub(r'\[?REC[\-\u2010\u2011\u2012\u2013\u2014]\d{5}\]?', repl, text)
