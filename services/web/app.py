import os
import json
import itertools
import networkx as nx

from flask import Flask, flash, g, redirect, render_template, request, session
from flask import Blueprint

import redis

from flask_cors import CORS, cross_origin

try:
    from . import utils
except ImportError:
    import utils

from flask_session import Session
sess = Session()

BASEDIR = os.path.dirname(__file__)
CKN_PATH = os.path.join(BASEDIR, 'data/AtCKN-v2-2023.06-biomine.tsv')
CKN_FILTERED_PATH = os.path.join(BASEDIR, 'data/AtCKN-v2-2023.06-filtered-biomine.tsv')
ANNOTATIONS_PATH = os.path.join(BASEDIR, 'data/AtCKN-v2-2023.06_node-annot.tsv')
# CKN_PATH = os.path.join(BASEDIR, 'data/sample.tsv')


class CKN(object):
    def __init__(self, force=False):
        self.graph = None
        self.load(force=force)

    def load(self, force=False, headers={}):
        if force or self.graph is None:

            self.graph = utils.load_CKN(CKN_PATH)#, self.edge_directions)
            utils.add_attributes(self.graph, ANNOTATIONS_PATH)

            self.graph_filtered = utils.load_CKN(CKN_FILTERED_PATH)
            utils.add_attributes(self.graph_filtered, ANNOTATIONS_PATH)

            self.node_search_data = utils.get_autocomplete_node_data(self.graph)
            print("loaded")

ckn = CKN(force=True)

print(ckn.graph.number_of_nodes(), ckn.graph.number_of_edges())


bp = Blueprint('bp', __name__,
               url_prefix='/ckn',
               static_folder='static/')

@bp.route('/get_node_data', methods=['GET', 'POST'])
def node_data():
    return ckn.node_search_data

@bp.route('/search', methods=['GET', 'POST'])
def search():
    try:
        data = request.get_json(force=False)
        query_nodes = set(data.get('nodes'))
        limit_ranks = bool(data.get('limit_ranks'))
    except Exception as e:
        return {'error': 'Invalid query data'}

    print("limit_ranks", limit_ranks)
    if limit_ranks:
        g = ckn.graph_filtered
        query_nodes = [n for n in query_nodes if n in g.nodes()]
    else:
        g = ckn.graph

    if len(query_nodes) == 0:
        return {'error': 'Invalid query data'}

    subgraph = utils.extract_shortest_paths(g, query_nodes)
    print(subgraph.number_of_nodes(), subgraph.number_of_edges())

    return json.dumps(utils.graph2json(subgraph, query_nodes=query_nodes))

#   AT1G07530
@bp.route('/expand', methods=['GET', 'POST'])
def expand():
    try:
        data = request.get_json(force=False)
        query_nodes = set(data.get('nodes'))
        all_nodes = set(data.get('all_nodes'))
        limit_ranks = bool(data.get('limit_ranks'))
    except Exception as e:
        return {'error': 'Invalid query data'}

    if limit_ranks:
        g = ckn.graph_filtered
        query_nodes = [n for n in query_nodes if n in g.nodes()]
    else:
        g = ckn.graph

    # potential edges are on the second level and may link to the existing graph
    subgraph = utils.expand_nodes(g, list(query_nodes), all_nodes)

    # # write potential edges in JSON
    # elist = []
    # for fr, to, attrs in potentialEdges:
    #     e = {**attrs, **utils.edge_style(attrs)}
    #     e['from'] = fr
    #     e['to'] = to
    #     elist.append(e)

    json_data = utils.graph2json(subgraph)
    # json_data['network']['potential_edges'] = elist

    # print(len(subgraph), len(potentialEdges))
    # print(potentialEdges)
    return json.dumps(json_data)

@bp.route('/')
@cross_origin()
def main():

    if '_user_id' in session:
        headers = {'Userid': session['_user_id']}
    else:
        headers = {}

    # refresh pss
    ckn.load(headers=headers)

    return render_template('index.html')

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

    app.register_blueprint(bp)
    return app


app = create_app()
