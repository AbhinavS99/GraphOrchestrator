from collections import defaultdict, deque
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
from graphorchestrator.core.logger import GraphLogger
from graphorchestrator.core.log_utils import wrap_constants
from graphorchestrator.core.log_constants import LogConstants as LC

from graphorchestrator.visualization.representation import (
    RepresentationalGraph,
    RepresentationalEdgeType,
)


class GraphVisualizer:
    def __init__(self, rep_graph: RepresentationalGraph):
        self.rep_graph = rep_graph

    def _compute_levels(self):
        log = GraphLogger.get()
        levels = {}
        start_id = "start"

        if start_id not in self.rep_graph.nodes:
            log.error(
                **wrap_constants(
                    message="Start node missing in representational graph",
                    **{
                        LC.EVENT_TYPE: "visualization",
                        LC.ACTION: "compute_levels_failed",
                        LC.CUSTOM: {"missing_node": "start"},
                    }
                )
            )
            raise ValueError("No 'start' node found in the representational graph.")

        queue = deque([(start_id, 0)])
        visited = set()

        while queue:
            node_id, level = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            levels[node_id] = level
            node = self.rep_graph.nodes[node_id]
            for edge in node.outgoing_edges:
                queue.append((edge.sink.node_id, level + 1))

        return levels

    def visualize(self, show: bool = True) -> None:
        log = GraphLogger.get()

        log.info(
            **wrap_constants(
                message="Graph visualization started",
                **{
                    LC.EVENT_TYPE: "visualization",
                    LC.ACTION: "visualize_start",
                    LC.CUSTOM: {
                        "nodes": len(self.rep_graph.nodes),
                        "edges": len(self.rep_graph.edges),
                    },
                }
            )
        )

        levels = self._compute_levels()

        level_nodes = defaultdict(list)
        for node_id, level in levels.items():
            level_nodes[level].append(node_id)

        pos = {}
        for level, nodes in level_nodes.items():
            count = len(nodes)
            for i, node_id in enumerate(sorted(nodes)):
                x = i - (count - 1) / 2.0
                y = -level
                pos[node_id] = (x, y)

        fig, ax = plt.subplots(figsize=(8, 6))

        for node_id, (x, y) in pos.items():
            node = self.rep_graph.nodes[node_id]
            color = "lightcoral" if node.node_type == "aggregator" else "lightblue"
            circle = Circle((x, y), radius=0.3, color=color, ec="black", zorder=2)
            ax.add_patch(circle)
            ax.text(x, y, node_id, ha="center", va="center", zorder=3)

        for edge in self.rep_graph.edges:
            src_id = edge.source.node_id
            sink_id = edge.sink.node_id
            start_pos = pos[src_id]
            end_pos = pos[sink_id]

            if edge.edge_type == RepresentationalEdgeType.CONDITIONAL:
                color = "orange"
                connection_style = "arc3,rad=0.2"
                line_style = "dashed"
            else:
                color = "gray"
                connection_style = "arc3,rad=0.0"
                line_style = "solid"

            arrow = FancyArrowPatch(
                start_pos,
                end_pos,
                arrowstyle="-|>",
                mutation_scale=15,
                color=color,
                linewidth=2,
                linestyle=line_style,
                connectionstyle=connection_style,
                shrinkA=15,
                shrinkB=15,
                zorder=1,
            )
            ax.add_patch(arrow)

        ax.autoscale()
        ax.axis("off")
        plt.tight_layout()

        log.info(
            **wrap_constants(
                message="Graph visualization complete",
                **{LC.EVENT_TYPE: "visualization", LC.ACTION: "visualize_complete"}
            )
        )

        if show:
            plt.show()
