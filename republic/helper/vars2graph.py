import networkx as nx

def vars2graph(vars):
    G_differentiated = nx.Graph()
    d_nodes = sorted(vars)
    for node in d_nodes:
        attached_nodes = vars[node]
        G_differentiated.add_node(node)
        for nod in attached_nodes:
            G_differentiated.add_edge(node, nod)
    cl = (G_differentiated.subgraph(c).copy() for c in nx.connected_components(G_differentiated))
    cc = [list(c) for c in list(cl)]
    return cc