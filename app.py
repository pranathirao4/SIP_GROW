"""
Groww SIP Retention Discovery Engine
A focused, professional qualitative AI discovery agent to uncover root causes
and increase the percentage of first-time mutual fund investors with an active SIP at 12 months.
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
    page_title="Groww SIP Retention Discovery",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Groww Dark Theme Styling
st.markdown("""
<style>
    /* Global Canvas */
    .stApp {
        background-color: #0A0E17;
        color: #F1F5F9;
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
    }
    
    /* Left Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0F1523;
        border-right: 1px solid #1E293B;
        padding-top: 1rem;
    }
    
    /* Hero Section */
    .hero-container {
        text-align: center;
        margin-top: 1.5rem;
        margin-bottom: 1.8rem;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.025em;
        margin-bottom: 0.4rem;
        line-height: 1.25;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        max-width: 640px;
        margin: 0 auto;
        line-height: 1.5;
    }
    
    /* Discovery Goal Banner */
    .goal-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(0, 208, 156, 0.08);
        border: 1px solid rgba(0, 208, 156, 0.25);
        color: #00D09C;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 600;
        margin-bottom: 1rem;
        letter-spacing: 0.02em;
    }
    
    /* Prompt Chips Layout */
    .chip-grid {
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 650px;
        margin: 1.2rem auto 2rem auto;
    }
    
    /* Custom Prompt Buttons */
    div[data-testid="stButton"] button {
        background-color: #131A29 !important;
        border: 1px solid #243046 !important;
        color: #E2E8F0 !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        text-align: left !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #00D09C !important;
        background-color: #172134 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 208, 156, 0.08) !important;
    }
    
    /* Pipeline Step Cards (How It Works) */
    .pipeline-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin: 1.5rem 0;
    }
    .pipeline-card {
        background: #131A29;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 14px;
        transition: border-color 0.15s ease;
    }
    .pipeline-card:hover {
        border-color: #00D09C;
    }
    .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        font-size: 11px;
        font-weight: 700;
        color: #FFFFFF;
        margin-right: 6px;
    }
    .step-1 { background-color: #2563EB; }
    .step-2 { background-color: #DC2626; }
    .step-3 { background-color: #D97706; }
    .step-4 { background-color: #059669; }
    .step-5 { background-color: #00D09C; }
    
    .step-title {
        font-size: 13.5px;
        font-weight: 700;
        color: #F8FAFC;
    }
    .step-desc {
        font-size: 12px;
        color: #94A3B8;
        margin-top: 6px;
        line-height: 1.4;
    }
    
    /* Right References Drawer */
    .ref-header {
        font-size: 14px;
        font-weight: 700;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 8px;
        margin-bottom: 12px;
        border-bottom: 1px solid #1E293B;
    }
    .ref-card {
        background: #111726;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        transition: border-color 0.15s ease;
    }
    .ref-card:hover {
        border-color: #38BDF8;
    }
    .ref-badge {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 10.5px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .badge-reddit { background: rgba(255, 69, 0, 0.12); color: #FF6433; border: 1px solid rgba(255, 69, 0, 0.3); }
    .badge-tradingqna { background: rgba(56, 189, 248, 0.12); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3); }
    .badge-reviews { background: rgba(0, 208, 156, 0.12); color: #00D09C; border: 1px solid rgba(0, 208, 156, 0.3); }
    
    .ref-quote {
        color: #CBD5E1;
        font-style: italic;
        border-left: 2px solid #00D09C;
        padding-left: 8px;
        margin: 6px 0;
        font-size: 12px;
        line-height: 1.45;
    }
    .ref-link {
        color: #38BDF8;
        text-decoration: none;
        font-size: 11.5px;
        font-weight: 500;
    }
    .ref-link:hover {
        text-decoration: underline;
    }
    
    /* Clean chat input styling */
    div[data-testid="stChatInput"] {
        border-radius: 20px !important;
        border: 1px solid #243046 !important;
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
# Sidebar: Streamlined, Professional Navigation
# ------------------------------------------------------------------
with st.sidebar:
    # Groww Logo & Title
    st.image("https://assets-netstorage.groww.in/web-assets/big_logo.png", width=115)
    st.markdown("### **SIP Discovery Engine**")
    st.caption("12-Month Retention Intelligence")
    st.markdown("---")

    # Clean Navigation Buttons
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

    st.markdown("---")
    
    # Recents List
    st.markdown("**RECENTS**")
    if not st.session_state.recents:
        st.caption("Chats you start show up here.")
    else:
        for idx, recent in enumerate(st.session_state.recents[-5:][::-1]):
            if st.button(f"💬 {recent[:26]}...", key=f"recent_{idx}", use_container_width=True):
                st.session_state.current_view = "chat"
                st.session_state.input_query = recent
                st.rerun()

    st.markdown("---")
    # Clean Status Indicator (Zero Clutter)
    if GROQ_API_KEY:
        st.markdown("<span style='color: #00D09C; font-size: 12px; font-weight: 500;'>● 120B Discovery Engine Active</span>", unsafe_allow_html=True)
    else:
        st.warning("API Key needed in .env")

    st.caption("Chats are saved for this browser session.")


# ------------------------------------------------------------------
# View 1: How It Works (Exact 5-Step Pipeline Card Banner)
# ------------------------------------------------------------------
if st.session_state.current_view == "how_it_works":
    st.title("🔀 How the Discovery Engine Works")
    st.markdown("The 5-stage pipeline transforming unstructured retail investor conversations into audited behavioral retention insights:")

    # 5-Step Pipeline Cards
    st.markdown("""
    <div class="pipeline-grid">
        <div class="pipeline-card">
            <span class="step-badge step-1">1</span>
            <span class="step-title">Collect</span>
            <div class="step-desc"><strong>419 raw discussions</strong> from Groww Play Store/App Store reviews, Reddit, and TradingQ&A.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-2">2</span>
            <span class="step-title">Filter</span>
            <div class="step-desc"><strong>406 search posts</strong> cleaned, normalized, and MD5 deduplicated across all sources.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-3">3</span>
            <span class="step-title">AI tag</span>
            <div class="step-desc"><strong>Groq 120B & heuristics</strong> label each post with investor stage, behaviour, and trigger context.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-4">4</span>
            <span class="step-title">RAG</span>
            <div class="step-desc"><strong>406 indexed records</strong> queried via BM25 retrieval to ground every answer in real Groww evidence.</div>
        </div>
        <div class="pipeline-card">
            <span class="step-badge step-5">5</span>
            <span class="step-title">Ask</span>
            <div class="step-desc"><strong>AI answers questions</strong> specifically for Groww PMs in plain English with clickable references.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Ethical & SEBI Compliance Guardrails")
    st.markdown("""
    1. **Strictly Zero Fund Recommendations:** The engine never recommends mutual funds, asset managers, or stock picks.
    2. **Zero Manufactured FOMO:** Focuses solely on understanding cash-flow realities, emergency pauses, and product friction.
    3. **Immutable Verifiable Evidence:** Every insight ties directly to an audited record ID (`REC-XXXXX`) and its original source link.
    """)
    
    if st.button("← Back to Discovery Agent"):
        st.session_state.current_view = "chat"
        st.rerun()


# ------------------------------------------------------------------
# View 2: Signals Library (Browse All 321 Cleaned Records)
# ------------------------------------------------------------------
elif st.session_state.current_view == "library":
    st.title("📖 Verified Signals Library")
    st.markdown(f"Browse the complete database of **{len(cleaned_records)} cleaned investor conversations** ({len(relevant_records)} core retention signals).")

    search_term = st.text_input("🔍 Search investor verbatims or keywords:", placeholder="e.g. salary delay, emergency, student, negative returns...")
    
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
            st.markdown(f"**Original Link:** [{r.get('url', '#')}]({r.get('url', '#')})")
            if "classification" in r:
                c = r["classification"]
                st.caption(f"Stage: `{c.get('investor_stage')}` | Trigger: `{c.get('trigger_context')}` | Behavior: `{c.get('reported_behaviour')}`")

    if st.button("← Back to Discovery Agent"):
        st.session_state.current_view = "chat"
        st.rerun()


# ------------------------------------------------------------------
# View 3: Main Discovery Agent (Clean, Professional & Goal-Oriented)
# ------------------------------------------------------------------
elif st.session_state.current_view == "chat":
    # Two-column layout: Left (70%) Chat Agent, Right (30%) References Panel
    col_main, col_ref = st.columns([7, 3])

    with col_main:
        # If no messages yet, show Clean Hero and Core 12-Month Retention Questions
        if len(st.session_state.messages) == 0:
            st.markdown("""
            <div class="hero-container">
                <div class="goal-badge">🎯 Goal: 12-Month Active SIP Retention</div>
                <div class="hero-title">Ask what retail investors say about Groww SIP cancellations & retention</div>
                <div class="hero-subtitle">Empirical discovery uncovering root causes to increase 12-month active SIP retention specifically on Groww. Grounded in verified Groww app reviews, Reddit discussions, and Indian retail forums.</div>
            </div>
            """, unsafe_allow_html=True)

            # The 5 Core Strategic Retention Questions specifically for Groww
            curated_questions = [
                ("⏱️", "Why do first-time Groww investors drop out before completing 12 months?"),
                ("⏸️", "Why do users permanently delete Groww AutoPay instead of using 'Pause'?"),
                ("🎓", "What causes students and gig workers on Groww to stop their monthly SIPs?"),
                ("📉", "How does seeing negative returns on the Groww dashboard cause users to panic?"),
                ("🛡️", "What product features should Groww build to keep first-time investors active for 12+ months?")
            ]

            st.markdown("<div class='chip-grid'>", unsafe_allow_html=True)
            for idx, (icon, question) in enumerate(curated_questions):
                if st.button(f"{icon}  {question}", key=f"core_q_{idx}", use_container_width=True):
                    st.session_state.input_query = question
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Render Active Chat Conversation
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Execute query if triggered by Button or Chat Input
        user_query = st.session_state.input_query
        if not user_query:
            user_query = st.chat_input("Ask a question about 12-month retention, drop-off reasons, or pause habits on Groww...")

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
            with st.spinner("Searching verified Groww and retail investor discussions..."):
                retrieved_docs = retriever.retrieve(user_query, top_k=6)
                st.session_state.active_references = retrieved_docs

            # Step 5: Ask LLM (Groq 120B Big Model)
            with st.chat_message("assistant"):
                with st.spinner("Synthesizing answer from real investor evidence..."):
                    try:
                        from groq import Groq
                        client = Groq(api_key=GROQ_API_KEY)

                        # Build context from retrieved references
                        context_blocks = []
                        for r in retrieved_docs:
                            quote = r.get("classification", {}).get("verbatim_quote") or r.get("raw_text", "")[:200]
                            context_blocks.append(
                                f"ID: {r['record_id']} | Source: {r.get('source')} | Title: {r.get('title')}\nVerbatim: \"{quote}\""
                            )
                        context_str = "\n\n".join(context_blocks)

                        system_prompt = f"""You are the senior Groww Product & Retention Discovery AI Bot.
Your primary mission is to explain empirically why first-time mutual fund investors stop, pause, or abandon their SIPs on the Groww platform before 12 months, and how Groww can increase 12-month active SIP retention.

Evidence Context from Real Investor Discussions (including Groww app reviews & investor forums):
{context_str}

How to Format Your Answer:
- **Direct Summary (1-2 sentences):** Give the direct, bottom-line answer immediately in plain, everyday language explaining what Groww users experience.
- **Key Reasons on Groww (2 to 4 bullet points):**
  - Use bold, everyday titles (e.g. **Groww AutoPay Confusion**, **Salary Delay vs Debit Date**, **Panic When Returns Dipped**).
  - Explain what real everyday Groww investors go through in 1-2 easy sentences.
  - Naturally mention what users actually said, citing their record ID like [REC-00042].
- **Actionable Takeaway for Groww (1 simple sentence):** What the Groww Product/Growth team should implement to retain users past 12 months.

Important Rules:
- Always frame the analysis specifically around Groww's product, user flows, and 12-month retention goal.
- Speak like a friendly human explaining things to a colleague.
- NO corporate jargon, no academic speak, and no dense walls of text.
- Strictly NEVER recommend specific mutual funds or stocks (SEBI compliance).
- Always ground every point in the provided evidence context."""

                        completion = client.chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
                            ],
                            max_tokens=900
                        )

                        choice = completion.choices[0].message
                        answer = choice.content or "No textual response generated."

                        st.markdown(answer)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "references": retrieved_docs
                        })
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error querying Groq: {e}")

    # Right Column: References Panel (Clean, Professional Drawer)
    with col_ref:
        st.markdown("""
        <div class="ref-header">
            <span>📚 References</span>
            <span style="font-size: 11.5px; color: #00D09C; font-weight: 500;">Real Verbatims</span>
        </div>
        """, unsafe_allow_html=True)

        refs = st.session_state.active_references
        if not refs:
            st.caption("When you ask a question, the exact supporting quotes from Reddit, TradingQ&A, and Groww reviews will appear here.")
        else:
            for r in refs:
                source = r.get("source", "other").lower()
                if "play_store" in source:
                    badge_class = "badge-reviews"
                    badge_label = "Groww Play Store"
                elif "app_store" in source:
                    badge_class = "badge-reviews"
                    badge_label = "Groww App Store"
                elif "groww" in source:
                    badge_class = "badge-tradingqna"
                    badge_label = "TradingQ&A (Groww)"
                elif "reddit" in source:
                    badge_class = "badge-reddit"
                    badge_label = "Reddit (Groww/MF)"
                else:
                    badge_class = "badge-tradingqna"
                    badge_label = "Investor Forum"
                
                quote = r.get("classification", {}).get("verbatim_quote") or r.get("raw_text", "")[:180]
                url = r.get("url", "#")
                
                st.markdown(f"""
                <div class="ref-card">
                    <span class="ref-badge {badge_class}">{badge_label}</span>
                    <strong style="color: #F8FAFC; display: block; margin-bottom: 3px; font-size: 12.5px;">{r['record_id']}</strong>
                    <div style="font-size: 12px; color: #94A3B8; margin-bottom: 6px;">{r.get('title', '')[:52]}...</div>
                    <div class="ref-quote">"{quote}..."</div>
                    <a href="{url}" target="_blank" class="ref-link">View original discussion ↗</a>
                </div>
                """, unsafe_allow_html=True)
