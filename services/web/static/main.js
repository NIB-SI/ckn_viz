// prevents dialog closing immediately when page navigates
vex.defaultOptions.closeAllOnPopState = false;

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

format.extend(String.prototype, {});

$(window)
  .resize(function () {
    scale();
  });

function enableSpinner() {
  console.log("enableSpinner")
  var spinnerEl = document.querySelector('#spinner')
  var spinner = bootstrap.Modal.getOrCreateInstance(spinnerEl) // Returns a Bootstrap modal instance
  spinner.show()

}

function disableSpinner() {
  console.log("disableSpinner")
  var spinnerEl = document.querySelector('#spinner')
  var spinner = bootstrap.Modal.getOrCreateInstance(spinnerEl) // Returns a Bootstrap modal instance
  spinner.hide()
}

function enableSuggestSpinner() {
  $('#searchSelectWrapper')
    .html(`<span class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></span> Loading node data...`);
}

function disableSuggestSpinner() {
  $('#searchSelectWrapper')
    .html("");
}

function buildSelectWidget() {
  select = $('#queryInput')
    .selectize({
      options: node_search_data,
      maxItems: null,
      closeAfterSelect: true,
      valueField: "id",
      labelField: "name",
      sortField: "id",
      searchField: ['id', 'name', 'TAIR', 'full_name', 'short_name', 'synonyms', 'GMM'],
      highlight: false,
      render: {
        //   item: function (item, escape) {
        //     return "<div>" + (item.name ? '<span class="name">' + escape(item.name) + "</span>" : "") + (item.description ? '<span class="email">' + escape(item.email) + "</span>" : "") + "</div>";
        // },
        option: function (item, escape) {
          let maxlen = 50;
          let shortName = item['short_name'].length > 0 ? '<span class="name"> {} </span>'.format(v.truncate(escape(item['short_name']), maxlen - 'short name:'.length)) : "";
          let tair = item.TAIR.length > 0 ? '<span class="caption"> <strong>TAIR identifier:</strong> {} </span>'.format(item.TAIR) : "";
          let description = item.full_name.length > 0 ? '<span class="caption"> <strong>description:</strong> {} </span>'.format(v.truncate(escape(item.full_name), maxlen - 'description:'.length)) : "";
          let synonyms = item.synonyms.length > 0 ? '<span class="caption"> <strong>synonyms:</strong> {} </span>'.format(v.truncate(escape(item.synonyms), maxlen - 'synonyms:'.length)) : "";
          let gmm = item['GMM'].length > 0 ? '<span class="caption"> <strong>GMM:</strong> {} </span>'.format(v.truncate(escape(item['GMM']), maxlen - 'GMM:'.length)) : "";

          return '<div>\
            {}\
            {}\
            {}\
            {}\
            {}\
            </div>'.format(shortName, tair, description, synonyms, gmm);
        },
      }
    });
}

// Below from https://stackoverflow.com/a/78550846/4996681
function addQueryParam(key, value) {
  // Get the current URL
  let url = new URL(window.location);

  // Add or update the query parameter
  url.searchParams.append(key, value);

  // Update the URL without reloading the page
  history.pushState({}, '', url);
}

