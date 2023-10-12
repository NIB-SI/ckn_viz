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


import graph_tool as gt
from graph_tool import util as gt_util
from graph_tool import topology as gt_topology
from graph_tool.centrality import pagerank

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



class CKN(object):

    def __init__(self,  edge_path, node_path, force=False, headers={}):

        self.graph = self.load_CKN(edge_path, node_path)
        self.node_search_data = self.get_autocomplete_node_data()

    def load_CKN(self,  edge_path, node_path):

        ckn = gt.load_graph_from_csv(
            edge_path,
            directed=False,
            eprop_types=[
                "string",
                "string",
                "string",
                "string",
                "bool",
                "bool",
                "string",
                "string"
            ],
            skip_first=True,
            strip_whitespace=True,
            csv_options={"delimiter":"\t"})

        # help from https://bbengfort.github.io/2016/06/graph-tool-from-networkx/
        tname = "string"
        with open(node_path, "r") as node_file:
            header = node_file.readline()
            header = header.strip().split("\t")

            for prop_name in header:
                prop = ckn.new_vertex_property(tname) # Create the PropertyMap
                ckn.vertex_properties[prop_name] = prop # Set the PropertyMap

            for line in node_file:
                d = {k:v for k, v in zip(header, line.strip().split("\t"))}
                node = gt_util.find_vertex(ckn, ckn.vp["name"], d["node_ID"])
                if len(node) == 1:
                    node = node[0]
                    for key in d:
                            ckn.vp[key][node] = d[key]

        print(ckn.list_properties())
        return ckn

    def get_autocomplete_node_data(self):
        data = []
        for node in self.graph.vertices():

            elt = {'id':int(node)}
            for atr in ['name', 'short_name', 'TAIR', 'full_name', 'GMM']:
                elt[atr] = self.graph.vp[atr][node]

            synonyms = self.graph.vp['synonyms'][node]
            elt[f'synonyms'] = synonyms
            for i, s in enumerate(synonyms.split("|")):
                elt[f'synonyms_{i}'] = s
            data.append(elt)

        return {'node_data': data}

    def filter(self, limit_ranks=None, limit_tissues=None):

        u = self.graph

        if limit_ranks:
            u = gt.GraphView(u, efilt=lambda x: u.ep['rank'][x] in limit_ranks)
        # if limit_tissues:
        #     u = gt.GraphView(u, vfilt=lambda x: g.vp['tissue'][x] in limit_tissues)

        # print("CKN filtered:", u.num_vertices(), u.num_edges())

        return u

    def extract_query(self, query_nodes, limit_ranks=None, limit_tissues=None):

        filtered_view = self.filter(limit_ranks=limit_ranks, limit_tissues=limit_tissues)

        if len(query_nodes) == 1:
            result_nodes = self.extract_neighbourhood(filtered_view, query_nodes, k=1)
        else:
            result_nodes = self.extract_shortest_paths(filtered_view, query_nodes)

        print("Final result:", len(result_nodes), result_nodes)
        # [print("node:", filtered_view.vp['name'][node]) for node in result_nodes]

        result = gt.GraphView(filtered_view, vfilt=lambda x: x in result_nodes)
        # [print("graph", result.vp['name'][node]) for node in result.vertices()]
        return result

    def extract_neighbourhood(self, graph, nodes, k=1):

        # [print(graph.vp['name'][node]) for node in nodes]

        nodes = [node for node in nodes if node in graph.vertices()]

        all_neighbours = set(nodes)
        fromnodes = nodes
        for i in range(k):
            neighbours = set(itertools.chain.from_iterable([graph.get_all_neighbors(node) for node in fromnodes]))  # - set(fromnodes)
            if not neighbours:
                break
            all_neighbours.update(neighbours)
            fromnodes = neighbours

        # [print(graph.vp['name'][node]) for node in all_neighbours]
        return all_neighbours

    def extract_shortest_paths(self, graph, nodes):

        paths_nodes = []
        for fr, to in itertools.combinations(nodes, 2):
            print("here")
            paths = [p for p in gt_topology.all_shortest_paths(graph, source=fr, target=to)]
            # print(paths)
            paths_nodes.extend([item for path in paths for item in path])

        # add back also nodes with no paths
        # this also covers the case with no paths at all
        paths_nodes = set(paths_nodes).union(nodes)

        return paths_nodes
        # g.subgraph(paths_nodes).copy()


    def expand_nodes(self, nodes, all_shown_nodes, limit_ranks=None, limit_tissues=None):
        if len(nodes) > 1:
            print('Error : expand not implemented for more than one node')
        node = nodes[0]

        filtered_view = self.filter(limit_ranks=limit_ranks, limit_tissues=limit_tissues)

        all_neighbours = self.extract_neighbourhood(filtered_view, nodes, k=1)

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


        result = gt.GraphView(filtered_view, vfilt=lambda x: x in all_neighbours)

        return result





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
    '0': 5,
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

