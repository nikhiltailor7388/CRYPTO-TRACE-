import networkx as nx
from typing import List, Dict, Any

from backend.services.address_validator import normalize_address


def build_graph_from_txs(txs: List[Dict[str, Any]]):
    # A pair of wallets may transact more than once. A DiGraph overwrites the
    # prior transaction and causes graph/evidence disagreement.
    G = nx.MultiDiGraph()
    for tx in txs:
        chain = tx.get("source_chain") or tx.get("chain") or "ETH"
        frm = normalize_address(tx["from"], chain)
        to = normalize_address(tx["to"], chain)
        tx_hash = tx.get("tx_hash")
        G.add_node(frm)
        G.add_node(to)
        # attach edge data keyed by tx_hash
        G.add_edge(frm, to, key=tx_hash or f"edge-{G.number_of_edges()}", **{
            "amount": tx["amount"],
            "asset": tx.get("asset", "ETH"),
            "timestamp": tx.get("timestamp"),
            "tx_hash": tx_hash,
            "block": tx.get("block")
        })
    return G


def bfs_subgraph_from_graph(G, start_wallets, max_hops=3):
    # The graph retains TRON's case-sensitive Base58 addresses. EVM starts
    # still resolve case-insensitively for historical inputs.
    start = []
    for wallet in start_wallets:
        candidate = str(wallet).strip()
        start.append(candidate if candidate in G else candidate.lower())
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
                if G.is_multigraph():
                    for _, attributes in (data or {}).items():
                        edges.add((u, v, attributes.get("tx_hash")))
                elif isinstance(data, dict):
                    edges.add((u, v, data.get('tx_hash')))
                if v not in visited:
                    next_frontier.add(v)
        visited.update(frontier)
        frontier = next_frontier
    return nodes, edges


def build_graph_payload(nodes: set, edges: set, evidence: List[Dict[str, Any]], wallet_targets: List[str], wallet_clusters: List[Dict[str, Any]] = None):
    """Return a full graph payload with concrete node and edge objects for the UI."""
    evidence_by_hash = {}
    for item in evidence:
        tx_hash = str(item.get('tx_hash') or '').lower()
        if tx_hash:
            evidence_by_hash[tx_hash] = item

    cluster_map = {}
    for cluster in wallet_clusters or []:
        for member in cluster.get('members', []) or []:
            cluster_map[str(member).lower()] = cluster.get('id')

    # Derive depth from the bounded, evidence-backed edge set. The prior UI
    # label used sorted-node position, which made a real multi-hop branch look
    # like arbitrary nodes rather than an investigation path.
    node_texts = {str(node) for node in nodes}
    roots = {
        str(wallet).strip() if str(wallet).strip() in node_texts else str(wallet).strip().lower()
        for wallet in wallet_targets if wallet
    }
    depth_by_node = {root: 0 for root in roots if root in node_texts}
    outgoing = {}
    for source, target, _ in edges:
        outgoing.setdefault(str(source), set()).add(str(target))
    frontier = list(depth_by_node)
    while frontier:
        source = frontier.pop(0)
        for target in outgoing.get(source, set()):
            next_depth = depth_by_node[source] + 1
            if target not in depth_by_node or next_depth < depth_by_node[target]:
                depth_by_node[target] = next_depth
                frontier.append(target)

    victim_set = {str(w or '').lower() for w in wallet_targets if w}
    vasp_set = set()
    for item in evidence:
        vasp = str(item.get('vasp') or '').strip()
        if vasp and vasp.lower() != 'unknown':
            vasp_set.add(str(item.get('to') or '').lower())
            vasp_set.add(str(item.get('from') or '').lower())

    node_list = []
    for node_id in sorted(nodes):
        node_id_text = str(node_id)
        lower_id = node_id_text.lower()
        hop_depth = depth_by_node.get(node_id_text)
        total_in = sum(float(item.get('amount') or 0) for item in evidence if str(item.get('to') or '').lower() == lower_id)
        total_out = sum(float(item.get('amount') or 0) for item in evidence if str(item.get('from') or '').lower() == lower_id)
        if lower_id in victim_set:
            node_type = 'victim'
            label = 'Victim Wallet (Source)'
        elif lower_id in vasp_set:
            node_type = 'vasp'
            label = 'VASP / Exchange Endpoint'
        elif cluster_map.get(lower_id):
            node_type = 'cluster_member'
            label = 'Cluster Member'
        else:
            node_type = 'intermediate'
            label = 'Intermediate Wallet' + (f' - Hop {hop_depth}' if hop_depth is not None else '')

        node_list.append({
            'id': node_id_text,
            'label': label,
            'type': node_type,
            'cluster_id': cluster_map.get(lower_id),
            'hop_depth': hop_depth,
            'total_in': round(total_in, 6),
            'total_out': round(total_out, 6),
        })

    edge_list = []
    for edge_index, (source, target, tx_hash) in enumerate(sorted(edges, key=lambda item: (item[0], item[1], str(item[2] or ''))), start=1):
        source_text = str(source)
        target_text = str(target)
        tx_hash_text = str(tx_hash or '')
        tx_data = evidence_by_hash.get(tx_hash_text.lower())
        edge = {
            'id': f'edge-{edge_index}',
            'source': source_text,
            'target': target_text,
            'tx_hash': tx_hash_text,
            'amount': float((tx_data or {}).get('amount') or 0),
            'asset': (tx_data or {}).get('asset') or 'ETH',
            'timestamp': (tx_data or {}).get('timestamp') or '',
            'edge_type': 'direct',
            'confidence': None,
            'source_chain': (tx_data or {}).get('source_chain') or (tx_data or {}).get('chain') or 'ETH',
            'destination_chain': (tx_data or {}).get('destination_chain') or (tx_data or {}).get('chain') or 'ETH',
            'continuation_status': (tx_data or {}).get('continuation_status'),
            'hop': (depth_by_node.get(source_text) + 1) if source_text in depth_by_node else None,
        }
        edge_list.append(edge)

    return {'nodes': node_list, 'edges': edge_list}
