from collections import deque
from typing import Iterable, List, Tuple

import networkx as nx


def build_transaction_graph(transactions: Iterable[dict]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for tx in transactions:
        frm = str(tx.get("from") or "").lower()
        to = str(tx.get("to") or "").lower()
        if not frm or not to:
            continue
        graph.add_node(frm)
        graph.add_node(to)
        graph.add_edge(
            frm,
            to,
            amount=float(tx.get("amount") or 0.0),
            asset=tx.get("asset", "ETH"),
            tx_hash=tx.get("tx_hash"),
            timestamp=tx.get("timestamp"),
            block=tx.get("block"),
            source_url=tx.get("source_url"),
        )
    return graph


def bounded_trace(graph: nx.DiGraph, start_wallets: List[str], max_hops: int = 3):
    """Follow the largest outbound edge at each hop, bounded by max_hops. Returns nodes and edges."""
    visited = set()
    frontier = deque((w.lower() for w in start_wallets if w))
    nodes = set(frontier)
    edges = []
    for _ in range(max_hops):
        if not frontier:
            break
        next_frontier = deque()
        while frontier:
            node = frontier.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node not in graph:
                continue
            successors = list(graph.successors(node))
            if not successors:
                continue
            for succ in successors:
                data = graph.get_edge_data(node, succ)
                if not isinstance(data, dict):
                    continue
                amount = float(data.get("amount") or 0.0)
                nodes.add(node)
                nodes.add(succ)
                edges.append((node, succ, amount, data.get("tx_hash")))
                if succ not in visited:
                    next_frontier.append(succ)
        frontier = next_frontier
    return sorted(nodes), edges
