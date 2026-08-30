from collections import defaultdict
from typing import Any, Dict, Iterable, List


def summarize_graph(graph: Any, wallet_addresses: Iterable[str]) -> Dict[str, Any]:
    wallet_set = set(wallet_addresses)
    nodes = list(graph.nodes())
    edges = list(graph.edges(data=True))

    degree_map = {node: graph.degree(node) for node in nodes}
    max_degree = max(degree_map.values(), default=0)
    suspicious_nodes = []
    for node, degree in degree_map.items():
        if node in wallet_set:
            continue
        if degree >= 3:
            suspicious_nodes.append({"address": node, "degree": degree, "weight": round(sum(v.get("weight", 0) for _, _, v in graph.edges(node, data=True)), 4)})

    suspicious_nodes.sort(key=lambda item: item["degree"], reverse=True)
    largest_outflow = max(
        (
            {"address": source, "total": round(sum(data.get("weight", 0) for _, _, data in graph.edges(source, data=True)), 4)}
            for source in nodes
            if source not in wallet_set
        ),
        key=lambda item: item["total"],
        default={"address": None, "total": 0},
    )

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "max_degree": max_degree,
        "largest_outflow": largest_outflow,
        "suspicious_nodes": suspicious_nodes[:5],
        "wallets_in_scope": len(wallet_set),
    }
