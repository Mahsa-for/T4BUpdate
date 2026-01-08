"""Simple, label-driven glossary builder:
- Read Boxology JSON labels
- Extract keywords
- Use provided test domains (no LLM for now)
- Fetch arXiv abstracts per domain with a simple query
- Extract short definitions and save glossary
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Tuple

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------- Config --------------------

ARXIV_API_URL = "http://export.arxiv.org/api/query"
PAPERS_PER_DOMAIN = 5
SORT_BY = "submittedDate"  # Also used: citationCount
SORT_METHODS = ["submittedDate", "citationCount"]  # Fetch from both
OUTPUT_DIR = pathlib.Path(__file__).parent / "dataset"
OUTPUT_GLOSSARY = OUTPUT_DIR / "glossary.txt"

# Your test domains (override LLM while testing)
PREDICTED_DOMAINS: List[str] = [
    "normalization",
    "transformation",
    "machine learning",
    "phycology",
    "machine learning in phycology",
    "clustered data",
    "semantic model",
    "semantic model in phycology",
    "Authentic Diagnosis",
]

# Structural/low-signal words to ignore
STOPWORDS: Set[str] = {
    "a","an","the","of","to","and","or","for","in","on","by","with","from",
    "data","number","symbol","semanticmodel","statisticalmodel","rules","process",
    "input","output","model","models","raw","cleaned","numeric","semantic","support",
    "actor","engineer","generate","train","deduce","transform","embed","artifacts"
}

# LLM (Ollama only)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct")

def _extract_json_block(text: str) -> str | None:
    i, j = text.find("{"), text.rfind("}")
    if i != -1 and j != -1 and j > i:
        return text[i:j+1]
    return None

def gen_search_queries_ollama(keywords: List[str]) -> List[str]:
    """Ask Ollama to produce 3–10 good scientific search queries."""
    prompt = (
        "You are an instruction LLM for scientific query generation.\n"
        "Normalize acronyms (e.g., FCM→fuzzy c-means), add synonyms, and disambiguate.\n"
        f"Retrieve recent approaches for {', '.join(sorted(set(keywords)))} "
        "Return strict JSON: {\"queries\": [\"...\"]}. No prose.\n\n"
        f"Labels/keywords: {', '.join(sorted(set(keywords)))}"
    )
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.3, "num_predict": 400}}
    try:
        r = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        r.raise_for_status()
        resp = r.json().get("response", "")
        jb = _extract_json_block(resp) or "{}"
        data = json.loads(jb)
        queries = [q.strip() for q in data.get("queries", []) if isinstance(q, str)]
        if 3 <= len(queries) <= 12:
            return queries
    except Exception as e:
        print(f"✗ Ollama query gen failed: {e}")
    # Fallback: simple expansions from keywords
    base = [k for k in keywords if len(k) > 3][:6]
    return [f'"{b}" AND (fuzzy OR clustering OR modeling)' for b in base]

def tfidf_rank(papers: List[Dict[str, str]], queries: List[str], top_k: int = 5) -> List[Dict[str, str]]:
    """Rank papers by cosine similarity between TF‑IDF of queries and paper texts."""
    if not papers:
        return []
    docs = [f"{p.get('title','')} {p.get('summary','')}".strip() for p in papers]
    corpus = queries + docs
    vec = TfidfVectorizer(stop_words="english", max_features=20000)
    X = vec.fit_transform(corpus)
    Q = X[:len(queries)]
    D = X[len(queries):]
    sims = cosine_similarity(Q, D)  # shape: (num_queries, num_docs)
    scores = sims.max(axis=0)  # best-match per doc
    ranked = sorted(zip(scores.tolist(), papers), key=lambda x: x[0], reverse=True)
    return [p for _, p in ranked[:top_k]]

def select_top_papers(domain_papers: Dict[str, List[Dict[str, str]]], queries: List[str], top_k: int = 5) -> Dict[str, List[Dict[str, str]]]:
    """Apply TF‑IDF ranking per domain and keep top_k."""
    out: Dict[str, List[Dict[str, str]]] = {}
    for domain, papers in domain_papers.items():
        out[domain] = tfidf_rank(papers, queries, top_k=top_k)
    return out

# -------------------- Label ingestion and keywording --------------------

def load_labels(data_dir: pathlib.Path) -> List[str]:
    """Collect all 'label' strings from any Boxology JSON (handles dict or list roots)."""

    def collect(node, acc: List[str]) -> None:
        if isinstance(node, dict):
            v = node.get("label")
            if isinstance(v, str) and v.strip():
                acc.append(v.strip())
            for child in node.values():
                collect(child, acc)
        elif isinstance(node, list):
            for item in node:
                collect(item, acc)

    labels: List[str] = []
    for p in data_dir.glob("*.json"):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        collect(obj, labels)

    # dedupe preserving order
    seen, out = set(), []
    for l in labels:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out

def extract_keywords(labels: List[str], max_keywords: int = 60) -> List[str]:
    phrases = [re.sub(r"\s+", " ", l.strip()) for l in labels if isinstance(l, str) and l.strip()]
    tokens: List[str] = []
    for l in phrases:
        for tok in re.split(r"[^A-Za-z0-9\+\-]+", l):
            t = tok.strip()
            if len(t) >= 3 and t.lower() not in STOPWORDS:
                tokens.append(t)
    bigrams: List[str] = []
    for l in phrases:
        ws = [w for w in re.split(r"[^A-Za-z0-9\+\-]+", l) if len(w) >= 3]
        for i in range(len(ws) - 1):
            if ws[i].lower() in STOPWORDS or ws[i+1].lower() in STOPWORDS:
                continue
            bigrams.append(f"{ws[i]} {ws[i+1]}")
    candidates = phrases + bigrams + tokens
    seen, out = set(), []
    for c in candidates:
        key = c.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(c)
        if len(out) >= max_keywords:
            break
    return out

# -------------------- arXiv --------------------

def build_query(domain: str, domain_terms: List[str], combined_terms: List[str]) -> str:
    pool = []
    for t in (domain_terms or []) + (combined_terms or []):
        t = str(t).strip().replace('"', "")
        if not t or len(t) < 3:
            continue
        pool.append(f'all:"{t}"' if " " in t else f"all:{t}")
        if len(pool) >= 8:
            break
    terms_clause = " OR ".join(pool) if pool else f'all:"{domain}"'
    return f"({terms_clause}) AND all:\"{domain}\""

def fetch_arxiv(query: str, max_results: int, sort_by: str = "submittedDate") -> str:
    params = {"search_query": query, "max_results": max_results, "sortBy": sort_by}
    headers = {"User-Agent": os.getenv("USER_AGENT", "Boxology-Glossary/1.0")}
    r = requests.get(ARXIV_API_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def parse_arxiv(xml_text: str) -> List[Dict[str, str]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    papers: List[Dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        title = " ".join(title.split())
        summary = " ".join(summary.split())
        if title or summary:
            papers.append({"title": title, "summary": summary})
    return papers

# -------------------- Term extraction and glossary --------------------

def extract_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 20]

def extract_definitions(papers: List[Dict[str, str]], candidates: List[str]) -> Dict[str, str]:
    defs: Dict[str, str] = {}
    cand = []
    seen = set()
    for t in candidates:
        t2 = " ".join(str(t).lower().split())
        if len(t2) > 2 and t2 not in seen:
            seen.add(t2)
            cand.append(t2)
    cand.sort(key=lambda x: (-1 if " " in x else 0, -len(x)))  # prefer multiword

    for paper in papers:
        title = paper.get("title", "")
        summary = paper.get("summary", "")
        sentences = extract_sentences(summary)
        if not sentences:
            continue
        for term in cand:
            if term in defs:
                continue
            for s in sentences:
                if term in s.lower():
                    defs[term] = s.strip()
                    break
            if term not in defs:
                txt = f"{title}. {summary}".lower()
                if term in txt and sentences:
                    defs[term] = sentences[0]
    return defs

def build_glossary(domain_papers: Dict[str, List[Dict[str, str]]], terms_by_domain: Dict[str, List[str]], combined_terms: List[str]) -> str:
    lines = [
        "# Scientific Glossary - Generated from arXiv Papers",
        f"# Domains: {', '.join(domain_papers.keys())}",
        f"# Total papers: {sum(len(p) for p in domain_papers.values())}",
        "",
    ]
    for domain, papers in domain_papers.items():
        if not papers:
            continue
        lines.append(f"## Domain: {domain}")
        lines.append("")
        candidates = sorted(set((terms_by_domain.get(domain) or terms_by_domain.get(domain.lower()) or []) + (combined_terms or [])))
        term_defs = extract_definitions(papers, candidates)
        for term in sorted(term_defs.keys(), key=str.lower)[:20]:
            definition = " ".join(term_defs[term].split())
            if len(definition) > 250:
                definition = definition[:247] + "..."
            lines.append(f"**{term}**: {definition}")
        lines.append("")
        lines.append(f"### Recent papers in {domain}:")
        for i, p in enumerate(papers[:2], 1):
            summ = p["summary"]
            if len(summ) > 250:
                summ = summ[:247] + "..."
            lines.append(f"{i}. {p['title']}: {summ}")
        lines.append("")
    return "\n".join(lines)

# -------------------- Main --------------------

def main() -> None:
    print("=" * 70)
    print("Simple arXiv Glossary Generator (label-driven, test domains)")
    print("=" * 70)

    data_dir = OUTPUT_DIR
    json_paths = list(data_dir.glob("*.json"))
    if not json_paths:
        print("No Boxology JSON found in dataset/. Add T4B-*.json and retry.")
        return

    labels = load_labels(data_dir)
    print(f"✓ Collected {len(labels)} labels")
    keywords = extract_keywords(labels, max_keywords=60)
    print(f"✓ Extracted {len(keywords)} keywords")

    # Test domains provided by you (no domain LLM)
    domains = PREDICTED_DOMAINS
    terms_by_domain: Dict[str, List[str]] = {d: [] for d in domains}
    combined = keywords

    # Generate search queries via Ollama (instruction LLM)
    queries = gen_search_queries_ollama(keywords)
    print(f"✓ Generated {len(queries)} search queries")

    # Fetch papers from multiple sort methods (recent + most cited)
    domain_papers: Dict[str, List[Dict[str, str]]] = {}
    for domain in domains:
        query = build_query(domain, terms_by_domain.get(domain, []), combined)
        print(f"\nFetching papers for: {domain}")
        print(f"Query: {query}")
        all_papers: List[Dict[str, str]] = []
        
        for sort_method in SORT_METHODS:
            try:
                print(f"  Fetching {PAPERS_PER_DOMAIN} papers (sorted by {sort_method})...")
                xml = fetch_arxiv(query, PAPERS_PER_DOMAIN, sort_by=sort_method)
                papers = parse_arxiv(xml)
                all_papers.extend(papers)
                print(f"  ✓ Found {len(papers)} papers")
            except Exception as e:
                print(f"  ✗ Error fetching with {sort_method}: {e}")
        
        # Deduplicate by title
        seen_titles = set()
        unique_papers = []
        for p in all_papers:
            title = p.get('title', '').lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(p)
        
        domain_papers[domain] = unique_papers
        print(f"✓ Total unique papers for {domain}: {len(unique_papers)}")

    # Rank papers per domain using TF‑IDF (embedding-like retrieval)
    domain_papers = select_top_papers(domain_papers, queries, top_k=5)

    glossary = build_glossary(domain_papers, terms_by_domain, combined)
    OUTPUT_GLOSSARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GLOSSARY.write_text(glossary, encoding="utf-8")
    print(f"\nSaved: {OUTPUT_GLOSSARY.resolve()}")

if __name__ == "__main__":
    main()
