import csv
import os
import pickle
# import subprocess
import itertools
import json
import re
import copy
from html.entities import name2codepoint as n2cp

import networkx as nx

# from fuzzywuzzy import fuzz, process

import requests

RE_HTML_ENTITY = re.compile(r'&(#?)([xX]?)(\w{1,8});', re.UNICODE)


# taken from gensim.utils
def decode_htmlentities(text):
    def safe_unichr(intval):
        try:
            return chr(intval)
        except ValueError:
            # ValueError: chr() arg not in range(0x10000) (narrow Python build)
            s = "\\U%08x" % intval
            # return UTF16 surrogate pair
            return s.decode('unicode-escape')

    def substitute_entity(match):
        try:
            ent = match.group(3)
            if match.group(1) == "#":
                # decoding by number
                if match.group(2) == '':
                    # number is in decimal
                    return safe_unichr(int(ent))
                elif match.group(2) in ['x', 'X']:
                    # number is in hex
                    return safe_unichr(int(ent, 16))
            else:
                # they were using a name
                cp = n2cp.get(ent)
                if cp:
                    return safe_unichr(cp)
                else:
                    return match.group()
        except Exception:
            # in case of errors, return original input
            return match.group()
    return RE_HTML_ENTITY.sub(substitute_entity, text)


def expand_nodes(g, nodes, all_shown_nodes):
    if len(nodes) > 1:
        print('Error : expand not implemented for more than one node')
    node = nodes[0]
    # ug = nx.Graph(g)

    # find also neighbours on the second level to connect to the rest of the graph (if possible)
    all_neighbours = set(nodes)
    fromnodes = nodes
    for i in range(1):
        neighbours = set(itertools.chain.from_iterable([g.to_undirected().neighbors(node) for node in fromnodes]))  # - set(fromnodes)
        if not neighbours:
            break
        all_neighbours.update(neighbours)
        fromnodes = neighbours

    # # vsi pari med all_neighbours in all_shown_nodes
    # potentialEdges = []
    # for fr, to in [(a, b) for a in set(all_neighbours)-set(nodes) for b in set(all_shown_nodes)-set(nodes)]:
    #     print('considering: ', fr, to)
    #     if g.has_edge(fr, to):
    #         edges = g.get_edge_data(fr, to)
    #         for k in edges:
    #             print(fr, to, k, edges[k])
    #             potentialEdges.append((fr, to, edges[k]))

    # potentialEdges = g.subgraph(all_neighbours ).edges(data=True)
    return g.subgraph(all_neighbours)#, potentialEdges

def load_CKN(fname):

    with open(fname, "rb") as handle:
        handle.readline() # header
        ckn = nx.read_edgelist(handle,
                    delimiter="\t",
                    create_using=nx.DiGraph,
                    data=[
                        ('effect', str),
                        ('type', str),
                        ('rank', str),
                        ('species', str),
                        ('isDirected', int),
                        ('isTFregulation', int),
                        ('interactionSources', str),
                        ("hyperlink", str),
                    ])
    return ckn


def add_attributes(ckn, fname):
    nodeAttributes = {}
    with open(fname) as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(2048))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        attNames = set(reader.fieldnames) - {'nodeID'}
        for row in reader:
            nodeAttributes[row['node_ID']] = {atr: row[atr] for atr in attNames}
    nx.set_node_attributes(ckn, nodeAttributes)


def get_autocomplete_node_data(g):
    data = []
    for nodeid, attrs in g.nodes(data=True):
        elt = copy.copy(attrs)
        elt['id'] = nodeid
        elt['name'] = nodeid
        # elt = {'id': nodeid, 'name': nodeid}
        for atr in ['short_name', 'TAIR', 'full_name', 'GMM']:
            elt[atr] = attrs.get(atr, '')
        for i, s in enumerate(attrs.get('synonyms', '').split("|")):
            elt[f'synonyms_{i}'] = s
        data.append(elt)
    return {'node_data': data}


def extract_subgraph(g, nodes, k=1):
    nodes = [node for node in nodes if node in g.nodes]
    all_neighbours = set(nodes)
    fromnodes = nodes
    for i in range(k):
        neighbours = set(itertools.chain.from_iterable([g.to_undirected().neighbors(node) for node in fromnodes]))  # - set(fromnodes)
        if not neighbours:
            break
        all_neighbours.update(neighbours)
        fromnodes = neighbours
    result = g.subgraph(all_neighbours).copy()
    # print(type(g), "result: ", result.number_of_nodes(), result.number_of_edges())
    return result


def extract_shortest_paths(g, query_nodes):
    if len(query_nodes) == 1:
        subgraph = extract_subgraph(g, query_nodes, k=1)
        paths_nodes = subgraph.nodes()
    else:
        paths_nodes = []
        for fr, to in itertools.combinations(query_nodes, 2):
            print("here")
            try:
                paths = [p for p in nx.all_shortest_paths(g.to_undirected(), source=fr, target=to)]
                # print(paths)
                paths_nodes.extend([item for path in paths for item in path])
            except nx.NetworkXNoPath:
                print('No paths:', fr, to)
                pass
        # add back also nodes with no paths
        # this also covers the case with no paths at all
        paths_nodes = set(paths_nodes).union(query_nodes)

    return g.subgraph(paths_nodes).copy()


