import networkx as nx
from typing import List, Dict, Any


def build_graph_from_txs(txs: List[Dict[str, Any]]):
    G = nx.DiGraph()
    for tx in txs:
        frm = tx["from"].lower()
        to = tx["to"].lower()
        tx_hash = tx.get("tx_hash")
        G.add_node(frm)
        G.add_node(to)
        # attach edge data keyed by tx_hash
        G.add_edge(frm, to, key=tx_hash, **{
            "amount": tx["amount"],
            "asset": tx.get("asset", "ETH"),
            "timestamp": tx.get("timestamp"),
            "tx_hash": tx_hash,
            "block": tx.get("block")
        })
    return G


def bfs_subgraph_from_graph(G, start_wallets, max_hops=3):
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
                # collect edges (u,v)
                data = G.get_edge_data(u, v)
                # edge data may be dict or nested for multi-edges
                if isinstance(data, dict):
                    # if nested dict of parallel edges, grab keys
                    try:
                        # networkx DiGraph stores attr dict
                        txh = data.get('tx_hash')
                        edges.add((u, v, txh))
                    except Exception:
                        edges.add((u, v, None))
                else:
                    edges.add((u, v, None))
                if v not in visited:
                    next_frontier.add(v)
        visited.update(frontier)
        frontier = next_frontier
    return nodes, edges
