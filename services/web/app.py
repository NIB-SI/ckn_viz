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
ANNOTATIONS_PATH = os.path.join(BASEDIR, 'data/AtCKN-v2-2023.06_node-annot.tsv')

NODE_DRAW_LIMIT = 100
EDGE_DRAW_LIMIT = 1000

ckn = utils.CKN(CKN_PATH, ANNOTATIONS_PATH, force=True)
print(ckn.graph.num_vertices(), ckn.graph.num_edges())

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
        query_nodes = set([int(x) for x in data.get('nodes')])
        limit_ranks = data.get('limit_ranks')
        limit_tissues = data.get('limit_tissues')
    except Exception as e:
        return {'error': 'Invalid query data'}

    print("limit_ranks:", limit_ranks, "\tlimit_tissues:", limit_tissues)

    if len(query_nodes) == 0:
        return {'error': 'Invalid query data'}

    subgraph = ckn.extract_query(query_nodes, limit_ranks=limit_ranks, limit_tissues=limit_tissues)
    if subgraph.num_vertices() == 0:
        return {'error': 'No result'}

    print(subgraph.num_vertices(), subgraph.num_edges())
    json_data = utils.graph2json(subgraph, query_nodes=query_nodes, node_limit=NODE_DRAW_LIMIT, edge_limit=EDGE_DRAW_LIMIT)

    return json.dumps(json_data)

#   AT1G07530
@bp.route('/expand', methods=['GET', 'POST'])
def expand():
    try:
        data = request.get_json(force=False)
        query_nodes = set(data.get('nodes'))
        all_nodes = set(data.get('all_nodes'))
        limit_ranks = data.get('limit_ranks')
        limit_tissues = data.get('limit_tissues')
    except Exception as e:
        return {'error': 'Invalid query data'}

    # potential edges are on the second level and may link to the existing graph
    subgraph = ckn.expand_nodes(list(query_nodes), all_nodes, limit_ranks=limit_ranks, limit_tissues=limit_tissues)

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
