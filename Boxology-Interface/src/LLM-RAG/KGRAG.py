"""Knowledge Graph RAG system using TransE embeddings.

Pipeline:
- Load TransE embeddings and KG structure
- Load JSON boxology file
- For queries about nodes: find similar entities in KG, retrieve context
- Provide descriptions based on KG knowledge
"""

from __future__ import annotations

import json
import pathlib
import re
import os
import socket
from typing import Dict, List, Tuple

import numpy as np
import requests


# File paths - relative to this file's location
_CURRENT_DIR = pathlib.Path(__file__).parent
ENTITY_EMBEDDINGS_FILE = _CURRENT_DIR / "model_output" / "entity_embeddings.npy"
RELATION_EMBEDDINGS_FILE = _CURRENT_DIR / "model_output" / "relation_embeddings.npy"
ENTITY_MAP_FILE = _CURRENT_DIR / "model_output" / "entity_map.txt"
RELATION_MAP_FILE = _CURRENT_DIR / "model_output" / "relation_map.txt"
TRIPLES_FILE = _CURRENT_DIR / "model_output" / "triples.txt"
KG_NT_FILE = _CURRENT_DIR.parent.parent / "dataset" / "Tool4BoxologyKG.nt"
GLOSSARY_FILE = _CURRENT_DIR.parent.parent / "dataset" / "glossary.txt"

# Config
EMBEDDING_DIM = 100
TOP_K = 5  # Number of similar entities to retrieve
RESPONSE_TEMPLATE = """Here is what I know about this node based on the boxology JSON and KG:\n{body}"""


# LLM API configuration with smart host detection
def _detect_ollama_host() -> str:
    """Detect the correct Ollama host based on environment."""
    # 1. Check environment variable (highest priority)
    env_host = os.getenv("OLLAMA_HOST")
    if env_host:
        print(f"[KGRAG] Using OLLAMA_HOST from environment: {env_host}")
        return env_host
    
    # 2. Check if running in Docker container
    if os.path.exists('/.dockerenv'):
        print("[KGRAG] Detected Docker environment, using host.docker.internal")
        return "host.docker.internal"
    
    # 3. Try to connect to localhost
    try:
        sock = socket.create_connection(("localhost", 11434), timeout=1)
        sock.close()
        print("[KGRAG] Ollama found on localhost")
        return "localhost"
    except (socket.error, socket.timeout):
        pass
    
    # 4. Try host.docker.internal (Docker Desktop)
    try:
        sock = socket.create_connection(("host.docker.internal", 11434), timeout=1)
        sock.close()
        print("[KGRAG] Ollama found on host.docker.internal")
        return "host.docker.internal"
    except (socket.error, socket.timeout):
        pass
    
    # 5. Default to localhost
    print("[KGRAG] Using default localhost (Ollama may not be available)")
    return "localhost"


OLLAMA_HOST = _detect_ollama_host()
OLLAMA_API_URL = f"http://{OLLAMA_HOST}:11434/api/generate"  # Use detected host
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Option 2: Use Hugging Face API (requires token for some models)
HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
HF_API_TOKEN = os.getenv("HF_API_TOKEN", None)

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "200"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

print(f"[KGRAG] Ollama API URL: {OLLAMA_API_URL}")


def load_embeddings() -> Tuple[np.ndarray, np.ndarray]:
    """Load entity and relation embeddings."""
    entity_bytes = ENTITY_EMBEDDINGS_FILE.read_bytes()
    relation_bytes = RELATION_EMBEDDINGS_FILE.read_bytes()
    
    entity_embeddings = np.frombuffer(entity_bytes, dtype=np.float32)
    relation_embeddings = np.frombuffer(relation_bytes, dtype=np.float32)
    
    return entity_embeddings, relation_embeddings