$(document)
  .ready(function () {

    $.ajax({
      url: "/ckn/get_node_data",
      // async: false,
      dataType: 'json',
      type: "POST",
      contentType: 'application/json; charset=utf-8',
      processData: false,
      beforeSend: function (jqXHR, settings) {
        enableSuggestSpinner();
      },
      success: function (data, textStatus, jQxhr) {
        node_search_data = data.node_data;
        node_search_data_dict = Object.assign({}, ...node_search_data.map((x) => ({
          [x.id]: x
        })));
        disableSuggestSpinner();
        buildSelectWidget();
        check_URLparams();
      },
      error: function (jqXhr, textStatus, errorThrown) {
        alert('Server error while loading node data.');
      }
    });

    $('#add2selected')
      .click(function () {
        var selected_values = select[0].selectize.getValue();
        var maxlen = 50;
        // console.log(selected_values);
        selected_values.forEach(function (item, index) {
          let node = node_search_data_dict[item];
          let title = node['short_name'] != '-' ? node['short_name'] : v.truncate(node.node_ID, 25);
          let tair = node['TAIR'].length > 0 ? '<small><strong>TAIR identifier: </strong>{}</small>'.format(node.TAIR, 25) : "";
          let node_id = '<div hidden class="node_id">{}</div>'.format(node.id);
          let synonyms = node.synonyms.length > 0 ? '<small><strong>Synonyms: </strong>{}</small>'.format(v.truncate(node.synonyms, maxlen)) : "";
          let description = node.full_name.length > 0 ? '<small><strong>Description: </strong>{}</small>'.format(node.full_name) : "";
          let list_item = '<a href="#" class="list-group-item list-group-item-action">\
                <div class="d-flex w-100 justify-content-between">\
                <h5 class="mb-1">{}</h5>\
                <button type="button" class="btn btn-link btn-sm float-end p-0 m-0"><i class="bi-x-circle" style="color: red;"></i></button>\
                </div>\
                {}\
                {}\
                {}\
                {}\
                </a>'.format(title, tair, synonyms, description, node_id);

          $('#queryList')
            .append(list_item);
          // scroll to bottom
          let element = $('#queryList')[0];
          element.scrollTop = element.scrollHeight;

          select[0].selectize.clear();
          $(".list-group-item button")
            .click(function () {
              $(this)
                .parent()
                .parent()
                .remove();
            })

        });
      });

    $('#searchButton')
      .click(function () {

        if ($('.node_id')
          .toArray()
          .length == 0) {
          return;
        }

        enableSpinner();

        var limit_ranks = [];
        $("input:checked[type='checkbox'][id^='limit_ranks']")
          .each(function () {
            limit_ranks.push($(this)
              .attr('value'));
          });
        // console.log(limit_ranks);

        var limit_tissues = [];
        $("input:checked[type='checkbox'][id^='limit_tissues']")
          .each(function () {
            limit_tissues.push($(this)
              .attr('value'));
          });

        var limit_nodes = $("#limit_nodes")
          .val();

        // console.log(limit_tissues);

        $.ajax({
          async: true,
          url: "/ckn/search",
          dataType: 'json',
          type: "POST",
          contentType: 'application/json; charset=utf-8',
          processData: false,
          data: JSON.stringify({
            'nodes': $('.node_id')
              .toArray()
              .map(x => $(x)
                .text()),
            'limit_ranks': limit_ranks,
            'limit_tissues': limit_tissues,
            'limit_nodes': limit_nodes
          }),
          success: function (data, textStatus, jQxhr) {
            console.log("received search result");
            netviz.isFrozen = false;
            if (data.error) {
              console.log(data.error)
              alert('Could not complete request, perhaps change the filters?');
            } else {
              drawNetwork(data);
              if (data.message) {
                alert(data.message)
              }

              // console.log(data.network);
              // $('#response pre').html( JSON.stringify( data ) );
            }
            disableSpinner();
          },
          error: function (jqXhr, textStatus, errorThrown) {
            console.log("error");
            disableSpinner();

            alert('Server error while loading the network.');
          }
        });

        // URL
        window.history.replaceState({}, '', window.location.pathname);
        $('.node_id')
          .toArray()
          .map(x => $(x)
            .text())
          .forEach((item, i) => {
            let node = node_search_data_dict[item];
            console.log(node)
            if (("TAIR" in node) && (node.TAIR !== '')) {
              console.log("identifier", node)
              addQueryParam("identifier", node.TAIR)
            }
          })
      });

    $("#showTooltipsCbox")
      .change(function () {
        if (netviz.network) {
          if (this.checked) {
            netviz.network.setOptions({ interaction: { tooltipDelay: 200 } });
          } else {
            netviz.network.setOptions({ interaction: { tooltipDelay: 3600000 } });
          }
        }
      });
    $("#showTooltipsCbox")
      .prop("checked", false);

    scale();
    initContextMenus();

    $('#saveAsDropdown a')
      .click(function () {
        if ($(this)
          .attr('href') == '#nodes') {
          export_nodes();
        } else if ($(this)
          .attr('href') == '#edges') {
          export_edges();
        } else if ($(this)
          .attr('href') == '#png') {
          export_png();
        }
      });
  });

function check_URLparams() {

  urlParams = new URLSearchParams(window.location.search);
  identifier_list = urlParams.getAll('identifier');
  console.log(identifier_list);

  if (identifier_list.length > 0) {
    for (var i = identifier_list.length - 1; i >= 0; i--) {
      id_ = identifier_list[i]

      var j = -1
      for (let x of node_search_data) {
        if (x.TAIR == id_) {
          j = x.id;
          break;
        }
      }
      if (j == -1) {
        alert(id_ + ' is not a valid identifier')
      } else {
        select[0].selectize.addItem(j);
        $('#add2selected')
          .click()
      }
    }
  }
  $('#searchButton')
    .click();
}

