var netviz = {
    nodes: undefined,
    edges: undefined,
    network: undefined,
    isFrozen: false,
    newNodes: undefined,
    newEdges: undefined
};


// var network = null;
var node_search_data = null;
var node_search_data_dict = null;
var select = null;

format.extend (String.prototype, {});

$(window).resize(function() {
    scale();
});

function enableSpinner() {
    // disable button
    $('#searchButton').prop("disabled", true);
    // add spinner to button
    $('#searchButton').html(`<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> searching...`);
}

function disableSpinner() {
    // enable button
    $('#searchButton').prop("disabled", false);
    // add back text only
    $('#searchButton').html('search');
}

function enableSuggestSpinner() {
    $('#searchSelectWrapper').html(`<span class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></span> Loading node data...`);
}

function disableSuggestSpinner() {
    $('#searchSelectWrapper').html(`<label for="queryInput" class="form-label">Search CKN</label>`);
}


$( document ).ready(function() {
    $.ajax({
      url: "/get_node_data",
      async: false,
      dataType: 'json',
      type: "POST",
      contentType: 'application/json; charset=utf-8',
      processData: false,
      beforeSend: function(jqXHR, settings) {
          enableSuggestSpinner();
      },
      success: function( data, textStatus, jQxhr ){
          // console.log(data.node_data);
          node_search_data = data.node_data;
          node_search_data_dict = Object.assign({}, ...node_search_data.map((x) => ({[x.id]: x})));
          disableSuggestSpinner();
      },
      error: function( jqXhr, textStatus, errorThrown ){
          alert('Server error while loading node data.');
      }
    });

    $('#add2selected').click(function(){
        var selected_values = select[0].selectize.getValue();
        // var maxlen = 100;
        // console.log(selected_values);
        selected_values.forEach(function (item, index) {
            let node = node_search_data_dict[item];
            let nodeName = v.truncate(node.name, 25);
            let node_id = '<small style="font-size:0px;"><strong>id: </strong><div class="node_id">{}</div></small>'.format(node.id);

            let list_item = '<a href="#" class="list-group-item list-group-item-action">\
                <div class="d-flex w-100 justify-content-between">\
                <h5 class="mb-1">{}</h5>\
                <button type="button" class="btn btn-link btn-sm float-end"><i class="bi-x-circle" style="color: red;"></i></button>\
                </div>\
                {}\
                </a>'.format(nodeName, node_id);

         $('#queryList').append(list_item);
         // scroll to bottom
         let element = $('#queryList')[0];
         element.scrollTop = element.scrollHeight;

         select[0].selectize.clear();
         $(".list-group-item button").click(function(){
           $(this).parent().parent().remove();
         })

        });
    });

    select = $('#queryInput').selectize({
        options: node_search_data,
        maxItems: null,
        closeAfterSelect: true,
        valueField: "id",
        labelField: "name",
        sortField: "name",
        searchField: ['name'],
        highlight: false,
        render: {
        //   item: function (item, escape) {
        //     return "<div>" + (item.name ? '<span class="name">' + escape(item.name) + "</span>" : "") + (item.description ? '<span class="email">' + escape(item.email) + "</span>" : "") + "</div>";
        // },
          option: function (item, escape) {
            let maxlen = 50;
            let name = '<span class="name"> {} </span>'.format(v.truncate(escape(item.id), maxlen));
            // let description = item.description.length>0 ? '<span class="caption"> <strong>description:</strong> {} </span>'.format(v.truncate(escape(item.description), maxlen - 'description:'.length)) : "";
            // let synonyms = item.synonyms.length>0 ? '<span class="caption"> <strong>synonyms:</strong> {} </span>'.format(v.truncate(escape(item.synonyms), maxlen - 'synonyms:'.length)) : "";
            // let evidence_sentence = item.evidence_sentence.length>0 ? '<span class="caption"> <strong>add. info:</strong> {} </span>'.format(v.truncate(escape(item.evidence_sentence), maxlen - 'add. info:'.length)) : "";

            return '<div>\
            {}\
            </div>'.format(name);
          },
        }
    });



    $('#searchButton').click(function(){
        if($('.node_id').toArray().length==0)
            return;

        enableSpinner();

        $.ajax({
          url: "/search",
          dataType: 'json',
          type: "POST",
          contentType: 'application/json; charset=utf-8',
          processData: false,
          data: JSON.stringify({'nodes': $('.node_id').toArray().map(x => $(x).text())}),
          success: function( data, textStatus, jQxhr ){
              // console.log(data);
              netviz.isFrozen = false;
              drawNetwork(data);
              // disableSpinner();
              // console.log(data.network);
              // $('#response pre').html( JSON.stringify( data ) );
          },
          error: function( jqXhr, textStatus, errorThrown ){
              disableSpinner();
              alert('Server error while loading the network.');
          }
        });
    });


    $("#showTooltipsCbox").change(function() {
        if (netviz.network) {
            if (this.checked) {
                netviz.network.setOptions({interaction:{tooltipDelay:200}});
            }
            else {
                netviz.network.setOptions({interaction:{tooltipDelay:3600000}});
            }
        }
    });
    $("#showTooltipsCbox").prop("checked", false);

    scale();
    initContextMenus();
});


