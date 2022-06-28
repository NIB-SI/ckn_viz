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
    ug = nx.Graph(g.copy())

    # find also neighbours on the second level to connect to the rest of the graph (if possible)
    all_neighbours = set(nodes)
    fromnodes = nodes
    for i in range(1):
        neighbours = set(itertools.chain.from_iterable([g.neighbors(node) for node in fromnodes]))  # - set(fromnodes)
        if not neighbours:
            break
        all_neighbours.update(neighbours)
        fromnodes = neighbours

    # vsi pari med all_neighbours in all_shown_nodes
    potentialEdges = []
    for fr, to in [(a, b) for a in set(all_neighbours)-set(nodes) for b in set(all_shown_nodes)-set(nodes)]:
        print('considering: ', fr, to)
        if g.has_edge(fr, to):
            edges = g.get_edge_data(fr, to)
            for k in edges:
                potentialEdges.append((fr, to, edges[k]))
        elif g.has_edge(to, fr):
            edges = g.get_edge_data(to, fr)
            for k in edges:
                potentialEdges.append((to, fr, edges[k]))

    # potentialEdges = g.subgraph(all_neighbours).edges(data=True)
    return g.subgraph([node] + list(ug.neighbors(node))), potentialEdges


def load_edge_directions(fname):
    directions = {}
    with open(fname) as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(2048))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            directions[row['intType']] = True if row['isDirected'].upper() == 'Y' else False
    return directions


def load_CKN(fname, directions):
    ckn = nx.MultiGraph()
    with open(fname) as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        for i, row in enumerate(reader):
            if i > 0:
                ckn.add_edge(row[0], row[1], type=row[2], rank=row[3], species=row[4], directed=directions[row[2]])
    return ckn


def add_attributes(ckn, fname):
    nodeAttributes = {}
    with open(fname) as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(2048))
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, dialect=dialect)
        attNames = set(reader.fieldnames) - {'nodeID'}
        for row in reader:
            nodeAttributes[row['nodeID']] = {atr: row[atr] for atr in attNames}
    nx.set_node_attributes(ckn, nodeAttributes)


def get_autocomplete_node_data(g):
    data = []
    for nodeid, attrs in g.nodes(data=True):
        elt = copy.copy(attrs)
        elt['id'] = nodeid
        elt['name'] = nodeid
        # elt = {'id': nodeid, 'name': nodeid}
        # for atr in ['name', 'synonyms', 'description', 'evidence_sentence'] + [f'{sp}_homologues' for sp in SPECIES]:
        #     elt[atr] = attrs.get(atr, '')
        # elt['synonyms'] = ', '.join(elt['synonyms'])
        data.append(elt)
    return {'node_data': data}


def extract_subgraph(g, nodes, k=1):
    nodes = [node for node in nodes if node in g.nodes]

    all_neighbours = set(nodes)
    fromnodes = nodes
    for i in range(k):
        neighbours = set(itertools.chain.from_iterable([g.neighbors(node) for node in fromnodes]))  # - set(fromnodes)
        if not neighbours:
            break
        all_neighbours.update(neighbours)
        fromnodes = neighbours
    result = g.subgraph(all_neighbours).copy()
    return result


def extract_shortest_paths(g, query_nodes):
    if len(query_nodes) == 1:
        subgraph = extract_subgraph(g, query_nodes, k=1)
        paths_nodes = subgraph.nodes()
    else:
        paths_nodes = []
        for fr, to in itertools.combinations(query_nodes, 2):
            try:
                paths = [p for p in nx.all_shortest_paths(g, source=fr, target=to)]
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


def graph2json(g, query_nodes=[]):
    groups_json = {'CKN node': {'shape': 'box',
                              'color': {'background': 'white'}}}
    nlist = []
    for nodeid, attrs in g.nodes(data=True):
        nodeData = copy.copy(attrs)
        nodeData['id'] = nodeid
        nodeData['label'] = nodeid

        if nodeid in query_nodes:
            nodeData['color'] = {'border': 'red',
                                 'background': 'white',
                                 'highlight': {'border': 'red'},  # this does not work, bug in vis.js
                                 'hover': {'border': 'red'}}  # this does not work, bug in vis.js
            nodeData['borderWidth'] = 2
        nlist.append(nodeData)

    elist = []
    for fr, to, attrs in g.edges(data=True):
        elist.append({'from': fr,
                      'to': to,
                      'label': attrs['type'],
                      'type': attrs['type'],
                      'rank': attrs['rank'],
                      'species': attrs['species'],
                      'directed': attrs['directed'],
                      'arrows': {'to': {'enabled': True}} if attrs['directed'] else {'to': {'enabled': False}}
                      })
    return {'network': {'nodes': nlist, 'edges': elist}, 'groups': groups_json}
