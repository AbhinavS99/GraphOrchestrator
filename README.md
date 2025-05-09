<p align="center">
  <img src="https://raw.githubusercontent.com/AbhinavS99/GraphOrchestrator/main/logo/logo.png" alt="GraphOrchestrator Logo" width="300"/>
</p>

<h1 align="center">GraphOrchestrator</h1>

<p align="center">
  <em>Composable graph-based execution engine for AI, tool, and human-in-the-loop workflows</em>
</p>

<p align="center">
  <a href="https://github.com/AbhinavS99/GraphOrchestrator/actions/workflows/ci.yml"><img src="https://github.com/AbhinavS99/GraphOrchestrator/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://codecov.io/gh/AbhinavS99/GraphOrchestrator"><img src="https://codecov.io/gh/AbhinavS99/GraphOrchestrator/graph/badge.svg?token=U69VNUUQ6I" alt="codecov"/></a>
  <a href="https://badge.fury.io/py/graph-orchestrator"><img src="https://badge.fury.io/py/graph-orchestrator.svg" alt="PyPI version"/></a>
  <a href="https://github.com/AbhinavS99/GraphOrchestrator/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-BSD%202--Clause-orange.svg" alt="License: BSD-2-Clause"/></a>
</p>

---

## 🔍 Overview

**GraphOrchestrator** is a lightweight, extensible Python library for building stateful, directed-graph-based workflows. It supports seamless composition of tool-driven, AI-driven, and human-in-the-loop execution pipelines with fault-tolerant, parallel processing capabilities.

This library is ideal for:
- Designing modular decision engines
- Coordinating complex agent workflows
- Constructing robust data processing pipelines

## ✨ Features

- ⚖️ **Composable Node Architecture**: Easily define `ProcessingNode`, `ToolNode`, `AINode`, and `AggregatorNode`.
- → **Flexible Edges**: Connect nodes using `ConcreteEdge` (unconditional) or `ConditionalEdge` (routing-based).
- ♻️ **Retry and Fallback Support**: Configure per-node retry policies and fallback paths.
- 🌟 **Structured State Flow**: Core `State` object carries messages across the graph.
- ⏱️ **Parallel Superstep Execution**: Asynchronous executor with checkpointing and recovery.
- 🎨 **Visualization**: Render the execution graph using Matplotlib.
- 👨‍📚 **Human-in-the-Loop Nodes**: Pause for external input during execution.
- ✍️ **Decorators for Routing and Actions**: Annotate logic with `@node_action`, `@routing_function`, `@aggregator_action`.

## 🚀 Installation

```bash
pip install graph-orchestrator
```

## 🌐 Usage Example

```python
from graphorchestrator.builder.graph_builder_ import GraphBuilder
from graphorchestrator.decorators.actions import node_action
from graphorchestrator.core.state import State

@node_action
def say_hello(state: State) -> State:
    state.messages.append("Hello from node!")
    return state

builder = GraphBuilder(name="hello-graph")
builder.add_node("greet", say_hello)
builder.add_concrete_edge("start", "greet")
builder.add_concrete_edge("greet", "end")
graph = builder.build_graph()

intial_state = State(messages=[])_
executor = GraphExecutor(graph=graph, initial_state=intial_state)
final_state = await executor.execute()_
```

## 🌧️ Local Development Setup

Clone and install the project locally:

```bash
git clone https://github.com/AbhinavS99/GraphOrchestrator.git
cd GraphOrchestrator
pip install requirements.txt
pip install requirements.dev.txt
```

Run tests:

```bash
python -m pytest
```

Visualize graphs (requires Matplotlib):

```bash
pip install matplotlib
```

## 📚 Contributing

We welcome contributions of all kinds! Here's how to get started:

1. Fork the repo and create your branch:

   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes and write tests.  
3. Run lint and tests locally:

   ```bash
   pytest && coverage run -m pytest && coverage report
   ```

4. Submit a pull request with a clear description.

Please ensure all public functions include NumPy-style docstrings.

## 📑 License

GraphOrchestrator is released under the [BSD 2-Clause License](https://github.com/AbhinavS99/GraphOrchestrator/blob/main/LICENSE).

---

Made with ❤️ by [Abhinav Sharma](https://github.com/AbhinavS99)
