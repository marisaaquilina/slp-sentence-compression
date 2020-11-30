import itertools
import joblib
import networkx as nx
import spacy
from flask import Flask, request

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")
edge_model = joblib.load("edge_model.joblib")
context_vectorizer = joblib.load("context_vectorizer.joblib")

def nbor(token, offset):
    try:
        nbor = token.nbor(offset)
        return nbor
    except:
        return None


def pos(token):
    if token: 
        return token.pos_
    return "None"


def matching_head(token):
    l, r = -1, 1
    matching_heads = {token: 1}
    while True:
        if nbor(token, l):
            matching_heads[nbor(token, l)] = int(token.head == token.nbor(l).head)
            l -= 1
        else:
            break
    while True:
        if nbor(token, r):
            matching_heads[nbor(token, r)] = int(token.head == token.nbor(r).head)
            r += 1
        else:
            break
    return matching_heads


def context(e):
    V = {}
    V["0_dep"] = e.dep_
    V["1_head_pos"] = e.head.pos_
    V["2_modifier"] = e.pos_
    V["4_head_head_pos"] = e.head.head.pos_
    V["5_head_dep"] = e.head.dep_
    V["6_-3_head_pos"] = pos(nbor(e.head, -3)) # e.head.l.l.l.pos_
    V["7_-2_head_pos"] = pos(nbor(e.head, -2)) # e.head.l.l.pos_
    V["8_-1_head_pos"] = pos(nbor(e.head.i, -1)) # e.head.l.pos_
    V["9_+1_head_pos"] = pos(nbor(e.head, 1)) # e.head.r.pos_
    V["10_+2_head_pos"] = pos(nbor(e.head, 2)) # e.head.r.r.pos_
    V["11_+3_head_pos"] = pos(nbor(e.head, 3)) # e.head.r.r.r.pos_
    V["12_-3_modifier_pos"] = pos(nbor(e, -3)) # e.l.l.l.pos_
    V["13_-2_modifier_pos"] = pos(nbor(e, -2)) # e.l.l.pos_
    V["14_-1_modifier_pos"] = pos(nbor(e, -1)) # e.l.pos_
    V["15_+1_modifier_pos"] = pos(nbor(e, 1)) # e.r.pos_
    V["16_+2_modifier_pos"] = pos(nbor(e, 2)) # e.r.r.pos_
    V["17_+3_modifier_pos"] = pos(nbor(e, 3)) # e.r.r.r.pos_
    return V


def get_root(doc):
    sent = next(doc.sents, None)
    return sent.root if sent is not None else sent


def get_edge_probs(edge_model, vectorizer, edge):
    return list(zip(edge_model.classes_,
                    edge_model.predict_proba(vectorizer
                                             .transform(context(edge)))[0]))


def get_probs(edge_model, vectorizer, edge, threshold=0.2):
    probs = get_edge_probs(edge_model, vectorizer, edge)
    filtered_probs = [p for p in probs if p[1] > threshold]
    return filtered_probs


def get_groups(edge_model, vectorizer, doc):
    return [[(d, p[0]) for p in get_probs(edge_model, vectorizer, d)]
            for d in doc]


def get_possible_paths(groups):
    return list(itertools.product(*groups))


def generate_candidate_compressions(nlp, edge_model, vectorizer, sentence):
    doc = nlp(sentence)
    root = get_root(doc)
    groups = get_groups(edge_model, vectorizer, doc)
    candidates = set()
    for path in get_possible_paths(groups):
        path_graph = nx.DiGraph() 
        for edge, label in path:
            path_graph.add_edge(edge.head.i, edge.i)
        for head, modifier in list(nx.edge_bfs(path_graph, root.i)):
            label = [l for e, l in path if e.i == modifier][0]
            if path_graph.has_node(modifier) and label == "del_l":
                subtree = list(nx.edge_bfs(path_graph, modifier))
                path_graph.remove_edges_from([(head, modifier), *subtree])
            elif path_graph.has_node(modifier) and label == "del_u":
                subtree = list(nx.edge_bfs(path_graph, modifier))
                path_graph = nx.DiGraph()
                path_graph.add_edges_from(subtree)
        if len(path_graph.edges) > 0:
            candidates.add(" ".join([doc[n].text
                                     for n
                                     in sorted(list(set([n
                                                         for e
                                                         in path_graph.edges
                                                         for n
                                                         in e])))]))
    return candidates


@app.route("/")
def main():
    sentence = request.args.get("sentence")
    if sentence is None or sentence == "":
        return "usage: ?sentence=[your sentence here]"
    candidate_compressions = generate_candidate_compressions(nlp,
                                                             edge_model,
                                                             context_vectorizer,
                                                             sentence)
    return "".join([f"<p>{c}</p>"
                    for c
                    in sorted(candidate_compressions, key=lambda x: len(x))])
