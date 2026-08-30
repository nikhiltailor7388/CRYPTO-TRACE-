import json
from pathlib import Path
import networkx as nx
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_FILE = DATA_DIR / "eth_cache.json"

def load_cached_transactions():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def build_graph():
    """Build a DiGraph from cached normalized transactions.
    Returns (DiGraph, tx_list)
    """
    txs = load_cached_transactions()
    G = nx.DiGraph()
    for tx in txs:
        frm = tx["from"].lower()
        to = tx["to"].lower()
        tx_hash = tx.get("tx_hash")
        # node attrs can include suspected_balance placeholder
        G.add_node(frm)
        G.add_node(to)
        # edge key by tx_hash to allow multiple parallel edges
        G.add_edge(frm, to, key=tx_hash, **{
            "amount": tx["amount"],
            "asset": tx.get("asset", "ETH"),
            "timestamp": tx["timestamp"],
            "tx_hash": tx_hash,
            "block": tx.get("block")
        })
    return G, txs


def bfs_subgraph(G, start_wallets, max_hops=3):
    """Return nodes and edges reachable from start_wallets up to max_hops."""
    start = [s.lower() for s in start_wallets]
    visited = set()
    frontier = set(start)
    edges = set()
    nodes = set(start)
    for hop in range(1, max_hops+1):
        next_frontier = set()
        for u in frontier:
            if u not in G:
                continue
            for v in G.successors(u):
                nodes.add(v)
                nodes.add(u)
                # collect edges (u,v) with attributes
                for key, data in G[u][v].items():
                    # when using simple DiGraph, G[u][v] returns dict of attributes
                    # For safety, try to extract tx_hash from data
                    txh = None
                    if isinstance(data, dict):
                        txh = data.get('tx_hash')
                    edges.add((u, v, txh))
                if v not in visited:
                    next_frontier.add(v)
        visited.update(frontier)
        frontier = next_frontier
    return nodes, edges
