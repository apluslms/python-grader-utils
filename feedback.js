;
/**
 * Using Cytoscape.js, draw tree defined by nodeArray and edgeArray into
 * the JQuery object container. Nodes will be placed in level order,
 * starting from the 0 index of nodeArray.
 * @param {array<object>} nodeArray - in format: {data: {id: <String>}}
 * @param {array<object>} edgeArray - in format: {data: {source: <String>,
 *                                                       target: <String>}}
 * @param {jquery object} container
 */
function drawTreeToContainer(nodeArray, edgeArray, container) {

  var cy = cytoscape({
    container: container,

    // Disable movable nodes
    autoungrabify: true,
    autounselectify: true,
    // Cap zooming so you can't lose the graph
    minZoom: 0.5,
    maxZoom: 2,

    // Level-order
    layout: {
      name: 'dagre'
    },

    style: [
      {
        selector: 'node',
        style: {
          'content': 'data(id)',
          'text-opacity': 0.8,
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-wrap': 'wrap',
          'text-outline-color': '#eef',
          'text-outline-width': 2,
          'color': '#0F1E69',
          'background-color': '#11479e'
        },
      },

      {
        selector: 'edge',
        style: {
          'width': 3,
          'target-arrow-shape': 'none',
          // TODO: color as parameter
          'line-color': '#9dbaea',
          'target-arrow-color': '#9dbaea',
          'curve-style': 'haystack'
        }
      }
    ],

    // Given as parameter
    elements: {
      nodes: nodeArray,
      edges: edgeArray
    },
  });

  // Check if tree drawing succeeded,
  // hide the default error message and enlargen the well containing the tree.
  // Also show short usage info (panning and zooming).
  if (cy) {
    container.siblings("p.error-msg").hide();
    // TODO: this could be approximated from the height of the tree,
    // which could be precalculated within the JSON data
    container.height(600);
    container.siblings("p.info").show();
    // Container size has changed, redraw the tree
    cy.resize();
    cy.fit();
  }

}


/**
 * Parses the treeJSON object into the format expected by Cytoscape.js and
 * calls drawTreeToContainer.
 * @param {object} treeJSON
 * @param {jquery object} targetContainer
 */
function parseTreeData(treeJSON, targetContainer) {

  var nodes = [];
  var edges = [];

  // Fill nodes and edges with js objects in Cytoscape.js format
  $.each(treeJSON, function(index, node) {
    nodes.push({data: {id: node.label}});
    $.each(node.children, function(index, targetNodeLabel) {
        edges.push({data: {source: node.label, target: targetNodeLabel}});
    });
  });

  drawTreeToContainer(nodes, edges, targetContainer);
}


/**
 * For each DOM element which matches resultPanelSelector and contains
 * the DOM element which matches JSONDataSelector, parse contents of the
 * latter element as JSON and call drawTree to draw the tree defined by
 * the JSON data into the DOM element matching targetContainerSelector,
 * inside the element which matched resultPanelSelector.
 * @param {string} resultPanelSelector
 * @param {string} JSONDataSelector
 * @param {string} targetContainerSelector
 */
function findAndDrawAllJSON(
      resultPanelSelector,
      JSONDataSelector,
      targetContainerSelector) {

  $.each($(resultPanelSelector), function(index, dataContainer) {

    var stringJSON = $(dataContainer).find(JSONDataSelector).html();
    if (stringJSON === undefined) {
      // No JSON here, skip to next
      return true;
    }

    var treeData = JSON.parse(stringJSON);

    if (treeData) {
      var targetContainer = $(dataContainer).find(targetContainerSelector);
      parseTreeData(treeData, targetContainer);
    }
  });
}


function loadError (oError) {
  throw new URIError("The script " + oError.target.src + " is not accessible.");
}


function importScript (sSrc, fOnload) {
  var oScript = document.createElement("script");
  oScript.type = "text\/javascript";
  oScript.onerror = loadError;
  if (fOnload) { oScript.onload = fOnload; }
  $("head").append(oScript);
  oScript.src = sSrc;
}


function importAllPathsAndRun(importPaths, containerSelectors) {
  importScript(importPaths[0], function() {
    importScript(importPaths[1], function() {
      importScript(importPaths[2], function() {

        // run everything if imports succeeded
        if (cytoscape !== undefined && dagre !== undefined) {
          findAndDrawAllJSON(
            containerSelectors.feedbackContainer,
            containerSelectors.treeDataJSON,
            containerSelectors.canvasContainer
          );
        }
      });
    });
  });
}


// If the rendered HTML contains additional data requiring rendering,
// draw all data, else do nothing
function main() {
  var treeSelectors = {
    feedbackContainer: ".feedback-failed",
    treeDataJSON: "script[data-json-tree]",
    canvasContainer: ".tree-graph-container .canvas-container"
  }

  if ($(treeSelectors.treeDataJSON).length > 0) {
    var importPaths = [
      'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/2.7.6/cytoscape.min.js',
      'https://cdn.rawgit.com/cpettitt/dagre/v0.7.4/dist/dagre.min.js',
      'https://cdn.rawgit.com/cytoscape/cytoscape.js-dagre/1.1.2/cytoscape-dagre.js'
    ]
    importAllPathsAndRun(importPaths, treeSelectors);
  }

  var plottingSelectors = {
    plotDataJSON: "script[data-json-benchmark]",
    plotContainer: ".plot-container"
  }

  if ($(plottingSelectors.plotDataJSON).length > 0) {
    var importPaths = [
        "https://d3js.org/d3.v4.min.js"
    ]
    // TODO draw tree json with d3js
  }
}

