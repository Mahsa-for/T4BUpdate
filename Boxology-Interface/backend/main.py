from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys, os, socket, importlib, traceback

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LLM_RAG_PATH = SRC / "LLM-RAG"

for p in (str(SRC), str(ROOT), str(LLM_RAG_PATH)):
    if p not in sys.path:
        sys.path.insert(0, p)

def _detect_host(service_name: str = "boxology_kg") -> str:
    env_host = os.getenv("SPARQL_HOST")
    if env_host:
        return env_host
    try:
        socket.gethostbyname(service_name)
        return service_name
    except OSError:
        return "localhost"

_kg_host = _detect_host()
SPARQL_ENDPOINT = f"http://{_kg_host}:8890/sparql"
SPARQL_UPDATE_ENDPOINT = f"http://{_kg_host}:8890/sparql-auth"
print(f"[BOOT] Virtuoso host={_kg_host}")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Store the current KG data in memory
current_kg_data = None
rag_instance = None

def _get_rag_instance():
    """Get or create RAG instance."""
    global rag_instance
    if rag_instance is None:
        try:
            from KGRAG import KGRAG
            rag_instance = KGRAG()
            print("[RAG] KGRAG instance created successfully")
        except Exception as e:
            print(f"[RAG] Error creating KGRAG instance: {e}")
            traceback.print_exc()
            return None
    return rag_instance


def _fresh_kg_module():
    # Drop any cached kg_creation modules
    for name in list(sys.modules.keys()):
        if name.startswith("kg_creation"):
            del sys.modules[name]
    import kg_creation.kg_creation as kg_module
    importlib.reload(kg_module)  # ensure fresh code + globals
    return kg_module

@app.post("/api/kg")
async def api_create_kg(source: dict):
    global current_kg_data
    try:
        ids = [b.get("id") for b in source.get("boxologies", [])]
        print(f"[API] incoming boxologies={ids}")
        kg_module = _fresh_kg_module()
        result = kg_module.create_kg(source)
        if not isinstance(result, dict):
            result = {"mode": "unknown"}
        
        # Store the current KG data
        current_kg_data = source
        print(f"[API] Stored KG data with {len(source.get('boxologies', []))} boxologies")
        
        # Load KG data into RAG system
        try:
            rag = _get_rag_instance()
            if rag is not None:
                rag.load_json_data(source)
                print(f"[API] KG data loaded into RAG system with {len(rag.current_json_nodes)} nodes")
        except Exception as e:
            print(f"[API] Warning: Could not load KG into RAG: {e}")
            traceback.print_exc()
        
        return {
            "status": "ok",
            "mode": result.get("mode"),
            "triples_len": result.get("triples_len"),
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kg/current")
async def get_current_kg():
    """Get the currently created KG data"""
    if current_kg_data is None:
        raise HTTPException(status_code=404, detail="No KG has been created yet")
    return current_kg_data

@app.post("/api/kg/node-description")
async def get_node_description(node_data: dict):
    """Get LLM description for a specific node"""
    global current_kg_data
    
    if current_kg_data is None:
        raise HTTPException(status_code=404, detail="No KG has been created yet. Please create a KG first.")
    
    try:
        node_id = node_data.get("id")
        node_label = node_data.get("label", "")
        print(f"[API] Getting description for node: {node_id} ({node_label})")
        
        # Get RAG instance
        rag = _get_rag_instance()
        if rag is None:
            return {
                "status": "error",
                "node_id": node_id,
                "description": "⚠️ RAG system not available. Check backend logs for initialization errors."
            }
        
        # Load current KG data into RAG if needed
        if not rag.current_json_nodes or rag.current_kg_data != current_kg_data:
            print("[API] Loading current KG data into RAG...")
            rag.load_json_data(current_kg_data)
            print(f"[API] RAG now has {len(rag.current_json_nodes)} nodes loaded")
        
        # Get description from RAG
        description = rag.describe_node(node_label or node_id)
        
        return {
            "status": "ok",
            "node_id": node_id,
            "description": description
        }
    except Exception as e:
        error_msg = f"Error getting node description: {str(e)}"
        print(f"[API] {error_msg}")
        traceback.print_exc()
        return {
            "status": "error",
            "node_id": node_data.get("id", "unknown"),
            "description": f"⚠️ Error: {str(e)}"
        }

@app.get("/")
async def root():
    return {"status": "running", "sparql_query": SPARQL_ENDPOINT, "sparql_update": SPARQL_UPDATE_ENDPOINT}


@app.get("/api/health")
async def health():
    """Health plus RAG availability."""
    rag = _get_rag_instance()
    return {
        "status": "running",
        "rag_available": rag is not None,
        "kg_loaded": current_kg_data is not None,
        "sparql_endpoint": SPARQL_ENDPOINT,
    }