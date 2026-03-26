from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from database import load_all_data, db_exists
from graph_builder import build_graph, graph_to_json
from llm_query import process_query

GRAPH_DATA = {"nodes": [], "edges": []}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global GRAPH_DATA
    print("🚀 Starting Order-to-Cash Graph API...")
    
    # Load data only if DB doesn't exist yet
    if not db_exists():
        load_all_data()
    else:
        print("✅ Using existing database")

    print("🔨 Building graph...")
    G = build_graph()
    GRAPH_DATA = graph_to_json(G)
    print(f"✅ Graph ready: {len(GRAPH_DATA['nodes'])} nodes, {len(GRAPH_DATA['edges'])} edges")
    yield

app = FastAPI(title="Order-to-Cash Graph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Order-to-Cash Graph API", "status": "running"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "nodes": len(GRAPH_DATA.get("nodes", [])),
        "edges": len(GRAPH_DATA.get("edges", []))
    }

@app.get("/graph")
def get_graph():
    return GRAPH_DATA

@app.get("/graph/stats")
def get_graph_stats():
    nodes = GRAPH_DATA.get("nodes", [])
    type_counts = {}
    for n in nodes:
        t = n.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    return {
        "total_nodes": len(nodes),
        "total_edges": len(GRAPH_DATA.get("edges", [])),
        "by_type": type_counts
    }

class QueryRequest(BaseModel):
    query: str

@app.post("/chat")
def chat(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    result = process_query(req.query.strip())
    return result

@app.get("/schema")
def get_schema_endpoint():
    from database import get_schema
    return get_schema()