function drawNetwork(graphdata){
     netviz.nodes = new vis.DataSet(graphdata.network.nodes);
     netviz.edges = new vis.DataSet(graphdata.network.edges);

     // create a network
     var container = document.getElementById('networkView');

     // provide the data in the vis format
     var data = {
         nodes: netviz.nodes,
         edges: netviz.edges
     };

     // console.log(data);
     var options = {groups: graphdata.groups,
                    interaction: {hover: true,
                                  navigationButtons: true,
                                  multiselect: true,
                                  tooltipDelay: $("#showTooltipsCbox").prop("checked") ? 200 : 3600000,  // effectively disabled by very long delay if unchecked
                                },
                    edges: {
                        arrows: 'to',
                        smooth: {
                            enabled: true,
                            // type: 'continuous',
                            type: 'dynamic',
                            forceDirection: 'none'
                        },
                        font: {
                            size: 9,
                            face: 'sans',
                            align: 'top', //'middle'
                            color: '#808080'
                        },
                        chosen: {
                            label: hover_edge_label
                        },
                        color: {color: 'dimgrey', hover: 'blue'},
                        hoverWidth: 0.6
                        },
                    nodes: {
                        shape: 'box',
                        color: '#9BDBFF',
                        widthConstraint: { maximum: 100},
                        font: {
                            multi: 'html'
                        },
                        chosen: {
                            node: hover_node,
                            label: hover_node_label
                        }
                    },
                    physics: {
                        enabled: true,
                        solver: 'barnesHut',

                        // barnesHut: {
                        //     gravitationalConstant: -5000,
                        //     centralGravity: 0.5,
                        //     springLength: 150,
                        //     springConstant: 0.16,
                        //     damping: 0.5 //  netviz.nodes.length > 100 ? 0.09 : 0.25
                        // },
                        barnesHut: {
                            gravitationalConstant: -18000,
                            centralGravity: 0.01,
                            springLength: 200,
                            springConstant: 0.16,
                            damping:  netviz.nodes.length > 100 ? 0.5 : 0.2,
                        },
                        repulsion: {
                            centralGravity: 0,
                            springLength: 150,
                            springConstant: 0.05,
                            nodeDistance: 170,
                            damping: 0.1
                        },
                        stabilization: {
                             enabled: true,
                             iterations: netviz.nodes.length > 100 ? 50: 100,
                             fit: true
                             // updateInterval: 5,
                         },
                    },
                    configure: {
                        enabled: false
                    },
                    layout :{
                        improvedLayout: true
                    }
    };
    postprocess_edges(data.edges);
    postprocess_nodes(data.nodes);
    netviz.network = new vis.Network(container, data, options);
    netviz.network.on('dragStart', onDragStart);
    netviz.network.on('dragEnd', onDragEnd);

    netviz.network.on("stabilizationIterationsDone", function (params) {
        disableSpinner();
   });
}


function hover_edge_label(values, id, selected, hovering) {
  values.mod = 'normal';
}

function hover_node_label(values, id, selected, hovering) {
  values.mod = 'normal';
}

function hover_node(values, id, selected, hovering) {
  values.borderWidth = 2;
  values.borderColor = 'blue'
  // values.color = 'blue'
}

