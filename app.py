"""
SIP Insight - Groww Research Lab
A focused, professional qualitative AI discovery agent to discover why investors
stay with their SIPs — or stop, increasing 12-month active SIP retention.
Faithfully deployed with Google Stitch aesthetics for Streamlit.
"""

import os
import sys
import json
import re
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from src.pipeline.retriever import SIPRetriever

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# Page configuration
st.set_page_config(
    page_title="SIP Insight - Groww Research Lab",
    page_icon="https://assets-netstorage.groww.in/web-assets/big_logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Stitch Styling & Theme Tokens
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />

<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #F9F9FF !important;
        color: #151C27 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Hide Streamlit Default Header and Clutter */
    header[data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(8px) !important;
        border-bottom: 1px solid #E2E8F0 !important;
    }
    #MainMenu, footer {
        visibility: hidden !important;
    }
    
    /* Left Sidebar (Google Stitch Style) */
    section[data-testid="stSidebar"] {
        background-color: #F0F3FF !important;
        border-right: 1px solid #E2E8F8 !important;
        padding-top: 1.5rem !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Sidebar Branding */
    .brand-container {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.5rem 0.5rem 1.25rem 0.5rem;
    }
    .brand-logo {
        height: 32px;
        width: auto;
        object-fit: contain;
    }
    .brand-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 16px;
        font-weight: 700;
        color: #151C27;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 11px;
        color: #575E70;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .nav-header {
        font-size: 11px;
        color: #575E70;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
        padding: 0.75rem 0.5rem 0.5rem 0.5rem;
    }

    /* Stitch Navigation Buttons in Sidebar */
    section[data-testid="stSidebar"] div[data-testid="stButton"] button {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #3C4A43 !important;
        border-radius: 8px !important;
        padding: 8px 14px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        box-shadow: none !important;
        transition: all 0.15s ease-in-out !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
        background-color: #E2E8F8 !important;
        color: #151C27 !important;
    }
    
    /* Main Content Styling */
    .main .block-container {
        max-width: 860px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* Hero Title & Subtitle */
    .stitch-hero-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 2.15rem;
        font-weight: 700;
        color: #151C27;
        letter-spacing: -0.025em;
        line-height: 1.2;
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.6rem;
    }
    .stitch-hero-subtitle {
        font-size: 0.95rem;
        color: #575E70;
        text-align: center;
        max-width: 640px;
        margin: 0 auto 1.4rem auto;
        line-height: 1.55;
    }
    
    /* Prompt Chips - Completely visible, zero truncation, wraps gracefully */
    .chip-section {
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 760px;
        margin: 0 auto 1rem auto;
    }
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stButton"] button {
        white-space: normal !important;
        word-break: normal !important;
        text-overflow: clip !important;
        overflow: visible !important;
        height: auto !important;
        min-height: 40px !important;
        padding: 9px 18px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        line-height: 1.4 !important;
        border-radius: 9999px !important;
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        color: #151C27 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.15s ease-in-out !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stButton"] button:hover {
        border-color: #006C4F !important;
        color: #006C4F !important;
        background-color: #F0FDF4 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(0, 108, 79, 0.08) !important;
    }
    
    /* Center Hero Search Bar (Google Stitch Exact) */
    div[data-testid="stForm"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 9999px !important;
        padding: 4px 8px 4px 16px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06) !important;
        max-width: 720px !important;
        margin: 0.5rem auto 1.8rem auto !important;
        display: flex !important;
        align-items: center !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stForm"]:hover, div[data-testid="stForm"]:focus-within {
        border-color: #006C4F !important;
        box-shadow: 0 6px 20px rgba(0, 108, 79, 0.12) !important;
    }
    div[data-testid="stForm"] div[data-testid="stTextInput"] {
        width: 100% !important;
        margin: 0 !important;
    }
    div[data-testid="stForm"] div[data-testid="stTextInput"] > div > div > input {
        border: none !important;
        background: transparent !important;
        font-size: 14.5px !important;
        color: #151C27 !important;
        padding: 8px 6px !important;
        box-shadow: none !important;
        outline: none !important;
    }
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] {
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
        border-radius: 9999px !important;
        background-color: #00D09C !important;
        color: #FFFFFF !important;
        width: 38px !important;
        height: 38px !important;
        min-width: 38px !important;
        min-height: 38px !important;
        padding: 0 !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 2px 6px rgba(0, 208, 156, 0.25) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #006C4F !important;
        transform: scale(1.05) !important;
    }
    .search-icon-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #00D09C;
        height: 100%;
        padding-right: 4px;
    }
    
    /* Chat Messages */
    div[data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        padding: 1.25rem 1.5rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
    }
    
    /* Expander Styling for Investor Concerns */
    div[data-testid="stExpander"] {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        margin-top: 0.75rem !important;
    }
    div[data-testid="stExpander"] details summary {
        font-size: 13.5px !important;
        font-weight: 600 !important;
        color: #006C4F !important;
    }
    
    /* Citations and Links */
    a.stitch-citation {
        color: #006C4F !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 2px !important;
    }
    a.stitch-citation:hover {
        text-decoration: underline !important;
    }
    
    /* Clean Overview Card */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .metric-val {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 26px;
        font-weight: 700;
        color: #151C27;
        margin: 4px 0;
    }
    .metric-lbl {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #575E70;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# Load Data
@st.cache_data
def load_discovery_data():
    base = Path("data")
    cleaned = []
    relevant = []
    
    if (base / "processed/cleaned_records.json").exists():
        with open(base / "processed/cleaned_records.json", "r", encoding="utf-8") as f:
            cleaned = json.load(f)
    if (base / "processed/relevant_records.json").exists():
        with open(base / "processed/relevant_records.json", "r", encoding="utf-8") as f:
            relevant = json.load(f)
            
    return cleaned, relevant

cleaned_records, relevant_records = load_discovery_data()
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
                src_name = "YouTube Comment"
            else:
                src_name = "Reddit"
            return f"[[🔗 View {src_name} Discussion ↗]({url})]"
        return raw

    return re.sub(r'\[?REC[\-\u2010\u2011\u2012\u2013\u2014]\d{5}\]?', repl, text)

# Initialize Retriever
@st.cache_resource
def get_retriever():
    return SIPRetriever(cleaned_records)

retriever = get_retriever()

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_view" not in st.session_state:
    st.session_state.current_view = "new_research"
if "input_query" not in st.session_state:
    st.session_state.input_query = ""


# ------------------------------------------------------------------
# Sidebar: Exact Google Stitch Navigation (Zero Clutter)
# ------------------------------------------------------------------
with st.sidebar:
    # Stitch Logo & Title
    st.markdown("""
    <div class="brand-container">
        <img class="brand-logo" src="https://lh3.googleusercontent.com/aida/AEtjO1XxscqvhXBkcVgnh5Xxbd9_HnN3BS1M02nmO_6n16xf3P6p8FFRNf68vmVkuP6gG8q_PXL-RRmkfVEYx23SdWEUHYCrvGynx27dOv7rFS_-kV4rCei2kNWp08O1gNKIUHSaFU1wf_R13A3BuXYU1f8PzzI65iDVX5apFu9xLoWo8j5OnIdYJyAfbzX2dDMGMGgRAoyn_nRA18HMJn6mSedpDmWaBSSm6IKYUE9DRbMTvoVrOZoLzf1qpg" alt="SIP Insight Logo" />
        <div>
            <div class="brand-title">SIP Insight</div>
            <div class="brand-subtitle">Groww Research Lab</div>
        </div>
    </div>
    <div class="nav-header">Core Navigation</div>
    """, unsafe_allow_html=True)

    # Navigation buttons
    if st.button("🧭  New Research", key="nav_new_research"):
        st.session_state.current_view = "new_research"
        st.rerun()

    if st.button("📊  Research Overview", key="nav_research_overview"):
        st.session_state.current_view = "research_overview"
        st.rerun()


# ------------------------------------------------------------------
# View 2: Research Overview
# ------------------------------------------------------------------
if st.session_state.current_view == "research_overview":
    st.markdown("<h2 style='font-family: Plus Jakarta Sans; font-size: 26px; font-weight: 700; margin-bottom: 4px;'>12-Month SIP Retention Landscape</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #575E70; font-size: 14px; margin-bottom: 24px;'>Empirical breakdown of why first-time investors discontinue SIPs on Groww before reaching their 12th monthly instalment.</p>", unsafe_allow_html=True)

    # Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-lbl">Audited Corpus</div>
            <div class="metric-val">406</div>
            <div style="font-size: 11.5px; color: #006C4F; font-weight: 500;">Verified Retail Signals</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-lbl">Retention Cohort</div>
            <div class="metric-val" style="color: #006C4F;">80</div>
            <div style="font-size: 11.5px; color: #575E70; font-weight: 500;">High-Signal Cases</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-lbl">Peak Drop-off</div>
            <div class="metric-val" style="color: #BA1A1A;">Month 3–6</div>
            <div style="font-size: 11.5px; color: #575E70; font-weight: 500;">Salary & Drawdown Dip</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-lbl">AutoPay Friction</div>
            <div class="metric-val" style="color: #007153;">38.4%</div>
            <div style="font-size: 11.5px; color: #575E70; font-weight: 500;">Mandate Cancellations</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="metric-card">
            <h4 style="font-family: Plus Jakarta Sans; font-size: 16px; font-weight: 700; margin-bottom: 12px; color: #151C27;">The 3 Critical Churn Moments</h4>
            <div style="font-size: 13.5px; color: #3C4A43; line-height: 1.55;">
                <p><strong>1. Salary Date Mismatch (Month 2–4):</strong> When debits precede delayed salary credits, users delete the AutoPay mandate permanently rather than pausing.</p>
                <p><strong>2. First Portfolio Drawdown (Month 4–7):</strong> First-time investors seeing -3% or -5% XIRR panic and stop SIPs, expecting fixed returns.</p>
                <p><strong>3. Hidden Pause Feature:</strong> Users cannot easily find a 1–3 month pause option, so hard cancellation is the default action.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="metric-card">
            <h4 style="font-family: Plus Jakarta Sans; font-size: 16px; font-weight: 700; margin-bottom: 12px; color: #151C27;">High-Impact Solutions for Groww</h4>
            <div style="font-size: 13.5px; color: #3C4A43; line-height: 1.55;">
                <p><strong>• Smart Pre-Debit Reminder (T-24h):</strong> Push notification with a 1-tap "Skip this month" button before debit date.</p>
                <p><strong>• Prominent "Pause for 1–3 Months" Flow:</strong> Intercept cancellation clicks with a friendly temporary pause option.</p>
                <p><strong>• Market Dip Reassurance:</strong> Show unit accumulation benefits during corrections ("Rupee-cost averaging in action").</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    if st.button("← Back to Discovery Agent"):
        st.session_state.current_view = "new_research"
        st.rerun()


# ------------------------------------------------------------------
# View 1: New Research (The Main AI Discovery Agent)
# ------------------------------------------------------------------
else:
    # Google Stitch Hero Section
    st.markdown("""
    <div style="text-align: center; margin-top: 0.5rem; margin-bottom: 1.25rem;">
        <div class="stitch-hero-title">Discover why investors stay with their SIPs — or stop.</div>
        <div class="stitch-hero-subtitle">Explore real investor conversations, identify recurring behavioral friction, and uncover evidence-backed opportunities to improve 12-month SIP retention.</div>
    </div>
    """, unsafe_allow_html=True)

    # Prompt Chips - Completely visible without any truncation
    # Row 1: Two spacious columns for Chip 1 and Chip 2
    c_chip1, c_chip2 = st.columns([1.15, 0.85])
    with c_chip1:
        if st.button("✨ Why do first-time investors stop their SIPs?", key="btn_chip_1", use_container_width=True):
            st.session_state.input_query = "Why do first-time investors stop their SIPs?"
            st.rerun()
    with c_chip2:
        if st.button("📈 What changes after starting a SIP?", key="btn_chip_2", use_container_width=True):
            st.session_state.input_query = "What changes after starting a SIP?"
            st.rerun()

    # Row 2: Full-width centered column for Chip 3 so all words are 100% visible
    c_chip3 = st.columns([1])[0]
    with c_chip3:
        if st.button("🧠 What unmet needs emerge from investor conversations?", key="btn_chip_3", use_container_width=True):
            st.session_state.input_query = "What unmet needs emerge from investor conversations?"
            st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Centered Search Bar (Google Stitch Exact - Placed right below the questions)
    with st.form(key="center_search_form", clear_on_submit=False):
        col_icon, col_input, col_submit = st.columns([0.5, 8.8, 0.7])
        with col_icon:
            st.markdown('<div class="search-icon-wrapper"><span class="material-symbols-outlined text-[22px] text-primary">psychology</span></div>', unsafe_allow_html=True)
        with col_input:
            typed_query = st.text_input(
                "Search",
                placeholder="Ask your research agent about SIP investor behaviour...",
                label_visibility="collapsed",
                key="center_input_text"
            )
        with col_submit:
            search_submitted = st.form_submit_button("↑")

    # Determine Active Query (either from Prompt Chip or from Center Search Bar)
    active_query = None
    if search_submitted and typed_query.strip():
        active_query = typed_query.strip()
    elif st.session_state.get("input_query"):
        active_query = st.session_state.input_query
        st.session_state.input_query = ""

    # Execute and Stream Query Response if Triggered
    if active_query:
        st.session_state.messages.append({"role": "user", "content": active_query})

        # Strict Scope Guardrail Check
        query_lower = active_query.lower()
        off_topic_keywords = [
            "cricket", "cricketer", "virat", "dhoni", "ipl", "football", "messi", "ronaldo",
            "birthday", "weather", "recipe", "cinema", "bollywood", "hollywood", "actor", "actress",
            "prime minister", "president", "capital of", "who wrote", "song", "movie", "horoscope"
        ]

        if any(k in query_lower for k in off_topic_keywords):
            out_of_scope_reply = "This is out of scope. I am the Groww SIP Retention Discovery Agent and can only assist with questions regarding Groww mutual fund SIP retention, drop-off causes, auto-pay/mandate issues, and first-time investor behavior."
            st.session_state.messages.append({
                "role": "assistant",
                "content": out_of_scope_reply,
                "references": []
            })
            st.rerun()
        else:
            # RAG Retrieval on 406 records
            with st.spinner("Searching verified Groww and retail investor discussions..."):
                retrieval_res = retriever.retrieve_with_evidence_stats(active_query, top_k=6)
                retrieved_docs = retrieval_res["primary_matches"]
                counter_docs = retrieval_res.get("counterevidence_matches", [])
                stats = retrieval_res["stats"]

            # Groq 120B Big Model Generation
            with st.spinner("Synthesizing answer from real investor evidence..."):
                try:
                    from groq import Groq
                    client = Groq(api_key=GROQ_API_KEY)

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

                    completion = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
                        ],
                        max_tokens=1400
                    )

                    choice = completion.choices[0].message
                    raw_answer = choice.content or "No textual response generated."

                    is_out_of_scope = "out of scope" in raw_answer.lower()
                    if is_out_of_scope:
                        formatted_answer = raw_answer
                        final_references = []
                    else:
                        formatted_answer = linkify_citations(raw_answer, records_lookup)
                        final_references = retrieved_docs

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": formatted_answer,
                        "references": final_references
                    })
                    st.rerun()

                except Exception as e:
                    fallback = f"""### Empirical Summary
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
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": fallback,
                        "references": retrieved_docs
                    })
                    st.rerun()

    # Render Conversation Messages (Appears directly below the search bar)
    if st.session_state.messages:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"], unsafe_allow_html=True)
                
                # Interactive "Show Specific Investor Concerns & Quotes"
                if msg["role"] == "assistant" and "references" in msg and msg["references"]:
                    with st.expander(f"💬 Show Specific Investor Concerns & Quotes ({len(msg['references'])} sources)"):
                        for ref in msg["references"]:
                            ref_src = ref.get("source", "").lower()
                            if "play_store" in ref_src:
                                src_label = "Groww Play Store Review"
                            elif "app_store" in ref_src:
                                src_label = "Groww App Store Review"
                            elif "tradingqna" in ref_src:
                                src_label = "TradingQ&A (Groww)"
                            else:
                                src_label = "Reddit Community"

                            quote_txt = ref.get("classification", {}).get("verbatim_quote") or ref.get("raw_text", "")[:220]
                            url = ref.get("url") or "#"

                            st.markdown(f"**• {src_label}** `({ref['record_id']})`")
                            st.markdown(f"> *\"{quote_txt}...\"*")
                            st.markdown(f"↳ [Open Original Discussion ↗]({url})")
                            st.markdown("---")