def graph2json(graph, query_nodes=None, node_limit=None, edge_limit=None):
    '''
    Limit nodes -- query_nodes + top nodes ordered by page rank

    Limit edges -- ??

    '''
    print("graph2json:", graph.num_vertices(), graph.num_edges())
    [print(graph.vp['name'][node]) for node in graph.vertices()]


    if not query_nodes:
        query_nodes = []


    # make graph smaller (for rendering)
    num_vertices = graph.num_vertices()
    if node_limit and (num_vertices > node_limit):
        pr = pagerank(graph)
        pr_array = pr.get_array()
        top_n_index = pr_array.argpartition(-(node_limit+1))[-(node_limit+1)]
        graph = gt.GraphView(graph, vfilt=lambda x: (pr[x] > pr_array[top_n_index]) or (x in query_nodes))

    num_vertices = graph.num_vertices()
    num_edges = graph.num_edges()

    print("Restricted:", num_vertices, num_edges)
    # if edge_limit and (num_edges > edge_limit):
    #     # make graph smaller (for rendering)
    #     if query_nodes:
    #         keep_nodes = set(query_nodes)
    #     else:
    #         keep_nodes = set()



    groups = set()
    for node in graph.vertices():
        groups.add(graph.vp['node_type'][node])

    groups_json = {}
    for elt in groups:
        if elt in NODE_STYLE:
            groups_json[elt] = NODE_STYLE[elt]
        else:
            groups_json[elt] = NODE_STYLE['default']

    nlist = []
    for node in graph.vertices():
        nodeData = {}
        group = node_type = graph.vp['node_type'][node]

        for atr in ['short_name', 'TAIR', 'node_type', 'full_name', 'synonyms', 'GMM', 'note']:
            nodeData[atr] = graph.vp[atr][node]

        nodeData['id'] = int(node)
        nodeData['group'] = node_type
        nodeData['label'] = nodeData['short_name']

        if node in query_nodes:
            nodeData['color'] = {'background': groups_json[group]['color']['background'],
                                 'border': 'red',
                                 'highlight': {'border': 'red'},  # this does not work, bug in vis.js
                                 'hover': {'border': 'red'}}  # this does not work, bug in vis.js
            nodeData['borderWidth'] = 2

        nlist.append(nodeData)

    elist = []
    for edge  in graph.edges():
        edgeData = {}

        for atr in ['type', 'rank', 'species', 'effect', 'isDirected', 'isTFregulation', 'hyperlink']:
            edgeData[atr] = graph.ep[atr][edge]

        edgeData = {**edgeData, **edge_style(edgeData)}
        edgeData['from'] = int(edge.source())
        edgeData['to'] = int(edge.target())

        # print(fr, to)
        elist.append(edgeData)

    return {'network': {'nodes': nlist, 'edges': elist}, 'groups': groups_json}