function postprocess_edge(item) {
    let maxlen = 100;
    let header = '<table class="table table-striped table-bordered tooltip_table">\
                  <tbody>';
    let footer = '</tbody>\
                  </table>';
    let data = [['Type', item.type],
                ['Rank', item.rank],
                ['Species', item.species],
                ['Directed', item.directed ? 'yes': 'no']];

    let table = '';
    data.forEach(function (item, index) {
        if (item[1] !=null && item[1].length>0) {
            let row = '<tr>\
                            <td><strong>{}</strong></td>\
                            <td class="text-wrap">{}</td>\
                       </tr>'.format(item[0], item[1]);
            table += row;
        }
    });
    table = header + table + footer;
    item.title = htmlTitle(table);
    return item;
}

function postprocess_edges(edges) {
    edges.forEach((item, i) => {
        edges[i] = postprocess_edge(item);
    });
}

function postprocess_node(item) {
    let maxlen = 100;
    let header = '<table class="table table-striped table-bordered tooltip_table">\
                  <tbody>';
    let footer = '</tbody>\
                  </table>';
    let data = [['Name', item.label],
                ['Group', item.group]];

    let table = '';
    data.forEach(function (item, index) {
        if (item[1] !=null && item[1].length>0) {   //if there is no group, ignore
            let row = '<tr>\
                            <td><strong>{}</strong></td>\
                            <td class="text-wrap">{}</td>\
                       </tr>'.format(item[0], item[1]);
            table += row;
        }
    });
    table = header + table + footer;
    item.title = htmlTitle(table);
    return item;
}

function postprocess_nodes(nodes) {
    nodes.forEach((item, i) => {
        // console.log('postproceesing ' + item.label);
        nodes[i] = postprocess_node(item);
    });
}

function htmlTitle(html) {
  const container = document.createElement("div");
  container.classList.add('node_tooltip')
  container.innerHTML = html;
  return container;
}

function scale() {
    $('#networkView').height(verge.viewportH()-40);
    $('#networkView').width($('#networkViewContainer').width());
}

function freezeNodes(state){
    // netviz.network.stopSimulation();
    netviz.network.setOptions( { physics: !state } );
    // // netviz.nodes.forEach(function(node, id){
    // //     netviz.nodes.updateOnly({id: id, fixed: state});
    // // });
    // netviz.network.setOptions( { physics: state } );

    // netviz.network.startSimulation();
}

function onDragStart(obj) {
    if (obj.hasOwnProperty('nodes') && obj.nodes.length==1) {
        var nid = obj.nodes[0];
        netviz.nodes.update({id: nid, fixed: false});
    }

}

function onDragEnd(obj) {
    if (netviz.isFrozen==false)
        return
    var nid = obj.nodes;
    if (obj.hasOwnProperty('nodes') && obj.nodes.length==1) {
        var nid = obj.nodes[0];
        netviz.nodes.update({id: nid, fixed: true});
    }
}

function formatNodeInfoVex(nid) {
    return netviz.nodes.get(nid).title;
}

function formatEdgeInfoVex(nid) {
    return netviz.edges.get(nid).title;
}

function edge_present(edges, newEdge) {
    var is_present = false;
    var BreakException = {};

    try {
        edges.forEach((oldEdge, i) => {
            if (newEdge.from == oldEdge.from &&
                newEdge.to == oldEdge.to &&
                newEdge.label == oldEdge.label) {
                    is_present = true;
                    throw BreakException; // break is not available in forEach
                }
        })
    } catch (e) {
        if (e !== BreakException) throw e;
    }
    return is_present;
}

function expandNode(nid) {
    $.ajax({
      url: "/expand",
      async: false,
      dataType: 'json',
      type: "POST",
      contentType: 'application/json; charset=utf-8',
      processData: false,
      data: JSON.stringify({'nodes': [nid], 'all_nodes': netviz.nodes.getIds()}),
      success: function( data, textStatus, jQxhr ){
          if (data.error) {
              vex.dialog.alert('Server error when expanding the node. Please report the incident.')
          }
          else {
              let newCounter = 0
              data.network.nodes.forEach((item, i) => {
                  if (!netviz.nodes.get(item.id)) {
                      netviz.nodes.add(postprocess_node(item));
                      newCounter += 1;
                  }
                  else {
                      // console.log('Already present ' + item.id + item.label)
                  }
              })

              data.network.edges.forEach((newEdge, i) => {
                  if(!edge_present(netviz.edges, newEdge)) {
                      netviz.edges.add(newEdge);
                      newCounter += 1;
                  }
              })

              data.network.potential_edges.forEach((edge, i) => {
                  if(!edge_present(netviz.edges, edge)) {
                      netviz.edges.add(edge);
                      newCounter += 1;
                  }
              })

              if (newCounter==0) {
                  vex.dialog.alert('No nodes or edges can be added.');
              }
          }
      },
      error: function( jqXhr, textStatus, errorThrown ){
          alert('Server error while loading node data.');
      }
    });

}


