#!/usr/bin/env python3
"""
test_exocortex.py (v1.4.2)
Automated unit and integration tests for Exocortex.
Tests VaultIO, Guards, SessionManager, GraphStore, and ExecutionEngine in isolation.
"""

import os
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.vault_io import VaultIO
from server.graph_store import GraphStore, cosine_similarity
from core.guards import slice_for_embedding, estimate_tokens, prune_history_if_needed
from core.session import SessionManager
from core.engine import ExecutionEngine


class TestVaultIO(unittest.TestCase):
    """Tests filesystem isolation and path traversal prevention."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temp_dir.name)
        self.vault_io = VaultIO(vault_path=self.vault_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_directory_creation(self):
        self.assertTrue(self.vault_io.graphs_dir.exists())
        self.assertTrue(self.vault_io.sessions_dir.exists())
        self.assertTrue(self.vault_io.scratchpad_dir.exists())

    def test_path_traversal_prevention(self):
        with self.assertRaises(PermissionError):
            self.vault_io._resolve_safe_path("../../etc/passwd")

    def test_scratchpad_append_and_read(self):
        self.vault_io.append_scratchpad("Thought A", filename="test.md")
        self.vault_io.append_scratchpad("Thought B", filename="test.md")
        content = self.vault_io.read_note("Scratchpad/test.md")
        self.assertIn("Thought A", content)
        self.assertIn("Thought B", content)

    def test_graph_json_io(self):
        sample_data = {"nodes": [{"id": "BC_001"}], "links": []}
        self.vault_io.write_graph_json("test_graph", sample_data)
        loaded = self.vault_io.read_graph_json("test_graph")
        self.assertEqual(loaded["nodes"][0]["id"], "BC_001")


class TestGuards(unittest.TestCase):
    """Tests defensive guards against context overflows and token budgeting."""

    def test_slice_for_embedding_removes_code_and_truncates(self):
        long_code = "```python\n" + ("x = 1\n" * 500) + "```"
        text = f"Analyze this architecture: {long_code} and summarize."
        sliced = slice_for_embedding(text, max_chars=100)
        self.assertNotIn("x = 1", sliced)
        self.assertIn("[Code Block]", sliced)
        self.assertLessEqual(len(sliced), 100)

    def test_estimate_tokens(self):
        text = "Short text for token estimation."
        tokens = estimate_tokens(text)
        self.assertGreaterEqual(tokens, 1)

    def test_prune_history_if_needed(self):
        messages = [{"role": "system", "content": "Base system prompt"}]
        # Add 10 turns
        for i in range(10):
            messages.append({"role": "user", "content": f"Question {i}" * 50})
            messages.append({"role": "assistant", "content": f"Answer {i}" * 50})

        # Prune to max 2 turns
        pruned = prune_history_if_needed(messages, max_tokens=100, keep_recent_turns=2)
        # System prompt must remain intact
        self.assertEqual(pruned[0]["role"], "system")
        # System + (2 turns * 2 = 4) = 5 messages
        self.assertEqual(len(pruned), 5)
        self.assertEqual(pruned[-1]["role"], "assistant")


class TestSessionManager(unittest.TestCase):
    """Tests session state, token accounting, and synchronous persistence."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_io = VaultIO(vault_path=Path(self.temp_dir.name))
        self.session = SessionManager(session_name="test_session", vault_io=self.vault_io)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_message_flow_and_token_usage(self):
        self.session.add_user_message("Hello Exocortex")
        self.session.add_assistant_message("Ready for resonance.")
        usage = self.session.get_token_usage()
        self.assertEqual(usage["message_count"], 2)
        self.assertGreater(usage["estimated_tokens"], 0)

    def test_save_and_load_session(self):
        self.session.add_user_message("Architecture audit")
        self.session.add_assistant_message("Coupling isolated.")
        paths = self.session.save_session("audit_session")

        self.assertTrue(Path(paths["markdown"]).exists())
        self.assertTrue(Path(paths["json"]).exists())

        new_session = SessionManager(vault_io=self.vault_io)
        data = new_session.load_session("audit_session")
        self.assertEqual(len(new_session.messages), 2)
        self.assertEqual(new_session.messages[0]["content"], "Architecture audit")