def load_entity_map() -> Tuple[Dict[int, str], Dict[str, int], Dict[int, str]]:
    """Load entity index mappings."""
    idx_to_uri = {}
    uri_to_idx = {}
    idx_to_label = {}
    
    with ENTITY_MAP_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                idx = int(parts[0])
                uri = parts[1]
                label = parts[2]
                idx_to_uri[idx] = uri
                uri_to_idx[uri] = idx
                idx_to_label[idx] = label
    
    return idx_to_uri, uri_to_idx, idx_to_label


def load_relation_map() -> Tuple[Dict[int, str], Dict[int, str]]:
    """Load relation index mappings."""
    idx_to_uri = {}
    idx_to_label = {}
    
    with RELATION_MAP_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                idx = int(parts[0])
                uri = parts[1]
                label = parts[2]
                idx_to_uri[idx] = uri
                idx_to_label[idx] = label
    
    return idx_to_uri, idx_to_label


def load_triples() -> List[Tuple[int, int, int]]:
    """Load indexed triples."""
    triples = []
    with TRIPLES_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                h, r, t = int(parts[0]), int(parts[1]), int(parts[2])
                triples.append((h, r, t))
    return triples


def parse_nt_triple(line: str) -> Tuple[str, str, str] | None:
    """Parse N-Triples line."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    
    pattern = r'<([^>]+)>\s+<([^>]+)>\s+<([^>]+)>|<([^>]+)>\s+<([^>]+)>\s+"([^"]+)"'
    match = re.match(pattern, line)
    
    if match:
        if match.group(1):
            return (match.group(1), match.group(2), match.group(3))
        elif match.group(4):
            return (match.group(4), match.group(5), match.group(6))
    return None


def build_entity_context(entity_idx: int, triples: List[Tuple[int, int, int]], 
                        entity_labels: Dict[int, str], relation_labels: Dict[int, str]) -> str:
    """Build context description for an entity from its triples."""
    outgoing = []
    incoming = []
    
    for h, r, t in triples:
        if h == entity_idx:
            rel = relation_labels.get(r, f"rel_{r}")
            tail = entity_labels.get(t, f"entity_{t}")
            outgoing.append(f"{rel} → {tail}")
        elif t == entity_idx:
            rel = relation_labels.get(r, f"rel_{r}")
            head = entity_labels.get(h, f"entity_{h}")
            incoming.append(f"{head} → {rel}")
    
    entity_name = entity_labels.get(entity_idx, f"entity_{entity_idx}")
    context_parts = [f"Entity: {entity_name}"]
    
    if outgoing:
        context_parts.append(f"Relationships: {'; '.join(outgoing[:5])}")
    if incoming:
        context_parts.append(f"Related by: {'; '.join(incoming[:5])}")
    
    return " | ".join(context_parts)


def summarize_node(node: Dict[str, str], contexts: List[str]) -> str:
    """Heuristic summary combining node metadata and nearby KG contexts."""
    parts = []
    label = node.get("label") or node.get("name") or "Unknown"
    ntype = node.get("name") or node.get("type") or ""
    pattern = node.get("pattern") or ""
    parts.append(f"Node: {label}")
    if ntype:
        parts.append(f"Type: {ntype}")
    if pattern:
        parts.append(f"Design Pattern: {pattern}")
    if contexts:
        parts.append(f"Nearby KG relations: {contexts[0]}")
    return " | ".join(parts)


def find_similar_entities(query_text: str, entity_embeddings: np.ndarray,
                         entity_labels: Dict[int, str], top_k: int = TOP_K) -> List[Tuple[int, float]]:
    """Find entities with labels similar to query text."""
    # Simple text matching for now - could be enhanced with sentence embeddings
    query_lower = query_text.lower()
    
    # Score entities by label similarity
    scores = []
    for idx, label in entity_labels.items():
        label_lower = label.lower()
        
        # Exact match
        if query_lower == label_lower:
            scores.append((idx, 1.0))
        # Contains query
        elif query_lower in label_lower:
            scores.append((idx, 0.8))
        # Query contains label
        elif label_lower in query_lower:
            scores.append((idx, 0.6))
        # Partial word match
        else:
            query_words = set(query_lower.split())
            label_words = set(label_lower.split())
            overlap = len(query_words & label_words)
            if overlap > 0:
                scores.append((idx, 0.4 * overlap / max(len(query_words), len(label_words))))
    
    # Sort by score and return top_k
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


def find_entity_by_id(node_id: str, entity_labels: Dict[int, str], 
                     entity_uris: Dict[int, str]) -> int | None:
    """Find entity index by node ID from JSON."""
    node_id_clean = node_id.lower().replace("_", "").replace("-", "")
    
    for idx, uri in entity_uris.items():
        uri_clean = uri.lower().replace("_", "").replace("-", "")
        if node_id in uri or node_id_clean in uri_clean:
            return idx
    
    # Try matching by label
    for idx, label in entity_labels.items():
        label_clean = label.lower().replace("_", "").replace("-", "")
        if node_id_clean in label_clean:
            return idx
    
    return None


def load_json_boxology(json_path: pathlib.Path) -> Dict:
    """Load JSON boxology file."""
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_json_nodes(boxology_data: Dict) -> List[Dict]:
    """Extract all nodes from JSON boxology."""
    nodes = []
    
    for boxology in boxology_data.get("boxologies", []):
        for pattern in boxology.get("DesignPattern", []):
            # Extract inputs
            for inp in pattern.get("input", []):
                nodes.append({
                    "id": inp.get("id"),
                    "label": inp.get("label"),
                    "name": inp.get("name"),
                    "type": "input",
                    "pattern": pattern.get("label")
                })
            
            # Extract outputs
            for out in pattern.get("output", []):
                nodes.append({
                    "id": out.get("id"),
                    "label": out.get("label"),
                    "name": out.get("name"),
                    "type": "output",
                    "pattern": pattern.get("label")
                })
            
            # Extract process
            proc = pattern.get("process", {})
            if proc:
                nodes.append({
                    "id": proc.get("id"),
                    "label": proc.get("label"),
                    "name": proc.get("name"),
                    "type": "process",
                    "pattern": pattern.get("label")
                })
    
    return nodes


class KGRAG:
    def __init__(self):
        print("Loading KG embeddings and mappings...")
        self.entity_embeddings, self.relation_embeddings = load_embeddings()
        self.entity_idx_to_uri, self.entity_uri_to_idx, self.entity_idx_to_label = load_entity_map()
        self.relation_idx_to_uri, self.relation_idx_to_label = load_relation_map()
        self.triples = load_triples()
        
        # Reshape embeddings
        num_entities = len(self.entity_idx_to_label)
        num_relations = len(self.relation_idx_to_label)
        self.entity_embeddings = self.entity_embeddings.reshape(num_entities, EMBEDDING_DIM)
        self.relation_embeddings = self.relation_embeddings.reshape(num_relations, EMBEDDING_DIM)
        
        print(f"Loaded {num_entities} entities, {num_relations} relations, {len(self.triples)} triples")
        
        self.current_json_nodes = []
        self.current_kg_data = None  # ✅ Track the actual KG data
        self.glossary_text = self._load_glossary()
        
        # Test LLM availability
        print(f"\nChecking LLM availability...")
        self.llm_available = self._check_llm_availability()
        if self.llm_available:
            print("✓ LLM API is available")
        else:
            print("⚠ No LLM API available, will use deterministic responses only")

    def _load_glossary(self) -> str:
        if GLOSSARY_FILE.exists():
            try:
                text = GLOSSARY_FILE.read_text(encoding="utf-8").strip()
                if text:
                    print(f"Loaded glossary from {GLOSSARY_FILE}")
                return text
            except Exception as exc:
                print(f"Warning: could not read glossary: {exc}")
        else:
            print("No glossary file found; consider adding ./dataset/glossary.txt for domain hints.")
        return ""
    
    def _check_llm_availability(self) -> bool:
        """Check if any LLM API is available."""
        # Try Ollama with detected host
        try:
            print(f"  Checking Ollama at {OLLAMA_HOST}:11434...")
            response = requests.get(f"http://{OLLAMA_HOST}:11434/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                print(f"  ✓ Ollama available with models: {model_names[:3]}")
                return True
        except Exception as e:
            print(f"  ✗ Ollama not available: {e}")
        
        # Try HuggingFace
        if HF_API_TOKEN:
            try:
                print("  Checking HuggingFace API...")
                headers = {"Content-Type": "application/json"}
                headers["Authorization"] = f"Bearer {HF_API_TOKEN}"
                response = requests.post(HF_API_URL, headers=headers, json={"inputs": "test"}, timeout=5)
                if response.status_code in [200, 503]:
                    print("  ✓ HuggingFace API available")
                    return True
            except Exception as e:
                print(f"  ✗ HuggingFace API error: {e}")
        
        return False
    
    def load_json_data(self, boxology_data: Dict):
        """Load KG data directly from dictionary."""
        print(f"\nLoading KG data from dictionary...")
        self.current_kg_data = boxology_data  # ✅ Store the data
        self.current_json_nodes = extract_json_nodes(boxology_data)
        print(f"Extracted {len(self.current_json_nodes)} nodes from KG data")
        
        print("\nAvailable nodes:")
        for i, node in enumerate(self.current_json_nodes[:10], 1):
            print(f"  {i}. [{node['type']}] {node['label']} (ID: {node['id']})")
        if len(self.current_json_nodes) > 10:
            print(f"  ... and {len(self.current_json_nodes) - 10} more")
    
    def load_json(self, json_path: pathlib.Path):
        """Load a JSON boxology file."""
        print(f"\nLoading JSON boxology from {json_path}...")
        boxology_data = load_json_boxology(json_path)
        self.load_json_data(boxology_data)
    
    def describe_node_by_data(self, node_data: Dict) -> str:
        """Describe a specific node based on its data."""
        if not self.current_json_nodes:
            return "Error: No KG data loaded. Please create a KG first."
        
        node_id = node_data.get("id", "")
        node_label = node_data.get("label", "")
        
        matching_node = None
        for node in self.current_json_nodes:
            if node.get("id") == node_id:
                matching_node = node
                break
        
        if not matching_node:
            return f"Error: Node with ID '{node_id}' not found in current KG."
        
        return self.describe_node(node_label or node_id)

    def describe_node(self, query: str) -> str:
        """Describe a node based on KG knowledge."""
        matching_json_nodes = []
        query_lower = query.lower()
        
        for node in self.current_json_nodes:
            node_id = node.get("id", "").lower()
            node_label = node.get("label", "").lower()
            node_name = node.get("name", "").lower()
            
            if query_lower in node_id or query_lower in node_label or query_lower in node_name:
                matching_json_nodes.append(node)
        
        if not matching_json_nodes:
            for node in self.current_json_nodes:
                node_label = node.get("label", "").lower()
                if any(word in node_label for word in query_lower.split()):
                    matching_json_nodes.append(node)
        
        contexts = []
        best_node = None
        
        if matching_json_nodes:
            best_node = matching_json_nodes[0]
            
            # Build simple context for LLM
            search_text = f"{best_node['label']} {best_node['name']}"
            similar = find_similar_entities(
                search_text,
                self.entity_embeddings,
                self.entity_idx_to_label,
                top_k=3
            )
            
            for entity_idx, score in similar:
                context = build_entity_context(
                    entity_idx, self.triples,
                    self.entity_idx_to_label,
                    self.relation_idx_to_label
                )
                contexts.append(context)
        
        # Generate clean output
        if best_node:
            summary_text = f"{best_node['label']} (Type: {best_node['name']})"
            llm_answer = self.generate_answer(best_node['label'], contexts, summary_text)
            
            output = f"**{best_node['label']}**\n\n"
            output += f"**Type:** {best_node['name']}\n"
            output += f"**Pattern:** {best_node['pattern']}\n\n"
            output += f"**Description:**\n{llm_answer}"
            
            return output
        else:
            return f"No information found for '{query}'"

    def generate_answer(self, query: str, contexts: List[str], summary: str) -> str:
        """Generate answer using LLM based on KG structure."""
        if not self.llm_available:
            return "LLM not available. This node is part of the knowledge graph representing a component in the boxology design pattern."
        
        kg_context = self._build_kg_context(contexts)
        
        prompt = (
            "You are an AI assistant analyzing a boxology knowledge graph node.\n"
            f"Node: {summary}\n\n"
            "Context from knowledge graph:\n" + kg_context + "\n\n"
            "Consider other nodes in neighbor and explain how those effect on eachother.\n\n"
            "Consider the role of each node as boxology, process, input, output, model or pattern.\n"
            "Provide a brief, clear explanation (2-3 sentences) of what this node represents and its role in the system. "
            "Focus on practical meaning, not technical IDs.\n\n"
            "Answer:"
        )
        
        # Try Ollama FIRST
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": TEMPERATURE, "num_predict": MAX_NEW_TOKENS}
            }
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "").strip()
                if answer:
                    return answer
        except Exception as e:
            print(f"[KGRAG] Ollama request failed: {e}")
        
        # Try HuggingFace as fallback
        try:
            headers = {"Content-Type": "application/json"}
            if HF_API_TOKEN:
                headers["Authorization"] = f"Bearer {HF_API_TOKEN}"
            
            payload = {
                "inputs": prompt,
                "parameters": {"max_new_tokens": MAX_NEW_TOKENS, "temperature": TEMPERATURE}
            }
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    answer = result[0].get("generated_text", "").strip()
                    if "Answer:" in answer:
                        answer = answer.split("Answer:")[-1].strip()
                    return answer if answer else "(Empty LLM response)"
        except Exception as e:
            print(f"[KGRAG] HuggingFace request failed: {e}")
        
        return "(LLM request failed - please install Ollama: https://ollama.com/download/windows)"
    
    def _build_kg_context(self, contexts: List[str]) -> str:
        """Build rich KG context showing entity relationships."""
        context_lines = []
        seen_entities = set()
        
        for context_str in contexts[:5]:
            context_lines.append(f"• {context_str}")
            
            parts = context_str.split("|")
            for part in parts:
                if "Entity:" in part:
                    entity_label = part.split("Entity:")[-1].strip()
                    
                    for idx, label in self.entity_idx_to_label.items():
                        if label.lower() == entity_label.lower() and idx not in seen_entities:
                            seen_entities.add(idx)
                            neighbors = self._get_entity_neighbors(idx)
                            if neighbors:
                                context_lines.append(f"  Related to: {neighbors}")
                            break
        
        context_lines.append("\nKey relationship patterns found:")
        rel_counts = {}
        for _, r, _ in self.triples[:100]:
            rel = self.relation_idx_to_label.get(r, f"rel_{r}")
            rel_counts[rel] = rel_counts.get(rel, 0) + 1
        
        for rel, count in sorted(rel_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            context_lines.append(f"  • {rel} (appears {count} times)")
        
        return "\n".join(context_lines)
    
    def _get_entity_neighbors(self, entity_idx: int, max_neighbors: int = 3) -> str:
        """Get neighbor entities and relationships."""
        neighbors = []
        
        for h, r, t in self.triples:
            if h == entity_idx:
                rel = self.relation_idx_to_label.get(r, f"rel_{r}")
                tail = self.entity_idx_to_label.get(t, f"entity_{t}")
                neighbors.append(f"{rel}→{tail}")
        
        for h, r, t in self.triples:
            if t == entity_idx:
                rel = self.relation_idx_to_label.get(r, f"rel_{r}")
                head = self.entity_idx_to_label.get(h, f"entity_{h}")
                neighbors.append(f"{head}→{rel}")
        
        return "; ".join(neighbors[:max_neighbors]) if neighbors else "(no direct neighbors)"
