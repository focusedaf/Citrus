"""
builds a directed transaction graph from traced edges and renders it as an interactive HTML visualization using pyvis

"""

import networkx as nx
from pyvis.network import Network


def build_graph(edges):
   
    G = nx.DiGraph()
    for src, dst, value_wei, tx_hash in edges:
        value_eth = float(value_wei) / 1e18
        G.add_edge(src, dst, weight=value_eth, tx_hash=tx_hash)
    return G


def render_graph(G, tags=None, output_file="graph.html"):

    net = Network(directed=True, height="600px", width="100%", bgcolor="#1e1e1e", font_color="white")

    for node in G.nodes:
        tag = tags.get(node) if tags else None
        if tag:
            color = "#e74c3c" if tag["type"] == "exchange" else "#f39c12"
            label = f"{node[:8]}...\n({tag['label']})"
        else:
            color = "#3498db"
            label = f"{node[:8]}..."
        net.add_node(node, label=label, color=color, title=node)

    for src, dst, data in G.edges(data=True):
        label = f"{data['weight']:.5f} ETH"
        net.add_edge(src, dst, title=label, value=max(data["weight"], 0.1))

    net.show(output_file, notebook=False)
    return output_file