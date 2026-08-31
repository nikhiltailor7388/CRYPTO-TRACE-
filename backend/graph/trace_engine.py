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


def bounded_trace(
    graph: nx.DiGraph, start_wallets: List[str], max_hops: int = 3
) -> Tuple[List[str], List[Tuple], List[str]]:
    """Follow the largest outbound edge at each hop, bounded by max_hops.

    At each hop, from each current frontier node, the single successor
    with the largest edge ``amount`` is followed.  Traversal stops at
    ``max_hops``, at dead-ends, or when no successor exists.

    Returns ``(nodes, edges, path)`` where:
      - ``nodes`` — sorted list of every wallet encountered within the hop bound.
      - ``edges`` — list of ``(from, to, amount, tx_hash)`` tuples for traversed edges.
      - ``path``  — ordered list of wallets forming the traced fund-flow chain
                    (start wallet → largest successor → …).
    """
    nodes: set = set()
    edges: List[Tuple] = []
    path: List[str] = []

    start_lower = [s.lower() for s in start_wallets if s]
    nodes.update(start_lower)

    for start in start_lower:
        if start not in path:
            path.append(start)
        current = start
        for _ in range(max_hops):
            if current not in graph:
                break
            successors = list(graph.successors(current))
            if not successors:
                break
            best_succ = None
            best_amount = -1.0
            best_data: dict = {}
            for succ in successors:
                data = graph.get_edge_data(current, succ)
                if not isinstance(data, dict):
                    continue
                amount = float(data.get("amount") or 0.0)
                if amount > best_amount:
                    best_amount = amount
                    best_succ = succ
                    best_data = data
            if best_succ is None:
                break
            nodes.add(best_succ)
            tx_hash = best_data.get("tx_hash")
            edges.append((current, best_succ, best_amount, tx_hash))
            if best_succ not in path:
                path.append(best_succ)
            current = best_succ

    return sorted(nodes), edges, path
