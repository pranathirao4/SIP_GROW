"""
Groww SIP Retention Discovery Engine
AI-powered qualitative discovery agent powered by Groq 120B Big Model and empirical retail investor signals.
"""

import os
import sys
import json
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
    page_title="Groww SIP Discovery Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme CSS tailored to Groww brand aesthetics and Discovery Agent layout
st.markdown("""
<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #0B0F17;
        color: #F1F5F9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Left Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1F2937;
        padding-top: 1rem;
    }
    
    /* Hero Section */
    .hero-container {
        text-align: center;
        margin-top: 2.5rem;
        margin-bottom: 2rem;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #F8FAFC;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #94A3B8;
        max-width: 650px;
        margin: 0 auto 1.5rem auto;
        line-height: 1.5;
    }
    
    /* Pipeline Step Cards (Image 1 Style) */
    .pipeline-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin: 1.5rem 0;
    }
    .pipeline-card {
        background: #162032;
        border: 1px solid #243247;
        border-radius: 10px;
        padding: 14px;
        transition: transform 0.15s ease;
    }
    .pipeline-card:hover {
        transform: translateY(-2px);
        border-color: #00D09C;
    }
    .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        font-size: 12px;
        font-weight: 700;
        color: #FFFFFF;
        margin-right: 8px;
    }
    .step-1 { background-color: #2563EB; }
    .step-2 { background-color: #DC2626; }
    .step-3 { background-color: #D97706; }
    .step-4 { background-color: #059669; }
    .step-5 { background-color: #3B82F6; }
    
    .step-title {
        font-size: 14px;
        font-weight: 700;
        color: #F1F5F9;
        display: inline-block;
    }
    .step-desc {
        font-size: 12px;
        color: #94A3B8;
        margin-top: 6px;
        line-height: 1.4;
    }
    
    /* Reference Cards */
    .ref-header {
        font-size: 15px;
        font-weight: 700;
        color: #00D09C;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 12px;
    }
    .ref-card {
        background: #131B2E;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        font-size: 13px;
    }
    .ref-card:hover {
        border-color: #38BDF8;
    }
    .ref-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .badge-reddit { background: rgba(255, 69, 0, 0.15); color: #FF4500; border: 1px solid #FF4500; }
    .badge-tradingqna { background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8; }
    .badge-reviews { background: rgba(0, 208, 156, 0.15); color: #00D09C; border: 1px solid #00D09C; }
    
    .ref-quote {
        color: #CBD5E1;
        font-style: italic;
        border-left: 2px solid #00D09C;
        padding-left: 8px;
        margin: 6px 0;
        font-size: 12px;
    }
    .ref-link {
        color: #38BDF8;
        text-decoration: none;
        font-size: 11px;
        font-weight: 500;
    }
    .ref-link:hover {
        text-decoration: underline;
    }
    
    /* Prompt Chips */
    .chip-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        margin-bottom: 2rem;
    }
    
    /* Bottom Chat Input Bar */
    div[data-testid="stChatInput"] {
        background: #162032;
        border-radius: 24px;
    }
    
    /* Nav Button Styling */
    .nav-btn {
        display: block;
        width: 100%;
        text-align: left;
        background: transparent;
        color: #94A3B8;
        border: none;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 14px;
        cursor: pointer;
    }
    .nav-btn:hover {
        background: #1F2937;
        color: #F8FAFC;
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

# Initialize Retriever
@st.cache_resource
def get_retriever():
    return SIPRetriever(cleaned_records)

retriever = get_retriever()

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recents" not in st.session_state:
    st.session_state.recents = []
if "current_view" not in st.session_state:
    st.session_state.current_view = "chat"
if "active_references" not in st.session_state:
    st.session_state.active_references = []
if "input_query" not in st.session_state:
    st.session_state.input_query = ""


# ------------------------------------------------------------------
# Sidebar: Navigation & Controls (Matches Image 2)
# ------------------------------------------------------------------
with st.sidebar:
    # App Branding
    st.image("https://assets-netstorage.groww.in/web-assets/big_logo.png", width=120)
    st.markdown("### **SIP Discovery Engine**")
    st.caption("AI-Powered Qualitative Retention Agent")
    st.markdown("---")

    # Navigation Actions
    if st.button("✏️ New chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.active_references = []
        st.session_state.current_view = "chat"
        st.rerun()

    if st.button("📖 Signals library", use_container_width=True):
        st.session_state.current_view = "library"
        st.rerun()

    if st.button("🔀 How it works", use_container_width=True):
        st.session_state.current_view = "how_it_works"
        st.rerun()

    st.markdown("[⟨⟩ Repository](https://github.com/pranathirao4/SIP_GROW)", unsafe_allow_html=True)

    st.markdown("---")
    
    # Recents List
    st.markdown("**RECENTS**")
    if not st.session_state.recents:
        st.caption("Chats you start show up here.")
    else:
        for idx, recent in enumerate(st.session_state.recents[-6:][::-1]):
            if st.button(f"💬 {recent[:28]}...", key=f"recent_{idx}", use_container_width=True):
                st.session_state.current_view = "chat"
                st.session_state.input_query = recent
                st.rerun()

    st.markdown("---")
    
    # LLM Engine Selector
    model_choice = st.selectbox(
        "Groq LLM Engine:",
        [
            "openai/gpt-oss-120b (120B Big Model)",
            "qwen/qwen3.8-27b (27B Fast)",
            "openai/gpt-oss-20b"
        ],
        index=0
    )
    selected_model = model_choice.split(" ")[0]

    if GROQ_API_KEY:
        st.markdown("<span style='color: #00D09C; font-size: 12px;'>🟢 Groq 120B Connected</span>", unsafe_allow_html=True)
    else:
        st.warning("API Key not found in .env")

    st.markdown("---")
    st.caption("Note - Chats are limited to this browser session. Refreshing the page clears them.")


# ------------------------------------------------------------------
# View 1: How It Works (Exact 5-Step Card Banner from Image 1)
# ------------------------------------------------------------------
if st.session_state.current_view == "how_it_works":
    st.title("🔀 How the Discovery Engine Works")
    st.markdown("The 5-stage pipeline transforming unstructured retail investor conversations into audited behavioral retention insights:")

    # 5-step banner cards
    st.markdown("""
    <div class="pipeline-grid">
        <div class="pipeline-card">
            <span class="step-badge step-1">1</span>
            <span class="step-title">Collect</span>
            <div class="step-desc"><strong>334 raw posts</strong> from Reddit (r/personalfinanceindia, r/IndiaInvestments), TradingQ&A, and Groww app reviews.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-2">2</span>
            <span class="step-title">Filter</span>
            <div class="step-desc"><strong>321 search posts</strong> cleaned, unicode normalized, and MD5 deduplicated across all sources.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-3">3</span>
            <span class="step-title">AI tag</span>
            <div class="step-desc"><strong>Groq 120B & heuristics</strong> label each post with investor stage, behaviour, and trigger context.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-4">4</span>
            <span class="step-title">RAG</span>
            <div class="step-desc"><strong>321 semantic records</strong> indexed for BM25 retrieval to ground answers in real verbatim evidence.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-5">5</span>
            <span class="step-title">Ask</span>
            <div class="step-desc"><strong>AI answers questions</strong> with context from real user discussions and verified clickable references.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Ethical & SEBI Compliance Guardrails")
    st.markdown("""
    1. **Strictly Zero Fund Recommendations:** The engine never recommends mutual funds, asset managers, or stock picks.
    2. **Zero FOMO / Urgency Tactics:** Analysis focuses solely on understanding friction, anxiety, and cash-flow reality.
    3. **Ground Truth Citations:** Every finding presented by the agent is mapped directly to an immutable record ID (`REC-XXXXX`) and original forum permalink.
    """)
    
    if st.button("← Back to Discovery Agent"):
        st.session_state.current_view = "chat"
        st.rerun()


# ------------------------------------------------------------------
# View 2: Signals Library (Browse All 321 Cleaned Records)
# ------------------------------------------------------------------
elif st.session_state.current_view == "library":
    st.title("📖 Verified Signals Library")
    st.markdown(f"Explore the entire database of **{len(cleaned_records)} cleaned records** ({len(relevant_records)} core retention signals).")

    search_term = st.text_input("🔍 Search investor verbatims or keywords:", placeholder="e.g. bounce charge, salary delay, student, XIRR...")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        source_filter = st.selectbox("Filter by Source:", ["All Sources", "reddit", "tradingqna", "app_reviews"])
    with col_f2:
        tier_filter = st.selectbox("Filter by Relevance:", ["All Records", "Tier 1: Direct SIP Retention", "Tier 2: Investor Psychology", "Tier 3: Mandate Technical"])

    filtered = cleaned_records
    if source_filter != "All Sources":
        filtered = [r for r in filtered if source_filter in r.get("source", "")]
    if tier_filter != "All Records":
        tier_num = 1 if "Tier 1" in tier_filter else (2 if "Tier 2" in tier_filter else 3)
        filtered = [r for r in filtered if r.get("relevance_tier") == tier_num]
    if search_term:
        filtered = [r for r in filtered if search_term.lower() in (r.get("title", "") + r.get("raw_text", "")).lower()]

    st.caption(f"Showing **{len(filtered)}** matching records")

    for r in filtered[:30]:
        with st.expander(f"[{r['record_id']}] {r.get('title', 'Untitled')} ({r.get('source', '')})"):
            st.markdown(f"**Verbatim Text:**\n> {r.get('raw_text', '')[:400]}...")
            st.markdown(f"**URL:** [{r.get('url', '#')}]({r.get('url', '#')})")
            if "classification" in r:
                c = r["classification"]
                st.caption(f"Stage: `{c.get('investor_stage')}` | Trigger: `{c.get('trigger_context')}` | Behavior: `{c.get('reported_behaviour')}`")

    if st.button("← Back to Discovery Agent"):
        st.session_state.current_view = "chat"
        st.rerun()


# ------------------------------------------------------------------
# View 3: Main Discovery Agent (Matches Image 2)
# ------------------------------------------------------------------
elif st.session_state.current_view == "chat":
    # Two-column layout: Left (70%) Chat Agent, Right (30%) References Drawer
    col_main, col_ref = st.columns([7, 3])

    with col_main:
        # If no messages yet, show Hero Section and Prompt Chips (Image 2)
        if len(st.session_state.messages) == 0:
            st.markdown("""
            <div class="hero-container">
                <div class="hero-title">Ask what retail investors say about SIP cancellations & retention</div>
                <div class="hero-subtitle">Answers come only from Reddit, TradingQ&A, and Groww app reviews. References sit on the right.</div>
            </div>
            """, unsafe_allow_html=True)

            # Suggested Query Chips (Pill Buttons)
            chips = [
                "Why do people cancel SIP within 6 months?",
                "Do users say bank bounce charges make them stop?",
                "What do students and irregular earners say about SIPs?",
                "Why do investors panic when XIRR is negative?"
            ]

            st.markdown("<div style='max-width: 600px; margin: 0 auto;'>", unsafe_allow_html=True)
            for c_idx, chip in enumerate(chips):
                if st.button(chip, key=f"chip_{c_idx}", use_container_width=True):
                    st.session_state.input_query = chip
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Render Active Chat Conversation
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg.get("reasoning"):
                    with st.expander("🧠 View 120B Reasoning Trace", expanded=False):
                        st.caption(msg["reasoning"])
                st.markdown(msg["content"])

        # Execute query if triggered by Chip or Input
        user_query = st.session_state.input_query
        if not user_query:
            user_query = st.chat_input("Ask about retail investor SIP drop-off, pause habits, or bounce penalties...")

        if user_query:
            # Clear input query from state
            st.session_state.input_query = ""
            
            # Add to recents
            if user_query not in st.session_state.recents:
                st.session_state.recents.append(user_query)

            # Record user message
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            # Step 4: RAG Retrieval
            with st.spinner("Retrieving verified investor discussions (BM25 RAG)..."):
                retrieved_docs = retriever.retrieve(user_query, top_k=6)
                st.session_state.active_references = retrieved_docs

            # Step 5: Ask LLM (Groq 120B)
            with st.chat_message("assistant"):
                with st.spinner(f"Synthesizing answer with {selected_model}..."):
                    try:
                        from groq import Groq
                        client = Groq(api_key=GROQ_API_KEY)

                        # Context from retrieved references
                        context_blocks = []
                        for r in retrieved_docs:
                            quote = r.get("classification", {}).get("verbatim_quote") or r.get("raw_text", "")[:200]
                            context_blocks.append(
                                f"ID: {r['record_id']} | Source: {r.get('source')} | Title: {r.get('title')}\nVerbatim: \"{quote}\""
                            )
                        context_str = "\n\n".join(context_blocks)

                        system_prompt = f"""You are a helpful, human-friendly AI Discovery Bot (like Google AI Overviews or a smart search bot).
Your goal is to answer queries in simple, plain, conversational English that any everyday human being can understand in 10 seconds.

Ground Truth Qualitative Evidence from Database:
{context_str}

How to Format Your Answer:
1. **Direct Answer (1-2 sentences):** Give the direct, bottom-line answer immediately in plain words. No throat-clearing.
2. **Top Reasons (2 to 4 bullet points):**
   - Use bold, everyday titles (e.g. **Unexpected Bank Penalties**, **Salary Delay & Tight Budget**, **Panic When Returns Dipped**).
   - Explain what real everyday investors go through in 1-2 easy sentences.
   - Mention what real people actually said, citing their record ID like [REC-00163].
3. **Bottom Line (1 simple sentence):** What this really means for normal people.

Important Style Guidelines:
- Speak like a friendly human explaining things to a friend.
- NO corporate buzzwords, no complicated financial jargon, and no dense walls of text.
- Strictly NEVER recommend specific mutual funds, equities, or push artificial FOMO (SEBI compliance).
- Always ground every point in the provided evidence context."""

                        completion = client.chat.completions.create(
                            model=selected_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
                            ],
                            max_tokens=1200
                        )

                        choice = completion.choices[0].message
                        answer = choice.content or "No textual response generated."
                        reasoning = getattr(choice, 'reasoning', None)

                        if reasoning:
                            with st.expander("🧠 View 120B Reasoning Trace", expanded=False):
                                st.caption(reasoning)

                        st.markdown(answer)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "reasoning": reasoning,
                            "references": retrieved_docs
                        })
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error connecting to Groq: {e}")

    # Right Column: References Panel (Matches Image 2 "References >")
    with col_ref:
        st.markdown("""
        <div class="ref-header">
            <span>📚 References</span>
            <span style="font-size: 12px; color: #94A3B8;">(Real Verbatims)</span>
        </div>
        """, unsafe_allow_html=True)

        refs = st.session_state.active_references
        if not refs:
            st.caption("When you ask a question, the retrieved investor quotes and sources will appear here.")
        else:
            for r in refs:
                source = r.get("source", "other")
                badge_class = "badge-reddit" if "reddit" in source else ("badge-tradingqna" if "tradingqna" in source else "badge-reviews")
                badge_label = "Reddit" if "reddit" in source else ("TradingQ&A" if "tradingqna" in source else "App Review")
                
                quote = r.get("classification", {}).get("verbatim_quote") or r.get("raw_text", "")[:180]
                url = r.get("url", "#")
                
                st.markdown(f"""
                <div class="ref-card">
                    <span class="ref-badge {badge_class}">{badge_label}</span>
                    <strong style="color: #F8FAFC; display: block; margin-bottom: 4px;">{r['record_id']}</strong>
                    <div style="font-size: 12px; color: #94A3B8; margin-bottom: 6px;">{r.get('title', '')[:55]}...</div>
                    <div class="ref-quote">"{quote}..."</div>
                    <a href="{url}" target="_blank" class="ref-link">View original discussion ↗</a>
                </div>
                """, unsafe_allow_html=True)
