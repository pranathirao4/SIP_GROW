"""
RAG Retriever Module for Groww SIP Retention Discovery Agent.
Performs fast, in-memory BM25-style lexical and causal matching over the cleaned investor dataset.
Calculates real empirical prevalence:
  - Exact matching record count
  - Independent unique conversation thread count (deduplicated by root URL)
  - Identifies counterevidence records (users who stayed invested / resolved the friction)
  - Flags data sufficiency to prevent ungrounded AI hallucinations
"""

import re
import math
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse


def clean_root_url(url: str) -> str:
    """Normalize URL to its root thread/page to accurately count unique conversations."""
    if not url:
        return "unknown_conversation"
    try:
        parsed = urlparse(url)
        path = parsed.path
        if "reddit.com" in parsed.netloc:
            m = re.match(r'(/r/[^/]+/comments/[a-z0-9]+)', path)
            if m:
                return f"https://www.reddit.com{m.group(1)}"
        elif "tradingqna.com" in parsed.netloc:
            m = re.match(r'(/t/[^/]+/\d+)', path)
            if m:
                return f"https://tradingqna.com{m.group(1)}"
        elif "youtube.com" in parsed.netloc:
            video_id = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id.group(1)}"
        return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip('/')
    except Exception:
        return url


class SIPRetriever:
    def __init__(self, records: List[Dict[str, Any]]):
        self.records = records
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9]{2,}\b', text)
        stopwords = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'for', 'of',
            'or', 'by', 'with', 'from', 'as', 'it', 'this', 'that', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'but', 'if'
        }
        return [t for t in tokens if t not in stopwords]

    def _build_index(self):
        self.doc_count = len(self.records)
        self.doc_tokens = []
        self.df = {}  # Document frequency for each term
        self.doc_lens = []

        for r in self.records:
            # Combine title, text, tags, and quotes for comprehensive search
            clf = r.get("classification", {})
            content = f"{r.get('title', '')} {r.get('raw_text', '')} {clf.get('verbatim_quote', '')} {clf.get('trigger_context', '')} {clf.get('underlying_problem', '')} {clf.get('observable_behaviour', '')}"
            tokens = self._tokenize(content)
            self.doc_tokens.append(tokens)
            self.doc_lens.append(len(tokens))

            unique_terms = set(tokens)
            for term in unique_terms:
                self.df[term] = self.df.get(term, 0) + 1

        self.avg_doc_len = sum(self.doc_lens) / max(1, self.doc_count)

    def _score_records(self, query: Any) -> List[Tuple[float, Dict[str, Any]]]:
        # Handle string or list of expanded query phrases
        if isinstance(query, list):
            primary_query = query[0] if query else ""
            expanded_queries = query[1:] if len(query) > 1 else []
        else:
            primary_query = str(query)
            expanded_queries = []

        primary_tokens = self._tokenize(primary_query)
        expanded_tokens = []
        for eq in expanded_queries:
            expanded_tokens.extend(self._tokenize(eq))

        all_query_tokens = set(primary_tokens + expanded_tokens)
        if not all_query_tokens:
            return [(1.0, r) for r in self.records]

        k1 = 1.5
        b = 0.75
        scores = []

        for i, (tokens, doc_len) in enumerate(zip(self.doc_tokens, self.doc_lens)):
            score = 0.0
            token_counts = {}
            for t in tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            for q in all_query_tokens:
                if q in token_counts:
                    tf = token_counts[q]
                    doc_freq = self.df.get(q, 1)
                    idf = math.log((self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                    denom = tf + k1 * (1 - b + b * (doc_len / self.avg_doc_len))
                    weight = 1.0 if q in primary_tokens else 0.55
                    score += weight * (idf * (tf * (k1 + 1)) / denom)

            # Boost Personal Experience records significantly
            r = self.records[i]
            tag = r.get("primary_tag") or r.get("classification", {}).get("primary_intent")
            if tag == "PERSONAL_EXPERIENCE":
                score *= 3.0
            elif tag == "OFF_TOPIC":
                score *= 0.1

            # Source / Tier adjustments
            tier = r.get('relevance_tier')
            if tier == "Tier 1: Directly Relevant" or tier == 1:
                score *= 1.35
            elif tier == "Tier 3: In-App & Mandate Friction" or tier == 3:
                score *= 1.25

            scores.append((score, r))

        scores.sort(key=lambda x: x[0], reverse=True)
        return scores

    def retrieve(self, query: Any, top_k: int = 20) -> List[Dict[str, Any]]:
        """Standard retriever interface returning top_k records."""
        scores = self._score_records(query)
        positive = [record for score, record in scores if score > 0]
        # Prefer personal experience items
        pe_records = [r for r in positive if r.get("primary_tag") == "PERSONAL_EXPERIENCE"]
        if len(pe_records) >= top_k:
            return pe_records[:top_k]
        return positive[:top_k] if positive else self.records[:top_k]

    def retrieve_with_evidence_stats(self, query: Any, top_k: int = 20) -> Dict[str, Any]:
        """
        Enriched retriever interface returning:
          - primary_matches: top_k records (personal experience ranked highest)
          - counterevidence_matches: records showing users who stayed invested / continued
          - prevalence_stats: exact matching count, unique conversation count, data sufficiency flag
        """
        scores = self._score_records(query)
        positive_records = [record for score, record in scores if score > 0]

        # Prioritize PERSONAL_EXPERIENCE items
        pe_matches = [r for r in positive_records if r.get("primary_tag") == "PERSONAL_EXPERIENCE"]
        other_matches = [r for r in positive_records if r.get("primary_tag") != "PERSONAL_EXPERIENCE"]

        combined_candidates = pe_matches + other_matches
        if not combined_candidates:
            combined_candidates = self.records[:top_k]

        primary_matches = combined_candidates[:top_k]

        # Calculate exact conversation counts across ALL positive matching records
        all_conv_urls = set()
        sources_found = set()
        counterevidence_candidates = []

        for r in combined_candidates:
            u = r.get("url", "")
            root_u = clean_root_url(u)
            if root_u != "unknown_conversation":
                all_conv_urls.add(root_u)

            src = r.get("source", "unknown")
            sources_found.add(src)

            # Check for counterevidence (continued / maintained active SIP)
            clf = r.get("classification", {})
            action = clf.get("action", "").lower()
            combined_txt = f"{r.get('title', '')} {r.get('raw_text', '')}".lower()
            if action == "continued" or any(w in combined_txt for w in ["continued", "stayed invested", "did not stop", "still investing", "restarted", "success"]):
                if len(counterevidence_candidates) < 3 and r["record_id"] not in [p["record_id"] for p in primary_matches]:
                    counterevidence_candidates.append(r)

        total_matching = len(combined_candidates)
        unique_conv_count = len(all_conv_urls) if all_conv_urls else max(1, len(primary_matches))

        # Data Sufficiency Assessment
        if unique_conv_count >= 8:
            data_sufficiency = "HIGH (Strong recurring pattern across multiple independent threads)"
        elif unique_conv_count >= 3:
            data_sufficiency = "MODERATE (Observed in multiple threads, but requires primary validation)"
        else:
            data_sufficiency = "SPARSE / ISOLATED (Limited to 1-2 examples; treat with caution, do not overgeneralize)"

        return {
            "primary_matches": primary_matches,
            "counterevidence_matches": counterevidence_candidates,
            "stats": {
                "total_matching_records": total_matching,
                "unique_conversations_count": unique_conv_count,
                "sources_represented": list(sources_found),
                "data_sufficiency": data_sufficiency
            }
        }
