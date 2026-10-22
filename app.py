"""
Groww AI-Powered SIP Retention Discovery Agent
Enterprise-grade Streamlit research workspace powered by Groq LLM.
"""

import os
import sys
import json
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables (supports .env and Streamlit secrets)
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]


# Set Page Config
st.set_page_config(
    page_title="Groww SIP Retention Discovery Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Groww Dark Theme)
st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00D09C !important;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #94A3B8 !important;
        font-weight: 500;
    }
    /* Card Container */
    .metric-card {
        background: #131B2E;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    /* Badge */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-tier1 { background: rgba(0, 208, 156, 0.15); color: #00D09C; border: 1px solid #00D09C; }
    .badge-tier2 { background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8; }
    .badge-tier3 { background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; }
    .badge-churn { background: rgba(244, 63, 94, 0.15); color: #F43F5E; border: 1px solid #F43F5E; }
    /* Quote Box */
    .quote-box {
        background: #162032;
        border-left: 4px solid #00D09C;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        font-style: italic;
        color: #E2E8F0;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# Data Loaders with Caching
@st.cache_data
def load_all_data():
    base = Path("data")
    cleaned = []
    relevant = []
    review_q = []
    clusters = []
    opps = []
    evidence = []

    if (base / "processed/cleaned_records.json").exists():
        with open(base / "processed/cleaned_records.json", "r", encoding="utf-8") as f:
            cleaned = json.load(f)
    if (base / "processed/relevant_records.json").exists():
        with open(base / "processed/relevant_records.json", "r", encoding="utf-8") as f:
            relevant = json.load(f)
    if (base / "processed/review_queue.json").exists():
        with open(base / "processed/review_queue.json", "r", encoding="utf-8") as f:
            review_q = json.load(f)
    if (base / "processed/theme_clusters.json").exists():
        with open(base / "processed/theme_clusters.json", "r", encoding="utf-8") as f:
            clusters = json.load(f)
    if (base / "processed/opportunity_matrix.json").exists():
        with open(base / "processed/opportunity_matrix.json", "r", encoding="utf-8") as f:
            opps = json.load(f)
    if (base / "evidence_log.json").exists():
        with open(base / "evidence_log.json", "r", encoding="utf-8") as f:
            evidence = json.load(f)

    return cleaned, relevant, review_q, clusters, opps, evidence


cleaned_data, relevant_data, review_queue, theme_clusters, opportunities, evidence_log = load_all_data()

# Sidebar Navigation
st.sidebar.image("https://assets-netstorage.groww.in/web-assets/big_logo.png", width=140)
st.sidebar.title("SIP Retention Discovery")
st.sidebar.markdown(f"**Live Database:** `{len(cleaned_data)}` Records  \n**Core Signals:** `{len(relevant_data)}` Verified  \n**Groq LLM:** `OpenAI GPT-OSS 120B`")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Select Workspace Module",
    [
        "📊 1. Executive Overview",
        "⚠️ 2. Data Quality & Review Queue",
        "🔍 3. Conversation Explorer",
        "🧩 4. Semantic Theme Clusters",
        "👥 5. Cohort & Segment Analysis",
        "🎯 6. Opportunity Prioritization Matrix",
        "📜 7. AI Evidence Log & Audit",
        "❓ 8. Research Questions & Interview Guides",
        "🤖 9. Live Groq AI Assistant",
        "📥 10. Export Center"
    ]
)

# -------------------------------------------------------------
# Module 1: Executive Overview
# -------------------------------------------------------------
if menu == "📊 1. Executive Overview":
    st.title("📈 Executive Overview: 12-Month SIP Retention Discovery")
    st.markdown("Evidence-based discovery analyzing why first-time mutual fund investors reduce, pause, cancel, or abandon SIPs before 12 months.")

    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cleaned Records", f"{len(cleaned_data)}", "Multi-Source")
    with col2:
        st.metric("Core Retention Signals", f"{len(relevant_data)}", f"{round(len(relevant_data)/len(cleaned_data)*100, 1)}% of Sample")
    with col3:
        st.metric("Discovered Risk Themes", f"{len(theme_clusters)}", "Operational Taxonomy")
    with col4:
        st.metric("Top Prioritized Bet", "Bank ECS Shield", "OPS: 4.71 / 5.0")

    st.markdown("---")

    # Visual Funnel & Distribution
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Discourse Funnel")
        funnel_stages = ["Total Raw Scraped", "Cleaned Unique", "Relevant Retention Signals", "Prioritized Opportunities"]
        funnel_counts = [334, len(cleaned_data), len(relevant_data), len(opportunities)]
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_stages,
            x=funnel_counts,
            textinfo="value+percent previous",
            marker={"color": ["#38BDF8", "#00D09C", "#F59E0B", "#F43F5E"]}
        ))
        fig_funnel.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_right:
        st.subheader("Source Breakdown")
        sources = [r["source"] for r in cleaned_data]
        source_df = pd.Series(sources).value_counts().reset_index()
        source_df.columns = ["Source", "Count"]
        fig_pie = px.pie(
            source_df,
            values="Count",
            names="Source",
            hole=0.45,
            color_discrete_sequence=["#00D09C", "#38BDF8", "#818CF8", "#F59E0B", "#F43F5E", "#EC4899"]
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # Core Discovered Findings
    st.subheader("Key Strategic Discoveries")
    st.markdown("""
    1. **Bank ECS Bounce Penalty Trap (Severe Severity):**  
       Users cancel mandates proactively to escape recurring **₹450–₹590 bank bounce fees** caused when debit dates precede salary arrival.
    2. **Inflexible Emergency Liquidity Traps:**  
       Users facing short-term cash crunches (medical bills, rent, exams) default to **hard cancellation** because a simple 1-3 month pause is not intuitive.
    3. **First-Year Negative XIRR Panic:**  
       Month 3–6 market drawdowns destroy confidence; beginners compare volatile equity to guaranteed 7% FDs and prematurely exit.
    """)

# -------------------------------------------------------------
# Module 2: Data Quality & Review Queue
# -------------------------------------------------------------
elif menu == "⚠️ 2. Data Quality & Review Queue":
    st.title("⚠️ Data Quality & Human Review Queue")
    st.markdown("Inspect borderline records (confidence 0.40–0.60) routed to human triage before downstream classification.")

    st.info(f"There are currently **{len(review_queue)} records** awaiting human review.")

    for item in review_queue:
        with st.expander(f"[{item['record_id']}] {item['title']} (Score: {item['score']} | {item['source']})"):
            st.markdown(f"**Source:** `{item['source']}` | **URL:** [{item['url']}]({item['url']})")
            st.markdown(f"**Snippet:** *\"{item['snippet']}\"*")
            st.markdown(f"**AI Rationale:** {item['rationale']}")
            st.markdown(f"**Matched Keywords:** `{', '.join(item['matched_keywords'])}`")
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("✅ Accept into Dataset", key=f"acc_{item['record_id']}"):
                    st.success(f"{item['record_id']} approved!")
            with c2:
                if st.button("❌ Exclude as Noise", key=f"rej_{item['record_id']}"):
                    st.warning(f"{item['record_id']} excluded.")

# -------------------------------------------------------------
# Module 3: Conversation Explorer
# -------------------------------------------------------------
elif menu == "🔍 3. Conversation Explorer":
    st.title("🔍 Conversation Explorer")
    st.markdown("Search, filter, and inspect all 321 qualitative investor records across Reddit, TradingQ&A, and App Reviews.")

    # Search and Filters
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        search_query = st.text_input("Live Keyword Search", placeholder="e.g. bounce, pause, penalty, negative return, student")
    with col_s2:
        source_options = ["All Sources"] + sorted(list(set(r["source"] for r in cleaned_data)))
        sel_source = st.selectbox("Filter Source", source_options)
    with col_s3:
        tier_options = ["All Records", "Tiers 1-3 (Core Retention)", "Tier 1 (Directly Relevant)"]
        sel_tier = st.selectbox("Relevance Filter", tier_options)

    # Filter records
    filtered = cleaned_data
    if sel_source != "All Sources":
        filtered = [r for r in filtered if r["source"] == sel_source]
    if search_query:
        sq = search_query.lower()
        filtered = [r for r in filtered if sq in r["title"].lower() or sq in r["raw_text"].lower()]

    st.markdown(f"Showing **{len(filtered)} records** matching your criteria.")

    for record in filtered[:30]:
        with st.expander(f"[{record['record_id']}] {record['title'] or record['raw_text'][:60]} ({record['source']})"):
            st.markdown(f"**URL:** [{record['url']}]({record['url']}) | **Author:** `{record.get('author')}` | **Likes/Upvotes:** `{record.get('upvotes_or_likes')}`")
            st.markdown(f"<div class='quote-box'>{record['raw_text'] or record['title']}</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# Module 4: Semantic Theme Clusters
# -------------------------------------------------------------
elif menu == "🧩 4. Semantic Theme Clusters":
    st.title("🧩 Semantic Theme Clusters (Operational Taxonomy)")
    st.markdown("The 13 baseline operational hypotheses ranked by qualitative prevalence among relevant discussions.")

    for thm in theme_clusters:
        with st.container():
            st.markdown(f"""
            <div class='metric-card'>
                <h3 style='margin:0; color:#38BDF8;'>[{thm['theme_id']}] {thm['theme_name']}</h3>
                <p style='color:#94A3B8; font-size:14px; margin-top:4px;'>{thm['definition']}</p>
                <span class='badge badge-tier1'>Prevalence: {thm['record_count']}/{thm['denominator']} ({thm['prevalence_percentage']}%)</span>
                <span class='badge badge-tier2'>Sources: {thm['unique_sources_count']} Channels</span>
                <p style='margin-top:10px;'><strong>Impact on 12-Month Retention:</strong> {thm['retention_connection']}</p>
            </div>
            """, unsafe_allow_html=True)

            if thm.get("representative_verbatims"):
                st.markdown("**Representative Quotations:**")
                for q in thm["representative_verbatims"][:2]:
                    st.markdown(f"<div class='quote-box'>\"{q['quote']}\"<br><small>— [{q['record_id']}] via <a href='{q['url']}'>{q['source']}</a></small></div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# Module 5: Cohort & Segment Analysis
# -------------------------------------------------------------
elif menu == "👥 5. Cohort & Segment Analysis":
    st.title("👥 Cohort & Segment Analysis")
    st.markdown("Comparative behavioral analysis across investor experience and cash-flow segments.")

    tab1, tab2, tab3 = st.tabs(["First-Time vs Experienced", "Retained vs Stopped", "Income Stability"])

    with tab1:
        st.subheader("First-Time Investors vs Experienced Portfolios")
        st.markdown("""
        | Behavioral Dimension | First-Time SIP Starters | Experienced Investors (>2 Years) |
        | :--- | :--- | :--- |
        | **Initial Expectation** | High optimism; expects 15-20% compounding within 6 months. | Realistic multi-year horizon (5-7 years). |
        | **Reaction to Market Dips** | Panic selling, negative returns viewed as 'scam/loss'. | Views drawdowns as rupee-cost averaging opportunity. |
        | **Monitoring Frequency** | High anxiety; checks portfolio daily or weekly. | Infrequent checkers (monthly or quarterly). |
        | **Cash-Flow Fragility** | Vulnerable to single salary delays or emergency expenses. | Has separate 6-month liquid emergency fund. |
        """)

    with tab2:
        st.subheader("Investors Who Retain vs Those Who Discontinue")
        st.markdown("""
        | Retention Dimension | 12-Month Retained Investors | Stopped / Cancelled Investors (<12 Months) |
        | :--- | :--- | :--- |
        | **Debit Timing** | Scheduled 3–5 days *after* guaranteed salary credit date. | Scheduled on the 1st of month, leading to ECS bounces. |
        | **Fund Count** | Simple, focused (1–2 broad index/flexi-cap funds). | Overloaded with 6–8 small-cap and sectoral funds. |
        | **Pause Usage** | Utilized pause during job transitions. | Defaulted to cancellation due to opaque pause flows. |
        """)

    with tab3:
        st.subheader("Fixed Salaried vs Variable / Freelance Income")
        st.markdown("""
        * **Fixed Salaried:** Predictable cash flow; drop-offs driven by ECS bounce penalties and competing EMIs.
        * **Students & Freelancers:** Highly volatile monthly cash; rigid monthly SIP models lead to early churn when income dips.
        """)

# -------------------------------------------------------------
# Module 6: Opportunity Prioritization Matrix
# -------------------------------------------------------------
elif menu == "🎯 6. Opportunity Prioritization Matrix":
    st.title("🎯 Opportunity Prioritization Matrix")
    st.markdown("8-Dimensional Opportunity Priority Score (OPS) balancing retention impact, severity, evidence strength, and Groww addressability.")

    opp_df = pd.DataFrame(opportunities)

    # 2x2 Quadrant Chart
    fig_matrix = px.scatter(
        opp_df,
        x="prevalence_pct",
        y=[opp["scores"]["groww_addressability"] for opp in opportunities],
        size="ops_score",
        color="ops_score",
        text="title",
        labels={"x": "Sample Prevalence (%)", "y": "Groww Addressability (1-5)"},
        title="Problem Prioritization Matrix (Quadrant)",
        color_continuous_scale="Viridis"
    )
    fig_matrix.update_traces(textposition="top center")
    fig_matrix.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_matrix, use_container_width=True)

    # Candidate Cards
    st.subheader("Candidate Problem Bets Ranked by OPS")
    for opp in opportunities:
        with st.container():
            st.markdown(f"""
            <div class='metric-card'>
                <h4 style='color:#00D09C;'>[{opp['opportunity_id']}] {opp['title']} (OPS: {opp['ops_score']} / 5.0)</h4>
                <p><strong>User Problem Hypothesis:</strong> {opp['hypothesis']}</p>
                <p><strong>Prevalence:</strong> {opp['evidence_count']}/{opp['denominator']} ({opp['prevalence_pct']}%)</p>
                <p><strong>Potential Product Intervention:</strong> {opp['solution_direction']}</p>
            </div>
            """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Module 7: AI Evidence Log & Audit
# -------------------------------------------------------------
elif menu == "📜 7. AI Evidence Log & Audit":
    st.title("📜 Persistent AI Evidence Log")
    st.markdown("Auditable ledger connecting every proposed insight to verbatim citations and PM verification status.")

    for entry in evidence_log:
        with st.expander(f"[{entry['log_id']}] {entry['title']} (Status: {entry['verification_status']})"):
            st.markdown(f"**Theme:** `{entry['theme_name']}` | **Prevalence:** `{entry['evidence_count']}/{entry['denominator']} ({entry['prevalence_percentage']}%)`")
            st.markdown(f"**User Problem Hypothesis:** {entry['user_problem_hypothesis']}")
            st.markdown(f"**AI Confidence:** `{int(entry['ai_confidence'] * 100)}%`")
            st.markdown("**Direct Supporting Citations:**")
            for cit in entry["citations"]:
                st.markdown(f"<div class='quote-box'>\"{cit['quote']}\"<br><small>Source: <a href='{cit['url']}'>{cit['source']}</a></small></div>", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.button("✅ Mark Accepted", key=f"ev_acc_{entry['log_id']}")
            with c2:
                st.button("✏️ Mark Revised", key=f"ev_rev_{entry['log_id']}")
            with c3:
                st.button("❌ Mark Rejected", key=f"ev_rej_{entry['log_id']}")

# -------------------------------------------------------------
# Module 8: Research Questions & Interview Guides
# -------------------------------------------------------------
elif menu == "❓ 8. Research Questions & Interview Guides":
    st.title("❓ Research Questions & Interview Guides")
    st.markdown("Qualitative open questions and pre-drafted 1-on-1 interview scripts for user research teams.")

    st.subheader("Top Open Research Hypotheses")
    st.markdown("""
    1. **The '₹450 Penalty' Churn Effect:** What percentage of users who experience a bank bounce charge cancel their mandate within 72 hours?
    2. **Intentional vs Accidental Pause:** How many cancellations are actually temporary pauses in disguise?
    3. **First Volatility Encounter:** Does proactive education at the first negative XIRR reading protect retention?
    """)

    st.subheader("1-on-1 User Interview Script (Groww UX Research)")
    st.code("""
1. "Think back to the last time you stopped or skipped an SIP instalment. What was happening in your personal or financial life at that exact moment?"
2. "Have you ever experienced a bank bounce charge or penalty for an unsuccessful mutual fund debit? How did that make you feel about continuing?"
3. "When your portfolio first showed negative returns, what did you do inside or outside the app?"
4. "If you could temporarily adjust your monthly contribution amount during months with tight cash, would you have kept your SIP active?"
    """, language="markdown")

# -------------------------------------------------------------
# Module 9: Live Groq AI Assistant
# -------------------------------------------------------------
elif menu == "🤖 9. Live Groq AI Assistant":
    st.title("🤖 Live Groq AI Assistant (OpenAI GPT-OSS 120B Big Model)")
    st.markdown("Query the entire 321-record qualitative database in natural language using Groq's ultra-fast 120B inference engine.")

    # Model selector and connection status
    c_m1, c_m2 = st.columns([2, 1])
    with c_m1:
        model_choice = st.selectbox(
            "Select Groq LLM Engine:",
            [
                "openai/gpt-oss-120b (120B Flagship Big Model - Active)",
                "qwen/qwen3.8-27b (27B Fast Reasoning)",
                "openai/gpt-oss-20b (20B Lightweight)"
            ],
            index=0,
            help="openai/gpt-oss-120b is the 120-Billion parameter reasoning model on Groq."
        )
        selected_model = model_choice.split(" ")[0]

    with c_m2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if GROQ_API_KEY:
            st.success("🟢 Groq Connected", icon="✅")
        else:
            st.warning("⚠️ API Key Needed", icon="🔑")

    active_key = GROQ_API_KEY
    if not active_key:
        active_key = st.text_input("Enter Groq API Key:", type="password", placeholder="gsk_...")

    if not active_key:
        st.error("Please configure `GROQ_API_KEY` in `.env` or enter your key above to use the AI Assistant.")
    else:
        try:
            from groq import Groq
            client = Groq(api_key=active_key)

            # Chat history in session state
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {"role": "assistant", "content": "Hello! I am your Groww SIP Retention Discovery Assistant powered by Groq's 120B Big Model. Ask me anything about our 321 investor conversations, specific verbatims, or why students and gig workers stop their SIPs."}
                ]

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    if "reasoning" in msg and msg["reasoning"]:
                        with st.expander("🧠 View 120B Reasoning Trace", expanded=False):
                            st.caption(msg["reasoning"])
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Ask about investor churn reasons, quotes, or themes..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner(f"Analyzing qualitative database with {selected_model}..."):
                        # Ingest sample verbatims as context
                        context_snippets = []
                        for r in relevant_data[:25]:
                            context_snippets.append(f"[{r['record_id']}] {r['title']}: {r.get('classification', {}).get('verbatim_quote', r.get('raw_text', ''))[:150]}")
                        context_str = "\n".join(context_snippets)

                        system_prompt = f"""You are a senior Product Discovery AI Assistant for Groww's Growth PM team.
You have direct access to a database of 321 cleaned qualitative retail investor records regarding SIP drop-off and retention in India.
Here is a representative sample of real investor verbatims from the dataset:
{context_str}

Guidelines:
1. Always cite real verbatims and record IDs where relevant.
2. Strictly never recommend specific mutual funds, stocks, or FOMO-driven nudges.
3. Be concise, strategic, and evidence-focused."""

                        completion = client.chat.completions.create(
                            model=selected_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
                            ],
                            max_tokens=1200
                        )
                        choice = completion.choices[0].message
                        reply = choice.content or "No textual response generated."
                        reasoning = getattr(choice, 'reasoning', None)

                        if reasoning:
                            with st.expander("🧠 View 120B Reasoning Trace", expanded=False):
                                st.caption(reasoning)

                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply, "reasoning": reasoning})

        except Exception as e:
            st.error(f"Error querying Groq: {e}")

# -------------------------------------------------------------
# Module 10: Export Center
# -------------------------------------------------------------
elif menu == "📥 10. Export Center":
    st.title("📥 Export Center")
    st.markdown("Download audited datasets, theme tables, and executive discovery documents.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Cleaned Dataset")
        df_clean = pd.DataFrame(cleaned_data)
        csv_clean = df_clean.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Cleaned CSV (321 Records)",
            data=csv_clean,
            file_name="groww_sip_cleaned_records.csv",
            mime="text/csv"
        )

    with col2:
        st.subheader("Theme Clusters")
        df_themes = pd.DataFrame(theme_clusters)
        csv_themes = df_themes.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Themes CSV",
            data=csv_themes,
            file_name="groww_sip_theme_clusters.csv",
            mime="text/csv"
        )

    with col3:
        st.subheader("Executive Report")
        report_path = Path("Docs/final_discovery_report.md")
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            st.download_button(
                label="📥 Download Executive Report (MD)",
                data=report_content,
                file_name="Groww_SIP_Retention_Discovery_Report.md",
                mime="text/markdown"
            )

    st.markdown("---")
    st.subheader("Executive Discovery Report Preview")
    report_file = Path("Docs/final_discovery_report.md")
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            st.markdown(f.read())
