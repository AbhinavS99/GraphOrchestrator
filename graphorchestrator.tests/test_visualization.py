import matplotlib
from graphorchestrator.GraphExecutorStatic import (
    GraphBuilder,
    ProcessingNode,
    AggregatorNode,
    RepresentationalGraph,
    GraphVisualizer,
    routing_function,
    passThrough,
    selectRandomState
)
matplotlib.use("Agg")

def testv_01_conversion_test():
    @routing_function
    def dummy_router(state):
        return "agg"
    builder = GraphBuilder()
    proc_node = ProcessingNode("proc", passThrough)
    agg_node = AggregatorNode("agg", selectRandomState)
    builder.add_node(proc_node)
    builder.add_aggregator(agg_node)
    builder.add_concrete_edge("start", "proc")
    builder.add_conditional_edge("proc", ["agg", "end"], dummy_router)
    graph = builder.build_graph()
    rep_graph = RepresentationalGraph.from_graph(graph)
    assert "start" in rep_graph.nodes
    assert "proc" in  rep_graph.nodes
    assert "agg" in  rep_graph.nodes
    assert "end" in rep_graph.nodes
    assert len(rep_graph.edges) ==  1+2
    concrete_edge = rep_graph.edges[0]
    assert concrete_edge.edge_type.name == "CONCRETE"
    for edge in rep_graph.edges[1:]:
        assert edge.edge_type.name == "CONDITIONAL"
    visualizer = GraphVisualizer(rep_graph)
    visualizer.visualize(show=False)