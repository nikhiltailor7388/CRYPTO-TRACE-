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

    victim_set = {str(w or '').lower() for w in wallet_targets if w}
    vasp_set = set()
    for item in evidence:
        vasp = str(item.get('vasp') or '').strip()
        if vasp and vasp.lower() != 'unknown':
            vasp_set.add(str(item.get('to') or '').lower())
            vasp_set.add(str(item.get('from') or '').lower())

    node_list = []
    for idx, node_id in enumerate(sorted(nodes)):
        node_id_text = str(node_id)
        lower_id = node_id_text.lower()
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
            label = 'Intermediate Wallet - Hop ' + str(idx + 1)

        node_list.append({
            'id': node_id_text,
            'label': label,
            'type': node_type,
            'cluster_id': cluster_map.get(lower_id),
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
        }
        edge_list.append(edge)

    return {'nodes': node_list, 'edges': edge_list}
