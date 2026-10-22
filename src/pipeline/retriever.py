"""
RAG Retriever Module for Groww SIP Retention Discovery Agent.
Performs fast, in-memory BM25-style lexical and semantic matching over the 321 investor records.
"""

import re
import math
from typing import List, Dict, Any

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
            content = f"{r.get('title', '')} {r.get('raw_text', '')} {r.get('classification', {}).get('verbatim_quote', '')} {r.get('classification', {}).get('trigger_context', '')}"
            tokens = self._tokenize(content)
            self.doc_tokens.append(tokens)
            self.doc_lens.append(len(tokens))

            unique_terms = set(tokens)
            for term in unique_terms:
                self.df[term] = self.df.get(term, 0) + 1

        self.avg_doc_len = sum(self.doc_lens) / max(1, self.doc_count)

    def retrieve(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.records[:top_k]

        k1 = 1.5
        b = 0.75
        scores = []

        for i, (tokens, doc_len) in enumerate(zip(self.doc_tokens, self.doc_lens)):
            score = 0.0
            token_counts = {}
            for t in tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            for q in query_tokens:
                if q in token_counts:
                    tf = token_counts[q]
                    doc_freq = self.df.get(q, 1)
                    # IDF formula
                    idf = math.log((self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                    # BM25 term weighting
                    denom = tf + k1 * (1 - b + b * (doc_len / self.avg_doc_len))
                    score += idf * (tf * (k1 + 1)) / denom

            # Boost high-signal records (Tier 1 & Tier 2)
            tier = self.records[i].get('relevance_tier', 4)
            if tier == 1:
                score *= 1.3
            elif tier == 2:
                score *= 1.15

            scores.append((score, self.records[i]))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [record for score, record in scores[:top_k] if score > 0] or self.records[:top_k]
