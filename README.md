# 📈 Groww AI-Powered SIP Retention Discovery Agent

> **An evidence-based qualitative discovery engine discovering why first-time mutual fund investors discontinue, pause, reduce, or cancel their SIPs before 12 months.**  
> Powered by **Streamlit**, **Groq 120B Big Model (`openai/gpt-oss-120b`)**, and empirical retail investor signals across Reddit, TradingQ&A, and App Store reviews.

---

## 🎯 Executive Summary & Context

* **Primary KPI:** Active SIP count ($\ge 1$ successful instalment in last 30 days) among retail investors who started their first SIP in the last 12 months.
* **Core Problem:** India's mutual fund industry experiences a ~50% drop-off in first-time SIPs before Month 12. Traditional quantitative dashboards show *that* users churned, but cannot explain *why*.
* **Solution:** This AI Discovery Agent ingests, cleans, classifies, and clusters **321 verified qualitative investor discussions**, tying every behavioral hypothesis to real verbatims and ranking interventions via an 8-dimensional Opportunity Priority Score (OPS).
* **Compliance:** Strictly adheres to SEBI regulations (zero fund/stock recommendations) and ethical growth principles (zero FOMO or artificial urgency).

---

## 🔬 Empirical Data Sources

The platform aggregates signals from four complementary qualitative channels:

| Source | Channel / Subreddit | Ingestion Method | Records | Focus Area |
| :--- | :--- | :--- | :---: | :--- |
| **Reddit** | `r/personalfinanceindia` & `r/IndiaInvestments` | Apify Actor (`trudax~reddit-scraper-lite`) | **144** | Students, irregular income, salary delay, job loss, market panic |
| **TradingQ&A** | [TradingQ&A Forum](https://tradingqna.com/) | Discourse JSON API (Zero-Key) | **150** | Bank auto-debit bounces, ECS penalties (₹450–₹590), mandate failures |
| **Play Store & App Store** | Groww App Reviews (`com.nextbillion.groww`) | Public Review Collectors | **40** | Auto-pay confusion, pause vs cancel UI friction, OTP mandate issues |
| **Total Raw** | — | — | **334** | Raw investor threads |
| **Total Cleaned** | — | Normalized & MD5 Deduplicated | **321** | Unified schema (`REC-00001` to `REC-00321`) |
| **Core Retention Signals** | — | 5-Tier Relevance Filter | **77** | Verified SIP drop-off & retention discussions |

---

## 🧠 Top Discovered Retention Hypotheses (Ranked by OPS)

1. **The Bank ECS Bounce Penalty Trap (OPS 4.71):**  
   * *Problem:* Unsuccessful auto-debit attempts trigger recurring bank bounce fees of ₹450–₹590 per failure.  
   * *Behavior:* Users cancel the mandate immediately to avoid further bank fines.  
   * *Verbatim:* *"My bank charged me ₹450 + GST penalty when SIP debited before salary arrived. I cancelled the SIP immediately."*
2. **Inflexible Emergency Liquidity Traps (OPS 4.60):**  
   * *Problem:* When unexpected life emergencies or student tuition deadlines occur, users find "Pause" opaque or buried and default to permanent cancellation.  
   * *Verbatim:* *"I needed cash for a family emergency. I wanted to pause for 2 months, but couldn't find the option, so I stopped it entirely."*
3. **Negative XIRR Panic in Months 3–6 (OPS 4.17):**  
   * *Problem:* New investors enter during market peaks; the first drawdown creates panic and regret, leading to premature redemption back to guaranteed FDs.  
   * *Verbatim:* *"Investing for 5 months and portfolio is -4.2%. FD gives 7% guaranteed. Stopped all SIPs."*
4. **Student & Irregular Income Mismatch (OPS 4.00):**  
   * *Problem:* Fixed monthly debit dates clash with irregular freelance income or pocket money cycles.

---

## 🖥️ Streamlit Workspace Modules

The Streamlit web application includes 10 dedicated modules:
1. **📊 Executive Overview:** High-level retention funnel, KPI cards, and source breakdown charts.
2. **⚠️ Data Quality & Human Review Queue:** Triage borderline records and audit deduplication stats.
3. **🔍 Conversation Explorer:** Full-text search and multi-facet filtering (Source, Stage, Behavior).
4. **🧩 Semantic Theme Clusters:** Explore the 13 baseline operational hypotheses with real quotes.
5. **👥 Cohort & Segment Analysis:** Compare First-Time vs Experienced investors and Churned vs Retained.
6. **🎯 Opportunity Prioritization Matrix:** Interactive Plotly 2x2 matrix plotting Severity vs Groww Addressability.
7. **📜 AI Evidence Log & Audit:** Audit log where Product Managers can mark hypotheses as Accepted, In Review, or Rejected.
8. **❓ Research Questions & Interview Guides:** UX research guides and 1-on-1 interview scripts.
9. **🤖 Live Groq AI Assistant:** Real-time conversational intelligence powered by Groq's **120B Flagship Big Model (`openai/gpt-oss-120b`)** with deep reasoning traces.
10. **📥 Export Center:** One-click CSV and Markdown downloads for executive decks and data teams.

---

## 🚀 Quickstart & Setup Guide

### 1. Clone the Repository
```bash
git clone <YOUR_GIT_REPO_URL>
cd AI_Discover_SIP
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Credentials
Create a `.env` file in the project root:
```ini
# Apify Token (for Reddit scraping)
APIFY_TOKEN=your_apify_token_here

# Groq API Key (for high-speed 120B reasoning)
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the Streamlit Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push this repository to your GitHub account.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
3. Click **"New app"**, select your repository, branch (`main`), and set **Main file path** to `app.py`.
4. In **Advanced settings**, add your secret key:
   ```toml
   GROQ_API_KEY = "gsk_..."
   ```
5. Click **"Deploy"** — the live app will build and run automatically!

---

## 🛡️ SEBI & Ethical Compliance Principles

* **No Stock/Fund Recommendations:** The system never suggests specific AMC schemes, fund ratings, or stock tickers.
* **No Manufactured Urgency:** Never utilizes countdown timers, fear triggers, or artificial FOMO nudges.
* **Verifiable Ground Truth:** Every conclusion links directly to an immutable verbatim quote with its original source permalink.