function initContextMenus() {
    var canvasMenu = {
        "stop": {name: "Stop simulation"},
        "start" : {name: "Start simulation"}
    };
    var canvasMenu = {
        "freeze": {name: "Freeze positions"},
        // "release" : {name: "Start simulation"}
    };
    var nodeMenuFix = {
        "delete": {name: "Delete"},
        "expand": {name: "Expand"},
        "fix": {name: "Fix position"},
        "info": {name: "Info"}
    };
    var nodeMenuRelease = {
        "delete": {name: "Delete"},
        "expand": {name: "Expand"},
        "release": {name: "Release position"},
        "info": {name: "Info"}
    };
    var edgeMenu = {
        "delete": {name: "Delete"},
        "info": {name: "Info"}
    };

    $.contextMenu({
            selector: 'canvas',
            build: function($trigger, e) {
                // this callback is executed every time the menu is to be shown
                // its results are destroyed every time the menu is hidden
                // e is the original contextmenu event, containing e.pageX and e.pageY (amongst other data)

                var hoveredEdge = undefined;
                var hoveredNode = undefined;
                if (!$.isEmptyObject(netviz.network.selectionHandler.hoverObj.nodes)) {
                    hoveredNode = netviz.network.selectionHandler.hoverObj.nodes[Object.keys(netviz.network.selectionHandler.hoverObj.nodes)[0]];
                }
                else {
                    hoveredNode = undefined;
                }
                if (!$.isEmptyObject(netviz.network.selectionHandler.hoverObj.edges)) {
                    hoveredEdge = netviz.network.selectionHandler.hoverObj.edges[Object.keys(netviz.network.selectionHandler.hoverObj.edges)[0]];
                }
                else {
                    hoveredEdge = undefined;
                }

                // ignore auto-highlighted edge(s) on node hover
                if (hoveredNode != undefined && hoveredEdge != undefined)
                    hoveredEdge = undefined;

                if (hoveredNode != undefined && hoveredEdge == undefined) {
                    return {
                        callback: function(key, options) {
                            if (key == "delete") {
                                netviz.nodes.remove(hoveredNode);
                            }
                            else if (key == "expand") {
                                // expandNode(hoveredNode.id);
                                vex.dialog.alert("Not yet implemented.");
                            }
                            else if (key == "fix") {
                                netviz.nodes.update({id: hoveredNode.id, fixed: true});
                            }
                            else if (key == "release") {
                                netviz.nodes.update({id: hoveredNode.id, fixed: false});
                            }
                            else if (key == "info") {
                                vex.dialog.alert({unsafeMessage: formatNodeInfoVex(hoveredNode.id)});
                            }
                        },
                        items: netviz.nodes.get(hoveredNode.id).fixed ? nodeMenuRelease : nodeMenuFix
                    };
                }
                else if (hoveredNode == undefined && hoveredEdge != undefined) {
                    return {
                        callback: function(key, options) {
                            if (key == "delete") {
                                netviz.edges.remove(hoveredEdge);
                            }
                            else if (key == "info") {
                                vex.dialog.alert({unsafeMessage: formatEdgeInfoVex(hoveredEdge.id)});
                            }
                        },
                        items: edgeMenu
                    };
                }
                else {
                    if (netviz.isFrozen) {
                        canvasMenu.freeze.name = "Release positions";
                        return {
                            callback: function(key, options) {
                                if (key == "freeze") {
                                    netviz.isFrozen = false;
                                    freezeNodes(netviz.isFrozen);
                                }
                            },
                            items: canvasMenu
                        };
                    }
                    else {
                        canvasMenu.freeze.name = "Freeze positions";
                        return {
                            callback: function(key, options) {
                                if (key == "freeze") {
                                    netviz.isFrozen = true;
                                    freezeNodes(netviz.isFrozen);
                                }
                            },
                            items: canvasMenu
                        };
                    }
                }
            }
        });

}