class TestGraphStore(unittest.TestCase):
    """Tests graph state, imprinting, resonance, mutations, and Canvas projection."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temp_dir.name)
        self.vault_io = VaultIO(vault_path=self.vault_path)
        
        # Create initial test graph
        initial_graph = {
            "directed": True,
            "multigraph": False,
            "graph": {"name": "default"},
            "nodes": [
                {
                    "id": "BC_001", 
                    "type": "BoundaryConstraint", 
                    "label": "Single_Responsibility", 
                    "payload": "Modular separation.", 
                    "embedding": [0.1, 0.2, 0.3],
                    "weight": 1.0
                }
            ],
            "edges": []
        }
        self.vault_io.write_graph_json("default", initial_graph)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("ollama.Client")
    def test_imprint_node_and_canvas_sync(self, mock_ollama):
        # Mock Ollama embeddings
        mock_client = MagicMock()
        mock_client.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_ollama.return_value = mock_client

        store = GraphStore(vault_io=self.vault_io)
        res = store.imprint_node(
            node_type="TrajectoryOperator",
            label="Decoupled_Daemon",
            content_payload="Separation of cognition and substrate.",
            tensor_links=["BC_001"]
        )

        self.assertEqual(res["node_id"], "TO_001")
        stats = store.get_graph_stats()
        self.assertEqual(stats["node_count"], 2)

        # Verify Canvas generation
        canvas_file = self.vault_path / "Exocortex_Interactive.canvas"
        self.assertTrue(canvas_file.exists())
        with open(canvas_file, "r", encoding="utf-8") as f:
            canvas_data = json.load(f)
            self.assertEqual(len(canvas_data["nodes"]), 2)
            self.assertGreaterEqual(len(canvas_data["edges"]), 1)

    @patch("ollama.Client")
    def test_mutate_node_actions(self, mock_ollama):
        """Tests STRENGTHEN, DECAY, UPDATE, PRUNE logic and constraints."""
        mock_client = MagicMock()
        # Embedding for UPDATE action
        mock_client.embeddings.return_value = {"embedding": [0.9, 0.9, 0.9]}
        mock_ollama.return_value = mock_client

        store = GraphStore(vault_io=self.vault_io)
        target_id = "BC_001"

        # 1. Test STRENGTHEN (capped at 3.0)
        res_s = store.mutate_node(target_id, action="STRENGTHEN", delta=0.5)
        self.assertEqual(res_s["status"], "success")
        self.assertEqual(res_s["new_weight"], 1.5)
        self.assertEqual(store.graph.nodes[target_id]["weight"], 1.5)

        store.mutate_node(target_id, action="STRENGTHEN", delta=2.0) # Should cap
        self.assertEqual(store.graph.nodes[target_id]["weight"], 3.0)

        # 2. Test DECAY (floor at 0.05)
        res_d = store.mutate_node(target_id, action="DECAY", delta=2.0)
        self.assertEqual(res_d["status"], "success")
        self.assertEqual(res_d["new_weight"], 1.0) # 3.0 - 2.0

        store.mutate_node(target_id, action="DECAY", delta=0.99) # Should hit floor
        self.assertEqual(store.graph.nodes[target_id]["weight"], 0.05)

        # 3. Test UPDATE (requires payload, updates embedding)
        res_u = store.mutate_node(target_id, action="UPDATE", payload_update="Updated Axiom.")
        self.assertEqual(res_u["status"], "success")
        self.assertEqual(store.graph.nodes[target_id]["payload"], "Updated Axiom.")
        self.assertEqual(store.graph.nodes[target_id]["embedding"], [0.9, 0.9, 0.9])

        # Test UPDATE error case
        res_u_err = store.mutate_node(target_id, action="UPDATE", payload_update="")
        self.assertEqual(res_u_err["status"], "error")

        # 4. Test PRUNE
        res_p = store.mutate_node(target_id, action="PRUNE")
        self.assertEqual(res_p["status"], "success")
        self.assertFalse(store.graph.has_node(target_id))
        self.assertEqual(store.get_graph_stats()["node_count"], 0)

        # 5. Test Non-existent Node
        res_err = store.mutate_node("VOID_001", action="DECAY")
        self.assertEqual(res_err["status"], "error")

    def test_cosine_similarity(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(cosine_similarity(v1, v3), 0.0)


class TestExecutionEngineIntegration(unittest.TestCase):
    """Tests tool schema, prompt assembly, and dispatching."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temp_dir.name)
        self.vault_io = VaultIO(vault_path=self.vault_path)
        
        initial_graph = {
            "directed": True,
            "multigraph": False,
            "graph": {"name": "default"},
            "nodes": [
                 {"id": "BC_001", "type": "BoundaryConstraint", "label": "Test", "payload": "...", "embedding": [0.1], "weight": 1.0}
            ],
            "edges": []
        }
        self.vault_io.write_graph_json("default", initial_graph)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("ollama.Client")
    def test_engine_tool_dispatch(self, mock_ollama):
        mock_client = MagicMock()
        mock_client.embeddings.return_value = {"embedding": [0.1, 0.1, 0.1]}
        mock_ollama.return_value = mock_client

        store = GraphStore(vault_io=self.vault_io)
        session = SessionManager(vault_io=self.vault_io)
        engine = ExecutionEngine(graph_store=store, session_manager=session)

        # 1. Schema completeness
        tool_names = [t["function"]["name"] for t in engine.tools_schema]
        self.assertIn("read_vault_note", tool_names)
        self.assertIn("exocortex_imprint_field", tool_names)
        self.assertIn("exocortex_temporal_anchor", tool_names)
        self.assertIn("exocortex_mutate_phase_space", tool_names)

        # 2. Legacy Tool dispatching test
        anchor_result = engine.tool_handlers["exocortex_temporal_anchor"](scope="iso")
        self.assertIn("<temporal_anchor>", anchor_result)

        # 3. Mutation Tool dispatching test (STRENGTHEN)
        mutate_result = engine.tool_handlers["exocortex_mutate_phase_space"](
            target_node_id="BC_001", 
            action="STRENGTHEN",
            delta=0.2
        )
        self.assertIn("<phase_space_mutation status='success'", mutate_result)
        self.assertIn("action='STRENGTHEN'", mutate_result)
        self.assertIn("new_weight='1.2'", mutate_result) # 1.0 + 0.2


if __name__ == "__main__":
    unittest.main(verbosity=2)