def filter_edges_for_display(g):
    to_remove = []
    for fr, to, key, attrs in g.edges(data=True, keys=True):
        # show edges according to Ziva's rule
        if not attrs['directed'] and attrs['type'] != 'binding':
            to_remove.append((fr, to, key))
            print(f'Removed: {fr}{to}: {attrs}')
    g.remove_edges_from(to_remove)





EDGE_TYPE_STYLE = {
    'binding':  {
        'color': {'color': "#57007D", 'hover': '#0000FF'},
        'label': 'binding',
        'dashes': True
    },
    'small RNA interactions': {
        'color': {'color': "#BA3E6D", 'hover': '#0000FF'},
        'label': 'sRNA'
    },
    'transcription factor regulation': {
        'color': {'color': "#0E9B9B", 'hover': '#0000FF'},
        'label': 'TF'
    },
    'post-translational modification': {
        'color': {'color': "#AA4000", 'hover': '#0000FF'},
        'label': 'PTM'
    },
    'other': {
        'color': {'color': "#0099CC", 'hover': '#0000FF'},
        'label': 'other'
    }
}

EDGE_EFFECT_STYLE = {
    'unk':  {
        'arrows': {'to': {'enabled': True, 'type': 'circle', 'scaleFactor':0.8}},
    },
    'inh': {
        'arrows': {'to': {'enabled': True, 'type': 'bar', 'scaleFactor':0.8}}
    },
    'act': {
        'arrows': {'to': {'enabled': True, 'type': 'arrow', 'scaleFactor':0.8}}
    },
    'phosphorylation': {
        'arrows': {'to': {'enabled': True, 'type': 'circle', 'scaleFactor':0.8}}
    },
    'act/inh': {
        'arrows': {'to': {'enabled': True, 'type': 'arrow', 'scaleFactor':0.8}}
    }
}

RANK_WIDTH = {
    '0': 4,
    '1': 3.2,
    '2': 2.5,
    '3': 1,
    '4': 0.6,
}

def edge_style(attrs):
    e = EDGE_TYPE_STYLE[attrs['type']].copy()
    e['arrows'] = EDGE_EFFECT_STYLE[attrs['effect']]['arrows'].copy()
    if not attrs['isDirected']:
        e['arrows']['from'] = e['arrows']['to']
    e['width'] = RANK_WIDTH[attrs["rank"]]

    return e

NODE_STYLE = {
    'complex': {
        'shape': 'box',
        'color': {'background': '#9cd6e4', 'border': '#40b0cb'}
    },
    # plant genes -- shades of green,
    'protein_coding': {
        'shape': 'box',
        'color': {'background': '#66CDAA', 'border': '#48c39a'}
    },
    'mirna': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'transposable_element_gene': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'pseudogene': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'antisense_long_noncoding_rna': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'pre_trna': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'other_rna': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'small_nucleolar_rna': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'small_nuclear_rna': {
        'shape': 'box',
        'color': {'background': '#98FB98', 'border': '#057c05'}
    },
    'biotic': {
        'shape': 'diamond',
        'color': {'background': '#cd853f', 'border': '#965e27'}
    },
    'abiotic': {
        'shape': 'diamond',
        'color': {'background': '#cd3f40', 'border': '#a62b2c'}
    },
    # every one else,
    'metabolite': {
        'shape': 'circle',
        'color': {'background': '#fff0f5', 'border': '#ff6799'}
    },
    'process': {
        'shape': 'box',
        'color': {'background': '#c4bcff', 'border': '#6e5aff'}
    },
    'default': {
        'shape': 'box',
        'color': {'background': 'White', 'border': '#6c7881'}
    }
}

def graph2json(g, query_nodes=None):
    if not query_nodes:
        query_nodes = []

    # groups_json = {'CKN node': {'shape': 'box',
    #                           'color': {'background': 'white'}}}

    groups = set()
    for nodeid, attrs in g.nodes(data=True):
        groups.add(attrs['node_type'])

    groups_json = {}
    for elt in groups:
        if elt in NODE_STYLE:
            groups_json[elt] = NODE_STYLE[elt]
        else:
            groups_json[elt] = NODE_STYLE['default']

    nlist = []
    for nodeid, attrs in g.nodes(data=True):
        group = attrs['node_type']

        nodeData = copy.copy(attrs)
        nodeData['id'] = nodeid
        nodeData['group'] = group

        nodeData['label'] = attrs['short_name']



        if nodeid in query_nodes:
            nodeData['color'] = {'background': groups_json[group]['color']['background'],
                                 'border': 'red',
                                 'highlight': {'border': 'red'},  # this does not work, bug in vis.js
                                 'hover': {'border': 'red'}}  # this does not work, bug in vis.js
            nodeData['borderWidth'] = 2

        nlist.append(nodeData)

    elist = []
    for fr, to, attrs in g.edges(data=True):
        e = {**attrs, **edge_style(attrs)}
        e['from'] = fr
        e['to'] = to

        # print(fr, to)
        elist.append(e)

    return {'network': {'nodes': nlist, 'edges': elist}, 'groups': groups_json}
