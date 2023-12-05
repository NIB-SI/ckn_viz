import os
import json
import itertools
import networkx as nx

from flask import Flask, flash, g, redirect, render_template, request, session

import redis

from flask_cors import CORS, cross_origin

try:
    from . import utils
except ImportError:
    import utils

from flask_session import Session
sess = Session()

BASEDIR = os.path.dirname(__file__)
CKN_PATH = os.path.join(BASEDIR, 'data/TMP_AtCKN_2022-01-26_UC.tsv')
DIRECTIONS_PATH = os.path.join(BASEDIR, 'data/arrows-and-edges.csv')
ANNOTATIONS_PATH = os.path.join(BASEDIR, 'data/TMP_network-anno_2022-06-16_for-AtCKN_2022-01-26.tsv')
# CKN_PATH = os.path.join(BASEDIR, 'data/sample.tsv')


class CKN(object):
    def __init__(self, force=False):
        self.graph = None
        self.load(force=force)

    def load(self, force=False, headers={}):
        if force or self.graph is None:
            self.edge_directions = utils.load_edge_directions(DIRECTIONS_PATH)
            self.graph = utils.load_CKN(CKN_PATH, self.edge_directions)
            utils.add_attributes(self.graph, ANNOTATIONS_PATH)
            self.node_search_data = utils.get_autocomplete_node_data(self.graph)


ckn = CKN(force=True)


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    rport = 6379
    rs = redis.Redis(host='redis', port=rport)
    try:
        rs.ping()
    except redis.exceptions.ConnectionError:
        print(f'Warning: Redis is not running on port {rport}. Not using this setting.')
    else:
        app.config.from_mapping(
            # Flask Session settings
            SESSION_TYPE='redis',
            SESSION_REDIS=redis.Redis(host='redis', port=rport)
        )
    sess.init_app(app)

    @app.route('/get_node_data', methods=['GET', 'POST'])
    def node_data():
        return ckn.node_search_data

    @app.route('/search', methods=['GET', 'POST'])
    def search():
        try:
            data = request.get_json(force=False)
            query_nodes = set(data.get('nodes'))
        except Exception as e:
            return {'error': 'Invalid query data'}

        subgraph = utils.extract_shortest_paths(ckn.graph, query_nodes)
        # # not all edges are shown, according to Ziva's table
        # utils.filter_edges_for_display(subgraph)
        # # WARNING: if the extracted graph containes isolates they are removed here along with newly
        # #          introduced isolates produced by removing some edges.
        # subgraph.remove_nodes_from(list(nx.isolates(subgraph)))
        return utils.graph2json(subgraph, query_nodes=query_nodes)

    @app.route('/expand', methods=['GET', 'POST'])
    def expand():
        try:
            data = request.get_json(force=False)
            query_nodes = set(data.get('nodes'))
            all_nodes = set(data.get('all_nodes'))
        except Exception as e:
            return {'error': 'Invalid query data'}

        # potential edges are on the second level and may link to the existing graph
        subgraph, potentialEdges = utils.expand_nodes(ckn.graph, list(query_nodes), all_nodes)

        # write potential edges in JSON
        elist = []
        for fr, to, attrs in potentialEdges:
            elist.append({'from': fr,
                          'to': to,
                          'label': attrs['type'],
                          'type': attrs['type'],
                          'rank': attrs['rank'],
                          'species': attrs['species'],
                          'directed': attrs['directed']
                          })

        json_data = utils.graph2json(subgraph)
        json_data['network']['potential_edges'] = elist

        print(len(subgraph), len(potentialEdges))
        print(potentialEdges)
        return json_data

    @app.route('/')
    @cross_origin()
    def main():

        headers = {'Userid': session['_user_id']} if '_user_id' in session else {}
        # refresh pss
        ckn.load(headers=headers)

        return render_template('index.html')

    return app


app = create_app()