function drawNetwork(graphdata) {
  netviz.nodes = new vis.DataSet(graphdata.network.nodes);
  netviz.edges = new vis.DataSet(graphdata.network.edges);

  // create a network
  var container = document.getElementById('networkView');

  // provide the data in the vis format
  var data = {
    nodes: netviz.nodes,
    edges: netviz.edges
  };

  netviz_options['groups'] = graphdata.groups
  netviz_options['physics']['barnesHut']['damping'] = data.nodes.length > 100 ? 0.5 : 0.2
  netviz_options['physics']['stabilization']['iterations'] = data.nodes.length > 100 ? 50 : 100,

    postprocess_edges(data.edges);
  postprocess_nodes(data.nodes);
  netviz.network = new vis.Network(container, data, netviz_options);
  netviz.network.on('dragStart', onDragStart);
  netviz.network.on('dragEnd', onDragEnd);

  netviz.network.on("doubleClick", onDoubleClick);

  netviz.network.on("stabilizationIterationsDone", function (params) {
    disableSpinner();
  });
}

function postprocess_edge(item) {
  let maxlen = 100;
  let header = '<table class="table table-striped table-bordered tooltip_table">\
                  <tbody>';
  let footer = '</tbody>\
                  </table>';
  let data = [
    ['Type', item.type],
    ['Rank', item.rank],
    ['Species', item.species],
    ['Directed', Boolean(item.isDirected)],
    ['Effect', item.effect],
    ['TF regulation', Boolean(item.isTFregulation)],
    ['Source(s)', item.hyperlink.replaceAll("|", "<br>")]
  ];

  let table = '';
  data.forEach(function (item, index) {
    if (item[1] != null) {
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

function postprocess_node(node) {
  let maxlen = 100;
  let header = '<table class="table table-striped table-bordered tooltip_table">\
                  <tbody>';
  let footer = '</tbody>\
                  </table>';

  let data = [
    ['Short name', node.short_name],
    ['TAIR', node.TAIR.length > 0 ? '<a target="_blank" href="https://www.arabidopsis.org/servlets/TairObject?name={}&type=locus">{}</a>'.format(node.TAIR, node.TAIR) : ''],
    ['Type', node.node_type],
    ['Description', node.full_name],
    ['Synonyms', node.synonyms],
    ['GMM annotation', node.GMM],
    ['Tissue (TAIR Plant Ontology)', node.tissue],
    ['Note', node.note],
    ['KnetMiner', node.TAIR.length > 0 ? '<p><a target="_blank" href="https://knetminer.com/araknet/genepage?{}">Search for {} in KnetMiner</a></p>'.format(jQuery.param({ list: node.TAIR }), node.TAIR) : '']
  ];

  let table = '';
  data.forEach(function (pair, index) {
    if (pair[1] != null && pair[1].length > 0) {
      let row = '<tr>\
                            <td><strong>{}</strong></td>\
                            <td class="text-wrap">{}</td>\
                       </tr>'.format(pair[0], pair[1].replaceAll("|", "<br>"));
      table += row;
    }
  });
  table = header + table + footer;
  node.title = htmlTitle(table);
  return node;
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
  $('#networkView')
    .height(verge.viewportH() - 60);
  $('#networkView')
    .width($('#networkViewContainer')
      .width());
}

function freezeNodes(state) {
  // netviz.network.stopSimulation();
  netviz.network.setOptions({ physics: !state });
  // // netviz.nodes.forEach(function(node, id){
  // //     netviz.nodes.updateOnly({id: id, fixed: state});
  // // });
  // netviz.network.setOptions( { physics: state } );

  // netviz.network.startSimulation();
}

function onDragStart(obj) {
  if (obj.hasOwnProperty('nodes') && obj.nodes.length == 1) {
    var nid = obj.nodes[0];
    netviz.nodes.update({ id: nid, fixed: false });
  }

}

function onDragEnd(obj) {
  if (netviz.isFrozen == false)
    return
  var nid = obj.nodes;
  if (obj.hasOwnProperty('nodes') && obj.nodes.length == 1) {
    var nid = obj.nodes[0];
    netviz.nodes.update({ id: nid, fixed: true });
  }
}

function onDoubleClick(obj) {
  // get the id of the clicked node
  var clickedNodeId = obj.nodes[0];
  expandNode(clickedNodeId)
}

function formatNodeInfoVex(nid) {
  return netviz.nodes.get(nid)
    .title;
}

function formatEdgeInfoVex(nid) {
  return netviz.edges.get(nid)
    .title;
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

  if (!netviz.nodes.getIds()
    .includes(nid)) {
    console.log("not a node in the current network")
    return
  }

  enableSpinner()

  var limit_ranks = [];
  $("input:checked[type='checkbox'][id^='limit_ranks']")
    .each(function () {
      limit_ranks.push($(this)
        .attr('value'));
    });
  // console.log(limit_ranks);

  var limit_tissues = [];
  $("input:checked[type='checkbox'][id^='limit_tissues']")
    .each(function () {
      limit_tissues.push($(this)
        .attr('value'));
    });
  // console.log(limit_tissues);

  var limit_nodes = $("#limit_nodes")
    .val();

  $.ajax({
    async: true,
    url: "/ckn/expand",
    dataType: 'json',
    type: "POST",
    contentType: 'application/json; charset=utf-8',
    processData: false,
    data: JSON.stringify({
      'nodes': [nid],
      'all_nodes': netviz.nodes.getIds(),
      'limit_ranks': limit_ranks,
      'limit_tissues': limit_tissues,
      'limit_nodes': limit_nodes
    }),
    success: function (data, textStatus, jQxhr) {
      console.log("received expand result");
      if (data.error) {
        vex.dialog.alert('Server error when expanding the node. Please report the incident.');
        disableSpinner()
      } else {
        let newCounter = 0;
        // console.log(data)
        data.network.nodes.forEach((item, i) => {
          if (!netviz.nodes.get(item.id)) {
            netviz.nodes.add(postprocess_node(item));
            newCounter += 1;
          } else {
            // console.log('Already present ' + item.id + item.label)
          }
        })

        data.network.edges.forEach((newEdge, i) => {
          if (!edge_present(netviz.edges, newEdge)) {
            // console.log(newEdge.from, newEdge.to)
            netviz.edges.add(postprocess_edge(newEdge));
            newCounter += 1;
          }
        })

        // data.network.potential_edges.forEach((edge, i) => {
        //     if(!edge_present(netviz.edges, edge)) {
        //         netviz.edges.add(postprocess_edge(edge));
        //         newCounter += 1;
        //     }
        // })

        disableSpinner();

        if (newCounter == 0) {
          console.log(newCounter)
          vex.dialog.alert('No nodes or edges can be added.');
        }

        if (data.message) {
          alert(data.message)
        }
      }
    },
    error: function (jqXhr, textStatus, errorThrown) {
      alert('Server error while loading node data.');
      disableSpinner();
    }
  });

}

function initContextMenus() {
  var canvasMenu = {
    "stop": { name: "Stop simulation" },
    "start": { name: "Start simulation" }
  };
  var canvasMenu = {
    "freeze": { name: "Freeze positions" },
    // "release" : {name: "Start simulation"}
  };
  var nodeMenuFix = {
    "delete": { name: "Delete" },
    "expand": { name: "Expand" },
    "fix": { name: "Fix position" },
    "info": { name: "Info" }
  };
  var nodeMenuRelease = {
    "delete": { name: "Delete" },
    "expand": { name: "Expand" },
    "release": { name: "Release position" },
    "info": { name: "Info" }
  };
  var edgeMenu = {
    "delete": { name: "Delete" },
    "info": { name: "Info" }
  };

  $.contextMenu({
    selector: 'canvas',
    build: function ($trigger, e) {
      // this callback is executed every time the menu is to be shown
      // its results are destroyed every time the menu is hidden
      // e is the original contextmenu event, containing e.pageX and e.pageY (amongst other data)

      var hoveredEdge = undefined;
      var hoveredNode = undefined;
      if (!$.isEmptyObject(netviz.network.selectionHandler.hoverObj.nodes)) {
        hoveredNode = netviz.network.selectionHandler.hoverObj.nodes[Object.keys(netviz.network.selectionHandler.hoverObj.nodes)[0]];
      } else {
        hoveredNode = undefined;
      }
      if (!$.isEmptyObject(netviz.network.selectionHandler.hoverObj.edges)) {
        hoveredEdge = netviz.network.selectionHandler.hoverObj.edges[Object.keys(netviz.network.selectionHandler.hoverObj.edges)[0]];
      } else {
        hoveredEdge = undefined;
      }

      // ignore auto-highlighted edge(s) on node hover
      if (hoveredNode != undefined && hoveredEdge != undefined)
        hoveredEdge = undefined;

      if (hoveredNode != undefined && hoveredEdge == undefined) {
        return {
          callback: function (key, options) {
            if (key == "delete") {
              netviz.nodes.remove(hoveredNode);
            } else if (key == "expand") {
              expandNode(hoveredNode.id);
              // vex.dialog.alert("Not yet implemented.");
            } else if (key == "fix") {
              netviz.nodes.update({ id: hoveredNode.id, fixed: true });
            } else if (key == "release") {
              netviz.nodes.update({ id: hoveredNode.id, fixed: false });
            } else if (key == "info") {
              vex.dialog.alert({ unsafeMessage: formatNodeInfoVex(hoveredNode.id) });
            }
          },
          items: netviz.nodes.get(hoveredNode.id)
            .fixed ? nodeMenuRelease : nodeMenuFix
        };
      } else if (hoveredNode == undefined && hoveredEdge != undefined) {
        return {
          callback: function (key, options) {
            if (key == "delete") {
              netviz.edges.remove(hoveredEdge);
            } else if (key == "info") {
              vex.dialog.alert({ unsafeMessage: formatEdgeInfoVex(hoveredEdge.id) });
            }
          },
          items: edgeMenu
        };
      } else {
        if (netviz.isFrozen) {
          canvasMenu.freeze.name = "Release positions";
          return {
            callback: function (key, options) {
              if (key == "freeze") {
                netviz.isFrozen = false;
                freezeNodes(netviz.isFrozen);
              }
            },
            items: canvasMenu
          };
        } else {
          canvasMenu.freeze.name = "Freeze positions";
          return {
            callback: function (key, options) {
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

function format_cell(s) {
  s = s.toString();
  s = s.trim();
  s = s.replace('\n', '');
  if (s[0] != '"' && s.slice(-1) != '"' && s.search(',') != -1) {
    s = '"' + s + '"';
  }
  return s;
}

function export_nodes() {
  if (netviz.nodes == undefined) {
    vex.dialog.alert('No nodes to export! You need to do a search first.');
    return;
  }

  var data = [
    ['id', 'TAIR', 'type', 'short name', 'description', 'synonyms', 'GMM', 'note', 'Tissue (PO)']
  ];
  netviz.nodes.forEach(function (node, id) {
    var line = new Array;

    ['id', 'TAIR', 'node_type', 'short_name', 'full_name', 'synonyms', 'GMM', 'note', 'tissue'].forEach(function (aname) {
      let atr = node[aname];
      if (atr != undefined)
        line.push(format_cell(atr));
      else
        line.push('');
    })
    data.push(line);
  })

  var datalines = new Array;
  data.forEach(function (line_elements) {
    datalines.push(line_elements.join(','));
  })
  var csv = datalines.join('\n')

  var blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  saveAs(blob, "nodes.csv");
}

function export_edges() {
  if (netviz.edges == undefined) {
    vex.dialog.alert('No edges to export! You need to do a search first.');
    return;
  }

  var data = [
    ['from', 'to', 'isDirected', 'rank', 'type', 'effect', 'species', 'isTFregulation', 'interactionSources']
  ];
  netviz.edges.forEach(function (edge, id) {
    var line = new Array;

    ['from', 'to', 'isDirected', 'rank', 'type', 'effect', 'species', 'isTFregulation', 'interactionSources'].forEach(function (aname) {
      let atr = edge[aname];
      if (atr != undefined)
        line.push(format_cell(atr));
      else
        line.push('');
    })

    data.push(line);
  })

  var datalines = new Array;
  data.forEach(function (line_elements) {
    datalines.push(line_elements.join(','));
  })
  var csv = datalines.join('\n');

  var blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  saveAs(blob, "edges.csv");
}

function export_png() {
  if (netviz.nodes == undefined) {
    vex.dialog.alert('No image to export! You need to do a search first.');
    return;
  }

  const ctx = netviz.network.canvas.getContext()
  const dataURL = ctx.canvas.toDataURL('image/png');

  saveAs(dataURL, "network.png");

}
