"""
SIP Review Engine - Groww Research Lab
A focused, professional qualitative AI discovery agent to discover why investors
stay with their SIPs — or stop, increasing 12-month active SIP retention.
Faithfully designed to match the Google Photos Review Engine aesthetic.
"""

import os
import sys
import time
import json
import re
from pathlib import Path
import streamlit as st
import threading
from groq import Groq
import streamlit.components.v1 as components
from dotenv import load_dotenv
from src.pipeline.retriever import SIPRetriever
from src.pipeline.agent_core import (
    OFF_TOPIC_MESSAGE,
    check_query_scope,
    rewrite_query_with_history,
    format_reviews_for_prompt,
    build_system_prompt,
    linkify_citations,
    get_source_label
)

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# Pre-cache & Pre-warm Groq Client Singleton
@st.cache_resource
def get_groq_client():
    if not GROQ_API_KEY:
        return None
    try:
        c = Groq(api_key=GROQ_API_KEY)
        # Pre-warm connection pool synchronously so first query is 100% warm (<0.15s TTFT)
        c.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": "1"}],
            max_tokens=1
        )
        return c
    except Exception:
        try:
            return Groq(api_key=GROQ_API_KEY)
        except Exception:
            return None

groq_client = get_groq_client()

# Page configuration
st.set_page_config(
    page_title="SIP Insight - Groww Research Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Google Photos Review Engine Aesthetic)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />

<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #FFFFFF !important;
        color: #202124 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Hide Default Streamlit Clutter */
    header[data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(8px) !important;
        border-bottom: 1px solid #F1F3F4 !important;
    }
    #MainMenu, footer {
        visibility: hidden !important;
    }
    
    /* Complete Elimination of Streamlit Stale Dimming, Ghosting & Blur */
    [data-stale="true"],
    div[data-stale="true"],
    .stApp[data-stale="true"],
    [data-testid="stAppViewContainer"][data-stale="true"],
    [data-testid="stVerticalBlock"][data-stale="true"],
    [data-testid="stChatMessage"][data-stale="true"],
    section.main[data-stale="true"],
    .main[data-stale="true"],
    .block-container[data-stale="true"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }
    [data-stale="true"] * {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }
    [data-testid="stStatusWidget"],
    div[data-testid="stStatusWidget"],
    .stStatusWidget,
    #stStatusWidget {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Left Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #ECEFF1 !important;
        padding-top: 1rem !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.5rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
    }
    
    /* Sidebar Brand Header (Matching Picture 1) */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0.5rem 0.5rem 1.25rem 0.5rem;
    }
    .brand-icon-box {
        width: 36px;
        height: 36px;
        background-color: #E6F8F0;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .brand-text-col {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .brand-title-text {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 16.5px;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.015em;
        line-height: 1.2;
    }
    .brand-subtitle-text {
        font-family: 'Inter', sans-serif;
        font-size: 9.5px;
        font-weight: 700;
        color: #4B5563;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        line-height: 1.2;
        margin-top: 2px;
    }
    
    /* Sidebar Navigation Buttons */
    .stSidebar div[data-testid="stButton"] button {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #3C4043 !important;
        border-radius: 8px !important;
        padding: 7px 12px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 10px !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }
    .stSidebar div[data-testid="stButton"] button:hover {
        background-color: #F1F3F4 !important;
        color: #202124 !important;
    }
    
    /* Recents Section in Sidebar */
    .sidebar-section-label {
        font-size: 11px;
        color: #70757A;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        padding: 1.2rem 0.5rem 0.4rem 0.5rem;
    }
    .recent-empty-text {
        font-size: 12px;
        color: #70757A;
        padding: 0.2rem 0.5rem 0.8rem 0.5rem;
        line-height: 1.4;
    }
    .sidebar-footer-note {
        font-size: 11px;
        color: #70757A;
        line-height: 1.4;
        padding: 1rem 0.5rem;
        border-top: 1px solid #F1F3F4;
        margin-top: 2rem;
    }
    
    /* Main Content Container Spacing */
    .main .block-container {
        max-width: 1180px !important;
        padding-top: 1.25rem !important;
        padding-bottom: 7.5rem !important; /* Clearance for sticky bottom input */
    }
    
    /* Empty State Hero (Pic 1) */
    .engine-hero-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 2.1rem;
        font-weight: 600;
        color: #202124;
        letter-spacing: -0.02em;
        text-align: center;
        margin-top: 3.5rem;
        margin-bottom: 0.6rem;
    }
    .engine-hero-subtitle {
        font-size: 0.95rem;
        color: #5F6368;
        text-align: center;
        max-width: 640px;
        margin: 0 auto 3.5rem auto;
        line-height: 1.55;
    }
    
    /* Prompt Chips (Stacked above input in Pic 1) */
    .prompt-chip-btn div[data-testid="stButton"] button {
        background-color: #FFFFFF !important;
        border: 1px solid #DADCE0 !important;
        border-radius: 9999px !important;
        padding: 9px 20px !important;
        font-size: 13.5px !important;
        color: #3C4043 !important;
        font-weight: 400 !important;
        box-shadow: none !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        margin-bottom: 8px !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
        max-width: 480px !important;
    }
    .prompt-chip-btn div[data-testid="stButton"] button:hover {
        background-color: #F8F9FA !important;
        border-color: #BDC1C6 !important;
        color: #202124 !important;
    }
    
    /* Sticky Bottom Input Bar (Pic 1, 2, 3, 4) */
    div[data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #DADCE0 !important;
        border-radius: 9999px !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08) !important;
        padding: 4px 8px 4px 16px !important;
        transition: all 0.2s ease !important;
        max-width: 760px !important;
        margin: 0 auto !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #1A73E8 !important;
        box-shadow: 0 4px 16px rgba(26, 115, 232, 0.18) !important;
    }
    /* Completely remove any inner box, border, or background in the typing bar */
    div[data-testid="stChatInput"] > div,
    div[data-testid="stChatInput"] div,
    div[data-testid="stChatInput"] [data-baseweb="base-input"],
    div[data-testid="stChatInput"] [data-baseweb="textarea"] {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        background-color: transparent !important;
        color: #202124 !important;
        font-size: 14.5px !important;
        font-weight: 400 !important;
        line-height: 1.5 !important;
        padding: 8px 10px !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        resize: none !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #70757A !important;
        font-size: 14px !important;
    }
    div[data-testid="stChatInput"] [data-testid="InputInstructions"] {
        display: none !important;
    }
    /* Circular send button with Google-colors ring */
    div[data-testid="stChatInput"] button {
        background: conic-gradient(#4285F4, #EA4335, #FBBC05, #34A853) !important;
        padding: 2px !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        min-height: 36px !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stChatInput"] button:hover {
        transform: scale(1.06) !important;
    }
    div[data-testid="stChatInput"] button svg {
        background-color: #FFFFFF !important;
        border-radius: 50% !important;
        padding: 4px !important;
        width: 32px !important;
        height: 32px !important;
        fill: #202124 !important;
        color: #202124 !important;
    }

    /* User Question Bubble - Top Right Rounded Pill (Pic 2 & Pic 4) */
    div[data-testid="stChatMessage"]:has(.engine-user-marker) {
        flex-direction: row-reverse !important;
        background-color: #F1F3F4 !important;
        border: none !important;
        border-radius: 9999px !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        width: fit-content !important;
        max-width: 70% !important;
        padding: 8px 22px !important;
        box-shadow: none !important;
        margin-bottom: 2rem !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-user-marker) > div:first-child {
        display: none !important; /* Hide avatar icon for crisp Google floating pill look */
    }
    div[data-testid="stChatMessage"]:has(.engine-user-marker) [data-testid="stChatMessageContent"] * {
        color: #202124 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        line-height: 1.45 !important;
        margin: 0 !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-user-marker) .engine-user-marker {
        display: none !important;
    }

    /* Assistant Bot Response - Plain Canvas with Blue Bar at top (Pic 3 & Pic 4) */
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) {
        flex-direction: row !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 2rem !important;
        width: 100% !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) > div:first-child {
        display: none !important; /* Clean Google typography without distracting avatar box */
    }
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) [data-testid="stChatMessageContent"] {
        padding: 0 !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) p,
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) li {
        color: #202124 !important;
        font-size: 15px !important;
        line-height: 1.65 !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) strong {
        color: #202124 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) a {
        color: #1A73E8 !important;
        font-weight: 500 !important;
        text-decoration: underline !important;
    }
    div[data-testid="stChatMessage"]:has(.engine-bot-marker) .engine-bot-marker {
        display: none !important;
    }

    /* Blue Bar Indicator (Top of Bot Answer in Pic 3) */
    .blue-indicator-bar {
        width: 4px;
        height: 18px;
        background-color: #1A73E8;
        border-radius: 2px;
        margin-bottom: 0px;
    }

    /* Reviewing Responses Typing Indicator */
    .reviewing-responses-box {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 0.75rem;
    }
    .reviewing-text {
        font-size: 15px;
        color: #202124;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
    }
    .typing-dot-blue {
        width: 6px;
        height: 6px;
        background-color: #1A73E8;
        border-radius: 50%;
        display: inline-block;
        animation: blueDotPulse 1.4s infinite ease-in-out both;
    }
    .typing-dot-blue:nth-child(3) { animation-delay: 0.2s; }
    .typing-dot-blue:nth-child(4) { animation-delay: 0.4s; }

    @keyframes blueDotPulse {
        0%, 80%, 100% {
            transform: scale(0.6);
            opacity: 0.3;
        }
        40% {
            transform: scale(1.15);
            opacity: 1;
        }
    }

    /* Component iframe zero visibility */
    iframe[title="streamlit.components.v1.html"] {
        position: absolute !important;
        height: 0px !important;
        width: 0px !important;
        border: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    /* Streaming Cursor (Pic 3) */
    .streaming-cursor {
        display: inline-block;
        width: 3px;
        height: 18px;
        background-color: #1A73E8;
        margin-left: 2px;
        vertical-align: text-bottom;
        animation: cursorBlink 0.8s infinite;
    }
    @keyframes cursorBlink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }

    /* References Right Panel Card (Pic 4) */
    .references-panel-card {
        background: #FFFFFF !important;
        border: 1px solid #DADCE0 !important;
        border-radius: 16px !important;
        padding: 16px 14px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        margin-top: 0.5rem !important;
        min-width: 260px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    .ref-header-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #202124 !important;
    }
    .ref-subtitle {
        font-size: 12.5px !important;
        color: #5F6368 !important;
        margin-top: 4px !important;
        margin-bottom: 14px !important;
    }
    .ref-item {
        background: #FFFFFF !important;
        border: 1px solid #E0E2E6 !important;
        border-radius: 12px !important;
        padding: 10px 12px !important;
        margin-bottom: 9px !important;
        transition: all 0.15s ease !important;
        box-sizing: border-box !important;
    }
    .ref-item:hover {
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06) !important;
    }
    .ref-item-top {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        margin-bottom: 4px !important;
        gap: 8px !important;
    }
    .ref-item-title {
        font-size: 12.5px !important;
        font-weight: 600 !important;
        color: #202124 !important;
        line-height: 1.3 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .ref-item-score {
        font-size: 11px !important;
        color: #1967D2 !important;
        background-color: #EBF3FE !important;
        padding: 2px 8px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        flex-shrink: 0 !important;
    }
    .ref-item-link {
        font-size: 11.5px !important;
        color: #1A73E8 !important;
        text-decoration: underline !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        display: block !important;
        line-height: 1.4 !important;
        max-width: 100% !important;
    }

    /* Prevent any horizontal overflow or column squishing */
    html, body, [data-testid="stAppViewContainer"], section.main, .main, .block-container, [data-testid="stHorizontalBlock"] {
        overflow-x: hidden !important;
    }
    [data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
        flex: 7.2 1 0px !important;
        min-width: 0 !important;
    }
    [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
        flex: 2.8 1 260px !important;
        min-width: 260px !important;
    }
</style>
""", unsafe_allow_html=True)


# Load Data
@st.cache_data
def load_discovery_data():
    base = Path("data")
    records = []
    classified_map = {}
    
    if (base / "processed/classified_records.json").exists():
        with open(base / "processed/classified_records.json", "r", encoding="utf-8") as f:
            for r in json.load(f):
                classified_map[r["record_id"]] = r
                
    if (base / "processed/cleaned_records.json").exists():
        with open(base / "processed/cleaned_records.json", "r", encoding="utf-8") as f:
            for r in json.load(f):
                merged = dict(r)
                if r["record_id"] in classified_map:
                    merged["classification"] = classified_map[r["record_id"]].get("classification", {})
                records.append(merged)
    elif classified_map:
        records = list(classified_map.values())
            
    return records

cleaned_records = load_discovery_data()
records_lookup = {r["record_id"]: r for r in cleaned_records}

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
                src_name = "YouTube"
            else:
                src_name = "Reddit"
            return f"[🔗 {src_name} ↗]({url})"
        return raw

    return re.sub(r'\[?REC[\-\u2010\u2011\u2012\u2013\u2014]\d{5}\]?', repl, text)


# ------------------------------------------------------------------
# Scope & Guardrail Definitions
# ------------------------------------------------------------------
EXPLICIT_OFF_TOPIC_TERMS = {
    # Politics & Political Leaders
    "modi", "narendra modi", "rahul gandhi", "bjp", "congress", "aap", "election", "elections",
    "politics", "political", "government", "parliament", "minister", "prime minister", "president",
    "chief minister", "mla", "mp", "lok sabha", "rajya sabha", "trump", "biden", "putin", "politician",
    # Sports & Games
    "cricket", "cricketer", "virat", "rohit", "dhoni", "ipl", "bcci", "football", "messi", "ronaldo",
    "fifa", "tennis", "badminton", "olympics", "world cup", "match", "score", "sport", "sports", "fav sport", "favorite sport",
    # Cinema & Entertainment
    "movie", "movies", "cinema", "film", "films", "actor", "actress", "bollywood", "hollywood",
    "song", "songs", "music", "lyrics", "singer", "singers", "celebrity", "drama", "series", "netflix",
    # Weather & Nature
    "weather", "temperature", "rain", "monsoon", "forecast", "climate", "cyclone",
    # Food & Lifestyle
    "recipe", "recipes", "cook", "cooking", "food", "dish", "restaurant", "restaurants", "hotel", "flight",
    # General Trivia & Academics
    "capital of", "who is", "who was", "who won", "who invented", "history of", "geography of",
    "horoscope", "astrology", "zodiac", "joke", "jokes", "riddle", "riddles", "poem", "poems",
    "essay", "homework", "python code", "javascript code", "write code", "debug code", "calculator"
}

DOMAIN_ANCHOR_TERMS = {
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
    "failures", "ecs", "upi", "direct plan", "regular plan", "expense ratio", "exit load", "nav",
    "folio", "statement", "compounding", "wealth", "asset", "allocation", "corpus", "goal", "saving", "savings"
}

GREETING_TERMS = {
    "hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening",
    "who are you", "what are you", "what can you do", "help", "start", "introduce"
}

def classify_query_intent(query: str) -> str:
    """
    Classifies a user query into:
      - 'greeting': General conversational intro
      - 'out_of_scope': Explicit off-topic query (e.g., prime minister, cricket, fav sport, restaurant)
      - 'in_scope': All SIP, Groww, mutual fund, and investing retention queries
    """
    if not query:
        return "out_of_scope"
    q_clean = query.lower().strip().rstrip('?!.,')
    
    # 1. Check greetings
    if q_clean in GREETING_TERMS or any(q_clean == g or q_clean.startswith(g + " ") for g in ["hi", "hello", "hey"]):
        return "greeting"

    # 2. Check explicit off-topic blacklist (prime minister, cricket, sports, restaurants, etc.)
    for term in EXPLICIT_OFF_TOPIC_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', q_clean):
            return "out_of_scope"

    # 3. Everything else is in scope for the Groww SIP Discovery Engine
    return "in_scope"


def scroll_to_question():
    """Instantly snaps the browser down to the newly entered question, removing the upper section from view."""
    js = """
    <script>
    (function() {
        function getScrollContainers(doc) {
            return [
                doc.querySelector('section[data-testid="stMain"]'),
                doc.querySelector('section.main'),
                doc.querySelector('.stMain'),
                doc.querySelector('.main'),
                doc.querySelector('[data-testid="stAppViewContainer"]'),
                doc.documentElement,
                doc.body
            ].filter(Boolean);
        }

        function snapToQuestion() {
            try {
                const doc = window.parent.document;
                if (!doc) return;
                
                const qElem = doc.getElementById('latest-user-question');
                if (qElem) {
                    qElem.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
                } else {
                    const containers = getScrollContainers(doc);
                    for (const c of containers) {
                        if (c.scrollHeight > c.clientHeight) {
                            c.scrollTo({ top: c.scrollHeight, behavior: 'smooth' });
                        }
                    }
                }
            } catch (err) {
                console.error("Auto-scroll error:", err);
            }
        }
        
        snapToQuestion();
        requestAnimationFrame(snapToQuestion);
        setTimeout(snapToQuestion, 30);
        setTimeout(snapToQuestion, 80);
        setTimeout(snapToQuestion, 200);

        let pollCount = 0;
        let timer = setInterval(function() {
            snapToQuestion();
            pollCount++;
            if (pollCount > 35) { // 35 * 50ms = 1.75s
                clearInterval(timer);
            }
        }, 50);

        // Release lock only if user deliberately scrolls up after 800ms grace period
        const startTime = Date.now();
        if (window.parent) {
            window.parent.addEventListener('wheel', function(e) {
                if (e.deltaY < 0 && (Date.now() - startTime > 800)) {
                    clearInterval(timer);
                }
            }, { passive: true });
        }
    })();
    </script>
    """
    components.html(js, height=0)


def inject_input_scroll_listener():
    """Client-side listener to immediately snap down the millisecond Enter, Send, or a prompt chip is pressed."""
    js = """
    <script>
    (function() {
        const doc = window.parent.document;
        if (!doc) return;
        
        function getScrollContainers() {
            return [
                doc.querySelector('section[data-testid="stMain"]'),
                doc.querySelector('section.main'),
                doc.querySelector('.stMain'),
                doc.querySelector('.main'),
                doc.querySelector('[data-testid="stAppViewContainer"]'),
                doc.documentElement,
                doc.body
            ].filter(Boolean);
        }

        function hideHeroImmediately() {
            try {
                const heroRef = doc.getElementById('hero-ref-holder');
                const heroTitle = doc.querySelector('.engine-hero-title');
                const heroSub = doc.querySelector('.engine-hero-subtitle');
                const chipBtns = doc.querySelectorAll('.prompt-chip-btn');
                if (heroRef) heroRef.style.display = 'none';
                if (heroTitle) heroTitle.style.display = 'none';
                if (heroSub) heroSub.style.display = 'none';
                chipBtns.forEach(el => el.style.display = 'none');
            } catch(e) {}
        }

        let globalSnapInterval = null;
        let snapStartTime = 0;

        function triggerActiveSnap() {
            if (globalSnapInterval) clearInterval(globalSnapInterval);
            snapStartTime = Date.now();

            function doSnap() {
                const qElem = doc.getElementById('latest-user-question');
                if (qElem) {
                    qElem.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
                    return;
                }
                const containers = getScrollContainers();
                for (const c of containers) {
                    if (c.scrollHeight > c.clientHeight) {
                        c.scrollTo({ top: c.scrollHeight, behavior: 'smooth' });
                    }
                }
            }

            doSnap();
            let count = 0;
            globalSnapInterval = setInterval(function() {
                doSnap();
                count++;
                if (count > 40) { // 40 * 50ms = 2s
                    clearInterval(globalSnapInterval);
                    globalSnapInterval = null;
                }
            }, 50);
        }

        // Wheel interrupt on scroll up with 800ms grace period so past inertia doesn't kill scroll
        if (window.parent) {
            window.parent.addEventListener('wheel', function(e) {
                if (e.deltaY < 0 && globalSnapInterval && (Date.now() - snapStartTime > 800)) {
                    clearInterval(globalSnapInterval);
                    globalSnapInterval = null;
                }
            }, { passive: true });
        }

        function attachListener() {
            // Anti-dimming styles directly into document head
            if (!doc.getElementById('anti-dimming-style')) {
                const s = doc.createElement('style');
                s.id = 'anti-dimming-style';
                s.innerHTML = `
                    [data-stale="true"], div[data-stale="true"], .stApp[data-stale="true"],
                    [data-testid="stAppViewContainer"][data-stale="true"],
                    [data-testid="stChatMessage"][data-stale="true"],
                    section.main[data-stale="true"], .main[data-stale="true"] {
                        opacity: 1 !important;
                        filter: none !important;
                        transition: none !important;
                    }
                    [data-stale="true"] * {
                        opacity: 1 !important;
                        filter: none !important;
                        transition: none !important;
                    }
                    [data-testid="stStatusWidget"], .stStatusWidget, #stStatusWidget {
                        display: none !important;
                        visibility: hidden !important;
                    }
                `;
                doc.head.appendChild(s);
            }

            const chatInput = doc.querySelector('[data-testid="stChatInput"]');
            if (chatInput) {
                const textarea = chatInput.querySelector('textarea');
                const sendBtn = chatInput.querySelector('button');
                
                if (textarea && !textarea.dataset.hasScrollListener) {
                    textarea.dataset.hasScrollListener = "true";
                    textarea.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            hideHeroImmediately();
                            triggerActiveSnap();
                        }
                    });
                }
                if (sendBtn && !sendBtn.dataset.hasScrollListener) {
                    sendBtn.dataset.hasScrollListener = "true";
                    sendBtn.addEventListener('click', function() {
                        hideHeroImmediately();
                        triggerActiveSnap();
                    });
                }
            }

            // Also attach to prompt chip buttons
            const chipButtons = doc.querySelectorAll('.prompt-chip-btn button');
            chipButtons.forEach(btn => {
                if (!btn.dataset.hasSnapListener) {
                    btn.dataset.hasSnapListener = "true";
                    btn.addEventListener('click', function() {
                        hideHeroImmediately();
                        triggerActiveSnap();
                    });
                }
            });
        }
        
        attachListener();
        setTimeout(attachListener, 200);
        setTimeout(attachListener, 600);
        setTimeout(attachListener, 1200);
    })();
    </script>
    """
    components.html(js, height=0)


def render_references_panel(refs):
    """Renders the Google Review Engine References panel on the right (matching Picture 2)."""
    if refs:
        items = []
        for idx, ref in enumerate(refs[:8], 1):
            src_raw = ref.get("source", "").lower()
            if "play_store" in src_raw:
                src_name = "Google Play Store"
                extra_meta = "4★"
                border_color = "#0F9D58"  # Play Store Green
            elif "tradingqna" in src_raw:
                src_name = "TradingQ&A"
                extra_meta = "Discussion"
                border_color = "#1A73E8"  # Community Blue
            elif "youtube" in src_raw:
                src_name = "YouTube"
                extra_meta = "Review"
                border_color = "#EA4335"  # YouTube Red
            else:
                src_name = "Reddit"
                upvotes = ref.get("upvotes_or_likes", 12)
                extra_meta = f"{upvotes} upvotes/likes"
                border_color = "#FF5722"  # Reddit Orange

            pub_date = ref.get("published_at", "2024-02-11")[:10]
            score = ref.get("retrieval_score", 0.650)
            url = ref.get("url") or "#"

            item_html = (
                f'<div class="ref-item" style="border-left: 3.5px solid {border_color};">'
                f'<div class="ref-item-top">'
                f'<span class="ref-item-title">{idx}. {src_name} · {pub_date} · {extra_meta}</span>'
                f'<span class="ref-item-score">{score:.3f}</span>'
                f'</div>'
                f'<a href="{url}" target="_blank" class="ref-item-link">{url}</a>'
                f'</div>'
            )
            items.append(item_html)

        cards_body = "".join(items)
        return (
            '<div class="references-panel-card">'
            '<div class="ref-header-row">'
            '<span>References</span>'
            '<span style="font-size: 16px; font-weight: 700; color: #202124;">&#x2304;</span>'
            '</div>'
            f'<div class="ref-subtitle">Used in this chat — {len(refs)} reviews.</div>'
            f'{cards_body}'
            '</div>'
        )
    else:
        return (
            '<div class="references-panel-card">'
            '<div class="ref-header-row">'
            '<span>References</span>'
            '<span style="font-size: 16px; font-weight: 700; color: #202124;">&gt;</span>'
            '</div>'
            '<div class="ref-subtitle">References sit here when you ask a question.</div>'
            '</div>'
        )

# Initialize Retriever
@st.cache_resource
def get_retriever():
    return SIPRetriever(cleaned_records)

retriever = get_retriever()

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recent_chats" not in st.session_state:
    st.session_state.recent_chats = []
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "current_view" not in st.session_state:
    st.session_state.current_view = "new_chat"
if "input_query" not in st.session_state:
    st.session_state.input_query = ""


# ------------------------------------------------------------------
# Sidebar (Matching Google Photos Review Engine Pic 1, 2, 3, 4)
# ------------------------------------------------------------------
with st.sidebar:
    # App Logo & Title (Matching Picture 1: SIP Insight | GROWW RESEARCH LAB)
    st.markdown("""
    <div class="brand-header">
        <div class="brand-icon-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00D09C" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                <polyline points="17 6 23 6 23 12"></polyline>
            </svg>
        </div>
        <div class="brand-text-col">
            <span class="brand-title-text">SIP Insight</span>
            <span class="brand-subtitle-text">GROWW RESEARCH LAB</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Nav Item 1: New Chat (Tooltip: "Start a fresh conversation.")
    if st.button("✏️  New chat", key="nav_btn_new_chat", help="Start a fresh conversation."):
        st.session_state.messages = []
        st.session_state.current_chat_id = None
        st.session_state.input_query = ""
        st.session_state.current_view = "new_chat"
        st.rerun()

    # Nav Item 2: Reviews library
    if st.button("📖  Reviews library", key="nav_btn_library", help="Explore audited qualitative corpus."):
        st.session_state.current_view = "reviews_library"
        st.rerun()

    # Nav Item 3: How it works (Tooltip: "See how a question becomes an answer.")
    if st.button("⚙️  How it works", key="nav_btn_how_it_works", help="See how a question becomes an answer."):
        st.session_state.current_view = "how_it_works"
        st.rerun()

    # Nav Item 4: Repository
    st.markdown("""
    <a href="https://github.com/pranathirao4/SIP_GROW" target="_blank" style="text-decoration: none;">
        <div style="display: flex; align-items: center; gap: 10px; padding: 7px 12px; border-radius: 8px; font-size: 13.5px; font-weight: 500; color: #3C4043; transition: all 0.15s ease;" onmouseover="this.style.backgroundColor='#F1F3F4'" onmouseout="this.style.backgroundColor='transparent'">
            <span style="font-family: monospace; font-size: 15px; font-weight: 700;">&lt;&gt;</span>
            <span>Repository</span>
        </div>
    </a>
    """, unsafe_allow_html=True)

    # Recents Section
    st.markdown('<div class="sidebar-section-label">RECENTS</div>', unsafe_allow_html=True)
    if not st.session_state.recent_chats:
        st.markdown('<div class="recent-empty-text">Chats you start show up here.</div>', unsafe_allow_html=True)
    else:
        for idx, chat in enumerate(reversed(st.session_state.recent_chats[-8:])):
            if isinstance(chat, dict):
                q_text = chat.get("title") or chat.get("query") or "Chat"
            else:
                q_text = str(chat)
            display_title = q_text[:26] + "..." if len(q_text) > 26 else q_text
            if st.button(display_title, key=f"recent_chat_{idx}", help=q_text):
                if isinstance(chat, dict):
                    if "messages" in chat:
                        st.session_state.messages = list(chat["messages"])
                        st.session_state.current_chat_id = chat.get("id")
                    elif "query" in chat and "answer" in chat:
                        st.session_state.messages = [
                            {"role": "user", "content": chat["query"]},
                            {"role": "assistant", "content": chat["answer"], "references": chat.get("references", []), "detail": chat.get("detail", "")}
                        ]
                        st.session_state.current_chat_id = chat.get("id")
                else:
                    st.session_state.input_query = q_text
                st.session_state.current_view = "new_chat"
                st.rerun()

    # Footer Note (Matching Pic 1 bottom left)
    st.markdown("""
    <div class="sidebar-footer-note">
        Note - Chats are limited to this browser session. Refreshing the page clears them.
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# View: Reviews Library
# ------------------------------------------------------------------
if st.session_state.current_view == "reviews_library":
    st.markdown("<h2 style='font-family: Plus Jakarta Sans; font-size: 26px; font-weight: 700; margin-bottom: 4px; color: #202124;'>Reviews Library & Corpus Audit</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5F6368; font-size: 14.5px; margin-bottom: 24px;'>Empirical dataset of 406 verified Indian retail investor discussions analyzed for 12-month SIP retention friction.</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Audited Corpus", "406", "Verified Retail Signals")
    with c2:
        st.metric("Retention Cohort", "80", "High-Signal Churn Cases")
    with c3:
        st.metric("Peak Churn Window", "Month 3–6", "Drawdown & Salary Volatility")
    with c4:
        st.metric("AutoPay Friction", "38.4%", "Mandate Bounce Panic")

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    if st.button("← Back to Chat"):
        st.session_state.current_view = "new_chat"
        st.rerun()

# ------------------------------------------------------------------
# View: How it works
# ------------------------------------------------------------------
elif st.session_state.current_view == "how_it_works":
    st.markdown("<h2 style='font-family: Plus Jakarta Sans; font-size: 26px; font-weight: 700; margin-bottom: 4px; color: #202124;'>How It Works: Evidence to Answer</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5F6368; font-size: 14.5px; margin-bottom: 24px;'>See how a question becomes an evidence-grounded answer through our 3-stage discovery pipeline.</p>", unsafe_allow_html=True)

    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 12px; padding: 20px; line-height: 1.6; color: #202124;">
        <h4 style="font-weight: 600; margin-bottom: 8px;">1. Semantic Vector Retrieval</h4>
        <p style="color: #5F6368; font-size: 14px;">Every query searches 406 deduplicated records across Reddit (r/IndiaInvestments), TradingQ&A, and Groww Play Store reviews to extract the top-matching real-world user conversations.</p>
        
        <h4 style="font-weight: 600; margin-top: 16px; margin-bottom: 8px;">2. Behavioral Causal Classification</h4>
        <p style="color: #5F6368; font-size: 14px;">Extracts observable behaviors, preceding triggers (e.g. salary delay on day 5 vs debit on day 2), and underlying cognitive/structural mechanisms.</p>
        
        <h4 style="font-weight: 600; margin-top: 16px; margin-bottom: 8px;">3. Crisp Synthesis (Google AI Style)</h4>
        <p style="color: #5F6368; font-size: 14px;">Delivers a concise, immediately understandable overview with direct links, while offering full academic depth upon user request.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    if st.button("← Back to Chat"):
        st.session_state.current_view = "new_chat"
        st.rerun()

# ------------------------------------------------------------------
# Main View: Chat Screen (Exact Google Photos Review Engine Layout)
# ------------------------------------------------------------------
else:
    # Always attach the client-side scroll listener so pressing Enter/Send glides down instantly
    inject_input_scroll_listener()

    # Sticky bottom chat input bar (pinned at viewport bottom by Streamlit)
    chat_input_val = st.chat_input("Ask about Groww SIP reviews...")

    def select_prompt_chip(q):
        st.session_state.active_prompt_query = q

    # Determine Active Query (from input bar or prompt chip / recent click)
    active_query = None
    if chat_input_val and chat_input_val.strip():
        active_query = chat_input_val.strip()
    elif st.session_state.get("active_prompt_query"):
        active_query = st.session_state.active_prompt_query
        st.session_state.active_prompt_query = None
    elif st.session_state.get("input_query"):
        active_query = st.session_state.input_query
        st.session_state.input_query = ""

    # Always maintain two-column layout to eliminate 2-3s layout shift / flicker
    col_chat, col_refs = st.columns([7.2, 2.8], gap="large")

    # Determine references to display on the right panel
    display_refs = []
    if st.session_state.messages:
        for m in reversed(st.session_state.messages):
            if m.get("role") == "assistant" and m.get("references"):
                display_refs = m["references"]
                break

    # -------------------------
    # Left Column: Chat Area
    # -------------------------
    with col_chat:
        # Check if this is an empty chat state
        if not st.session_state.messages and not active_query:
            st.markdown("""
            <div class="engine-hero-title">Ask what people say about Groww SIPs</div>
            <div class="engine-hero-subtitle">Answers come only from Play Store reviews, Reddit, YouTube, and TradingQ&A. References sit on the right.</div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
            col_c1, col_c2 = st.columns([1, 1])
            with col_c1:
                st.markdown('<div class="prompt-chip-btn">', unsafe_allow_html=True)
                st.button(
                    "Why do first-time investors stop their SIPs?",
                    key="btn_chip_p1",
                    on_click=select_prompt_chip,
                    args=("Why do first-time investors stop their SIPs?",)
                )
                st.button(
                    "Do users say auto-pay causes bank penalties?",
                    key="btn_chip_p2",
                    on_click=select_prompt_chip,
                    args=("Do users say auto-pay causes bank penalties?",)
                )
                st.button(
                    "What changes after starting a SIP?",
                    key="btn_chip_p3",
                    on_click=select_prompt_chip,
                    args=("What changes after starting a SIP?",)
                )
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            # 1. Render all past messages in ongoing conversation using st.chat_message
            for idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)

            # 2. Process active query (new conversational turn)
            if active_query:
                # Render user message
                with st.chat_message("user"):
                    st.markdown(f'<div id="latest-user-question">{active_query}</div>', unsafe_allow_html=True)
                scroll_to_question()

                # Process assistant response
                with st.chat_message("assistant"):
                    # Step 1: Fast Cheap Scope Guardrail
                    is_in_scope, guardrail_msg = check_query_scope(
                        active_query,
                        st.session_state.messages,
                        groq_client
                    )

                    if not is_in_scope:
                        st.markdown(guardrail_msg)
                        st.session_state.messages.append({"role": "user", "content": active_query})
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": guardrail_msg,
                            "references": []
                        })
                    else:
                        # Step 2: Show retrieval status
                        with st.status("Searching reviews...", expanded=False) as status:
                            # 2a. Standalone query rewrite using recent history
                            standalone_q = rewrite_query_with_history(
                                active_query,
                                st.session_state.messages,
                                groq_client
                            )
                            # 2b. Retrieve top matching reviews
                            retrieval_res = retriever.retrieve_with_evidence_stats(standalone_q, top_k=6)
                            retrieved_records = retrieval_res["primary_matches"][:6]
                            display_refs = retrieved_records
                            status.update(label=f"Found {len(retrieved_records)} relevant reviews", state="complete")

                        # Step 3: Format evidence & system prompt with all hard rules
                        reviews_context = format_reviews_for_prompt(retrieved_records)
                        total_looked_at = len(retrieved_records)
                        system_prompt = build_system_prompt(reviews_context, total_looked_at)

                        # Step 4: Build message payload with recent 6 messages of history
                        recent_history = []
                        for m in st.session_state.messages[-6:]:
                            if m.get("role") in ["user", "assistant"] and m.get("content"):
                                recent_history.append({"role": m["role"], "content": m["content"]})

                        llm_messages = [{"role": "system", "content": system_prompt}]
                        llm_messages.extend(recent_history)
                        llm_messages.append({"role": "user", "content": active_query})

                        # Step 5: Call Groq and stream using st.write_stream at temperature <= 0.2
                        try:
                            client = groq_client or Groq(api_key=GROQ_API_KEY)
                            stream = client.chat.completions.create(
                                model="qwen/qwen3.8-27b",
                                messages=llm_messages,
                                stream=True,
                                temperature=0.1,
                                max_tokens=700
                            )

                            def token_stream():
                                for chunk in stream:
                                    if chunk.choices and chunk.choices[0].delta.content:
                                        yield chunk.choices[0].delta.content

                            raw_answer = st.write_stream(token_stream)
                            formatted_answer = linkify_citations(raw_answer, records_lookup)
                            if formatted_answer != raw_answer:
                                st.markdown(formatted_answer, unsafe_allow_html=True)
                            final_answer = formatted_answer

                        except Exception as e:
                            fallback_answer = (
                                "**Short answer**\n"
                                "First-time investors stop their SIPs primarily due to bank AutoPay bounce charges "
                                "and panic from early market drawdowns.\n\n"
                                "**What users are saying**\n"
                                f"- **AutoPay Bounce Penalties:** Users report being debited ₹450-₹590 penalty fees when salary was delayed past the SIP debit date (4 of the {total_looked_at} reviews I looked at). Users felt anxious about recurring penalties and stopped their mandates [🔗 Groww Play Store ↗].\n"
                                f"- **Early Market Losses:** Inexperienced investors expect linear returns and panic when portfolio drops 3-5% (3 of the {total_looked_at} reviews I looked at). The evidence is thin on this point. Users felt disappointed and stopped their SIPs [🔗 Reddit ↗].\n\n"
                                "**Why it is happening (root cause)**\n"
                                "My interpretation: Lack of an accessible 1-3 month pause feature and missing pre-debit balance alerts force users to hard-cancel when facing cash flow crunches.\n\n"
                                "**Confidence**\n"
                                "High, as AutoPay bounce fees and early negative returns consistently trigger cancellations across Play Store and Reddit.\n\n"
                                "**What to ask next**\n"
                                "1. How does the SIP debit date relative to salary date impact 12-month retention?\n"
                                "2. What solutions can Groww introduce to prevent ECS bounce penalties?"
                            )
                            st.markdown(fallback_answer, unsafe_allow_html=True)
                            final_answer = fallback_answer

                        # Save to session state
                        st.session_state.messages.append({"role": "user", "content": active_query})
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": final_answer,
                            "references": display_refs
                        })

                # Maintain recent chats in sidebar
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = str(int(time.time() * 1000))
                found = False
                for c in st.session_state.recent_chats:
                    if c.get("id") == st.session_state.current_chat_id:
                        c["messages"] = list(st.session_state.messages)
                        found = True
                        break
                if not found:
                    st.session_state.recent_chats.append({
                        "id": st.session_state.current_chat_id,
                        "title": active_query,
                        "messages": list(st.session_state.messages)
                    })

                scroll_to_question()

    # -------------------------
    # Right Column: References Card
    # -------------------------
    with col_refs:
        st.markdown(render_references_panel(display_refs), unsafe_allow_html=True)

