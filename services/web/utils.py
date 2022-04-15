import csv
import os
import pickle
# import subprocess
import itertools
import json
import re
from html.entities import name2codepoint as n2cp

import networkx as nx

# from fuzzywuzzy import fuzz, process

import requests

RE_HTML_ENTITY = re.compile(r'&(#?)([xX]?)(\w{1,8});', re.UNICODE)

SPECIES = [
    "ath",
    "osa",
    "stu",
    "sly",
    "nta",
    "ptr",
    "vvi",
]


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


def expand_nodes(g, nodes):
    if len(nodes) > 1:
        print('Error : expand not implemented for more than one node')
    node = nodes[0]
    ug = nx.Graph(g.copy())

    # find also neighbours on the second level to connect to the rest of the graph (if possible)
    all_neighbours = set(nodes)
    fromnodes = nodes
    for i in range(2):
        neighbours = set(itertools.chain.from_iterable([g.neighbors(node) for node in fromnodes]))  # - set(fromnodes)
        if not neighbours:
            break
        all_neighbours.update(neighbours)
        fromnodes = neighbours
    potentialEdges = g.subgraph(all_neighbours).edges(data=True)
    return g.subgraph([node] + list(ug.neighbors(node))), potentialEdges




# def visualize_graphviz(g, path, output='pdf'):
#     dotfile = path + '.dot'
#     nx.drawing.nx_pydot.write_dot(g, dotfile)
#     subprocess.call(['dot', '-T{}'.format(output), dotfile, '-o', '{}.{}'.format(path, output)])  # , cwd=outdir)

def parseJSON(url=None, path=None, headers={}):
    '''Try url first, if failed, fall back to path'''

    nodes = []
    edges = []
    g = nx.DiGraph()

    if not (path or url):
        raise Exception("ERROR: at least path or url")

    success = False
    if url:
        try:
            response = requests.get(url, headers=headers)
            if response.ok:
                success = True
                for line in response.text.split("\n"):
                    line = json.loads(line)
                    if line['type'] == 'node':
                        nodes.append(line)
                    elif line['type'] == 'relationship':
                        edges.append(line)
                    else:
                        raise ValueError('Unknown line')
                    # print(line)
        except requests.exceptions.ConnectionError as e:
            print(f"Could not fetch file from {url}. Using a local copy.")
            # raise e

    if not success:
        with open(path) as fp:
            for line in fp:
                # current_app.logger.info(line)
                line = json.loads(line)
                if line['type'] == 'node':
                    nodes.append(line)
                elif line['type'] == 'relationship':
                    edges.append(line)
                else:
                    raise ValueError('Unknown line')
                # print(line)

    for node in nodes:
        # g.add_node(node['id'], name=node['properties']['name'], labels=node['labels'])
        node['properties']['name'] = decode_htmlentities(node['properties']['name'])
        node['properties']['description'] = decode_htmlentities(node['properties'].get('description', ''))
        node['properties']['evidence_sentence'] = decode_htmlentities(node['properties'].get('evidence_sentence', ''))
        g.add_node(node['id'], labels=node['labels'], **node['properties'])
    for edge in edges:
        # if edge['start']['id'] not in g.nodes:
        #     print('UNKNOWN START NODE: ', edge['start']['id'])
        # if edge['end']['id'] not in g.nodes:
        #     print('UNKNOWN END NODE: ', edge['end']['id'])
        props = edge['properties'] if 'properties' in edge else {}
        g.add_edge(edge['start']['id'], edge['end']['id'], label=edge['label'], **props)

    return nodes, edges, g




def fetch_group(labels):
    index_labels = ['Family', 'Plant', 'Foreign', 'Node', 'FunctionalCluster']
    for x in labels:
        if not (x in index_labels):
            return x

    # just in case
    return labels[0]


################################ NEW


def load_CKN(fname):
    ckn = nx.MultiGraph()
    with open(fname) as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        for i, row in enumerate(reader):
            if i > 0:
                ckn.add_edge(row[0], row[1], type=row[2], rank=row[3], species=row[4], directed=True if row[5].upper()=='Y' else False)
    return ckn
    #
    # basename = os.path.splitext(fname)[0]
    # pickled_fname = f'{basename}.nxgraph.pickle'
    # if not os.path.exists(pickled_fname):
    #     ckn = nx.MultiGraph()
    #     with open(fname) as csvfile:
    #         # reader = csv.reader(csvfile, delimiter='\t')
    #         # for row in reader:
    #         #     ckn.add_edge(row[0], row[1], type=row[2], rank=row[3], species=row[4], directed=True if row[5].upper()=='Y' else False)
    #
    #         dialect = csv.Sniffer().sniff(csvfile.read(2048))
    #         csvfile.seek(0)
    #         reader = csv.DictReader(csvfile, dialect=dialect)
    #         for row in reader:
    #             ckn.add_edge(row['intL'], row['intR'], type=row['intType'], rank=row['intRank'], species='ath', directed=True if row['isDirected'].upper()=='Y' else False)
    #     with open(pickled_fname, 'wb') as fp:
    #         pickle.dump(ckn, fp)
    # else:
    #     with open(pickled_fname, 'rb') as fp:
    #         ckn = pickle.load(fp)
    # return ckn


def get_autocomplete_node_data(g):
    data = []
    for nodeid, attrs in g.nodes(data=True):
        elt = {'id': nodeid, 'name': nodeid}
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
    groups_json = {'group0': {'shape': 'box',
                              'color': {'background': 'white'}}}
    nlist = []
    for nodeid, attrs in g.nodes(data=True):
        nodeData = {'id': nodeid,
                    'label': nodeid,
                    'group': 'group0'}
        if nodeid in query_nodes:
            nodeData['color'] = {'border': 'red',
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
                      'directed': attrs['directed']
                      })
    return {'network': {'nodes': nlist, 'edges': elist}, 'groups': groups_json}


if __name__ == '__main__':
    ns, es, g = parseJSON('data/PSS-latest.json')
    j = graph2json(ns, es, g)
    nd = get_autocomplete_node_data(g)
