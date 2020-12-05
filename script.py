import itertools
import joblib
import json
import networkx as nx
import nltk
import numpy as np
import re
import spacy
from flask import Flask, request
from flask_cors import CORS, cross_origin
from functools import reduce
from spacy.lang.en import TAG_MAP

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
nlp = spacy.load("en_core_web_sm")
edge_model = joblib.load("edge_model.joblib")
context_vectorizer = joblib.load("context_vectorizer.joblib")
cfdist = joblib.load("cfdist.joblib")
compression_model = joblib.load("compression_model.joblib")
regression_vectorizer = joblib.load("regression_vectorizer.joblib")

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


def match(uncomp, comp):
    uncomp_indicies = [i for i in range(len(uncomp))]
    comp_indicies = []
    uncomp_w, comp_w = 0, 0
    while uncomp_w < len(uncomp) and comp_w < len(comp):
        if uncomp[uncomp_w] == comp[comp_w]:
            comp_indicies.append(uncomp_w)
            comp_w += 1
        uncomp_w += 1
    return comp_indicies


def POS_features(s, c):
    doc = nlp(" ".join(s))
    s_indices = set([i for i in range(len(s))])
    c_indices = set(match(s, c))
    c_deletions = s_indices - c_indices
    uncomp_doc = [token.tag_ for token in doc]
    del_doc = [token.tag_ for token in doc if token.i in c_deletions]
    pos_feat = {}
    for pos in list(TAG_MAP.keys()):
        pos_feat[pos + "_UNCOMP"] = uncomp_doc.count(pos)
        pos_feat[pos + "_DEL"] = del_doc.count(pos)
    return pos_feat


def Gramm(c, cfdist):
    m = len(c)
    if m > 2:
        likelihood_candidate = reduce(lambda x, y: x*y, [cfdist[(t1, t2)].freq(t3) for t1, t2, t3 in nltk.trigrams(c)])
    elif m == 0:
        return 0
    else:
        likelihood_candidate = 0
    return (1 / m) * np.log(1 + likelihood_candidate) #+1 backoff


def get_regression_features(uncomp_tok, curr_tok):
    features = {
        "grammaticality_rate": Gramm(curr_tok, cfdist),
        # "importance_rate": Imp_Rate(D, uncomp_tok, curr_tok),
        # "average_deletion_depth": average_deletion_depth(uncomp_tok, curr_tok),
        # "average_inclusion_depth": average_inclusion_depth(uncomp_tok, curr_tok)
    }
    features.update(POS_features(uncomp_tok, curr_tok))
    return features


@app.route("/")
@cross_origin()
def main():
    try:
        sentence = request.args.get("sentence")
        end = ""
        if sentence is None or sentence == "":
            return json.dumps({"msg": "usage: ?sentence=[your sentence here]",
                            "compressions": None})
        if re.match("\W", sentence[-1]):
            end = sentence[-1]
            sentence = sentence[:-1]
        candidate_compressions = generate_candidate_compressions(nlp,
                                                                edge_model,
                                                                context_vectorizer,
                                                                sentence)
        regression_feats = [get_regression_features(sentence, c) for c in candidate_compressions]
        ranks = compression_model.predict(regression_vectorizer.transform(regression_feats))
        return json.dumps({"msg": "success",
                        "compressions": list(sorted(zip(ranks, [f"{c}{end}" for c in candidate_compressions]),
                                                    key=lambda x: -x[0]))})
    except Exception as e:
        return json.dumps({"msg": f"server encountered an error: {e}", "compressions": None})
