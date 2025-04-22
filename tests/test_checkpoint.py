import os
import pytest
from graphorchestrator.core.state import State
from graphorchestrator.core.checkpoint import PickleCheckpointStore
from graphorchestrator.graph.builder import GraphBuilder
from graphorchestrator.graph.executor import GraphExecutor
from graphorchestrator.nodes.nodes import ProcessingNode
from graphorchestrator.decorators.actions import node_action

CHECKPOINT_PATH = ".checkpoints/test_resume.pkl"
execution_log = []

@node_action
def node1_action(state: State):
    execution_log.append("node1")
    state.messages.append("node1_done")
    return state

@node_action
def node2_action(state: State):
    execution_log.append("node2")
    state.messages.append("node2_done")
    return state

@pytest.mark.asyncio
async def test_checkpoint_resume():
    # Setup: clean checkpoint directory
    os.makedirs(".checkpoints", exist_ok=True)
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    # Step 1: Build graph
    builder = GraphBuilder()
    builder.add_node(ProcessingNode("node1", node1_action))
    builder.add_node(ProcessingNode("node2", node2_action))
    builder.add_concrete_edge("start", "node1")
    builder.add_concrete_edge("node1", "node2")
    builder.add_concrete_edge("node2", "end")
    graph = builder.build_graph()

    # Step 2: Simulate first run and save checkpoint after node1
    checkpoint_store = PickleCheckpointStore(CHECKPOINT_PATH)
    initial_state = State(messages=["start"])
    executor = GraphExecutor(graph, initial_state, checkpoint_store=checkpoint_store)
    
    # Manually simulate state after node1
    state_after_node1 = State(messages=["start", "node1_done"])
    executor.checkpoint_store.save_checkpoint(1, {"node2": [state_after_node1]})

    # Step 3: Resume and execute node2
    resumed_executor = GraphExecutor(graph, initial_state, checkpoint_store=checkpoint_store)
    final_state = await resumed_executor.execute()

    # ✅ Assertions
    assert "node2_done" in final_state.messages
    assert "node1" not in execution_log  # Was not re-run
    assert "node2" in execution_log      # Was resumed

@pytest.mark.asyncio
async def test_checkpoint_fresh_execution():
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    builder = GraphBuilder()
    
    @node_action
    def simple_node(state: State):
        state.messages.append("ok")
        return state

    builder.add_node(ProcessingNode("n1", simple_node))
    builder.add_concrete_edge("start", "n1")
    builder.add_concrete_edge("n1", "end")
    graph = builder.build_graph()

    executor = GraphExecutor(graph, State(messages=[]),
                             checkpoint_store=PickleCheckpointStore(CHECKPOINT_PATH))
    final = await executor.execute()

    assert "ok" in final.messages
    assert os.path.exists(CHECKPOINT_PATH)

@pytest.mark.asyncio
async def test_checkpoint_resume_skips_completed_node():
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    call_log = []

    @node_action
    def record_node(state: State):
        call_log.append("executed")
        state.messages.append("run")
        return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("a", record_node))
    builder.add_concrete_edge("start", "a")
    builder.add_concrete_edge("a", "end")
    graph = builder.build_graph()

    store = PickleCheckpointStore(CHECKPOINT_PATH)
    store.save_checkpoint(1, {"end": [State(messages=["run"])]})

    resumed_executor = GraphExecutor(graph, State(messages=[]), checkpoint_store=store)
    final = await resumed_executor.execute()

    assert final.messages == ["run"]
    assert call_log == []  # node was not re-run

@pytest.mark.asyncio
async def test_checkpoint_invalid_file_format(tmp_path):
    path = tmp_path / "bad.pkl"
    path.write_text("this is not pickle")

    store = PickleCheckpointStore(str(path))
    
    with pytest.raises(Exception):
        store.load_checkpoint()

def test_checkpoint_clear_removes_file():
    path = CHECKPOINT_PATH
    store = PickleCheckpointStore(path)
    
    # Simulate something
    store.save_checkpoint(0, {"dummy": [State(messages=[])]})
    assert os.path.exists(path)

    store.clear_checkpoints()
    assert not os.path.exists(path)


@pytest.mark.asyncio
async def test_resume_multi_node_graph():
    os.makedirs(".checkpoints", exist_ok=True)
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)

    @node_action
    def n1(state): state.messages.append("n1"); return state
    @node_action
    def n2(state): state.messages.append("n2"); return state
    @node_action
    def n3(state): state.messages.append("n3"); return state

    builder = GraphBuilder()
    builder.add_node(ProcessingNode("n1", n1))
    builder.add_node(ProcessingNode("n2", n2))
    builder.add_node(ProcessingNode("n3", n3))
    builder.add_concrete_edge("start", "n1")
    builder.add_concrete_edge("n1", "n2")
    builder.add_concrete_edge("n2", "n3")
    builder.add_concrete_edge("n3", "end")
    graph = builder.build_graph()

    # Simulate we stopped at n2
    partial_state = State(messages=["n1", "n2"])
    store = PickleCheckpointStore(CHECKPOINT_PATH)
    store.save_checkpoint(2, {"n3": [partial_state]})

    executor = GraphExecutor(graph, State(messages=[]), checkpoint_store=store)
    result = await executor.execute()

    assert result.messages == ["n1", "n2", "n3"]
