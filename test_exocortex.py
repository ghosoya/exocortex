"""
test_exocortex.py
Modular unit & integration test suite for the Exocortex cognitive engine.
Tests Vault I/O, GraphStore, Guards, Sessions, Compiler, and Prompt Management.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json

from core.guards import slice_for_embedding, estimate_tokens, prune_history_if_needed
from core.session import SessionManager
from core.compiler import compile_topology_prompt, _normalize_topology_schema
from core.prompts import PromptManager
from server.vault_io import VaultIO
from server.graph_store import GraphStore, NodeType, cosine_similarity


class TestGuards(unittest.TestCase):
    def test_slice_for_embedding_removes_code_and_truncates(self):
        raw_text = "Here is an axiom: ```python\nprint('secret')\n``` End of note."
        sliced = slice_for_embedding(raw_text, max_chars=50)
        self.assertNotIn("print('secret')", sliced)
        self.assertIn("[Code Block]", sliced)
        self.assertLessEqual(len(sliced), 50)

    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertGreaterEqual(estimate_tokens("Hello World"), 1)

    def test_prune_history_if_needed(self):
        messages = [
            {"role": "system", "content": "You are Exocortex."},
            {"role": "user", "content": "Query 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Query 2"},
            {"role": "assistant", "content": "Response 2"},
        ]
        # Token limit high enough -> no pruning
        pruned = prune_history_if_needed(messages, max_tokens=1000, keep_recent_turns=1)
        self.assertEqual(len(pruned), 5)

        # Forced pruning -> retains system prompt and recent tail
        pruned_forced = prune_history_if_needed(messages, max_tokens=2, keep_recent_turns=1)
        self.assertEqual(pruned_forced[0]["role"], "system")
        self.assertEqual(pruned_forced[1]["role"], "user")
        self.assertEqual(pruned_forced[1]["content"], "Query 2")


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.vault_io = VaultIO(vault_path=Path(self.temp_dir))
        self.session = SessionManager(session_name="test_session", vault_io=self.vault_io)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_message_flow_and_token_usage(self):
        self.session.add_user_message("Hello Exocortex")
        self.session.add_assistant_message("Hello Operator")
        self.assertEqual(len(self.session.messages), 2)

        usage = self.session.get_token_usage()
        self.assertEqual(usage["message_count"], 2)
        self.assertGreater(usage["estimated_tokens"], 0)

    def test_save_and_load_session(self):
        self.session.add_user_message("State Mutation")
        self.session.add_assistant_message("Concept Created")
        paths = self.session.save_session("persisted_session")

        self.assertTrue(Path(paths["markdown"]).exists())
        self.assertTrue(Path(paths["json"]).exists())

        new_session = SessionManager(vault_io=self.vault_io)
        data = new_session.load_session("persisted_session")
        self.assertEqual(len(new_session.messages), 2)
        self.assertEqual(data["session_name"], "persisted_session")


class TestVaultIO(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.vault_io = VaultIO(vault_path=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_directory_creation(self):
        self.assertTrue(self.vault_io.graphs_dir.exists())
        self.assertTrue(self.vault_io.sessions_dir.exists())
        self.assertTrue(self.vault_io.scratchpad_dir.exists())

    def test_scratchpad_append_and_read(self):
        path = self.vault_io.append_scratchpad("Test insight", filename="Insights.md")
        self.assertTrue(Path(path).exists())
        content = self.vault_io.read_note("Insights.md")
        self.assertIn("Test insight", content)

    def test_graph_json_io(self):
        dummy_graph = {"nodes": [{"id": "CST_001", "type": "Constraint"}], "edges": []}
        saved_path = self.vault_io.write_graph_json("test_graph", dummy_graph)
        self.assertTrue(Path(saved_path).exists())

        loaded = self.vault_io.read_graph_json("test_graph")
        self.assertEqual(loaded["nodes"][0]["id"], "CST_001")

    def test_path_traversal_prevention(self):
        with self.assertRaises(PermissionError):
            self.vault_io._resolve_safe_path("../../../outside.txt")


class TestGraphStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.vault_io = VaultIO(vault_path=Path(self.temp_dir))
        
        # Seed default graph with canonical v1.5 types
        seed_data = {
            "nodes": [
                {"id": "CST_001", "type": "Constraint", "label": "Test Guard", "payload": "Strict typing"},
                {"id": "CNC_001", "type": "Concept", "label": "Test Well", "payload": "Modular architecture"}
            ],
            "edges": []
        }
        self.vault_io.write_graph_json("default", seed_data)
        self.store = GraphStore(vault_io=self.vault_io)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_cosine_similarity(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 1.0)
        self.assertAlmostEqual(cosine_similarity(v1, v3), 0.0)
        self.assertEqual(cosine_similarity([], []), 0.0)

    def test_imprint_node_and_canvas_sync(self):
        res = self.store.imprint_node(
            node_type="Constraint",
            label="Zero_Leak",
            content_payload="Prevent side effects",
            links=["CNC_001"]
        )
        self.assertEqual(res["node_id"], "CST_002")
        self.assertTrue(self.store.graph.has_node("CST_002"))
        self.assertTrue(self.store.graph.has_edge("CST_002", "CNC_001"))

        # Verify Canvas synchronization
        canvas_path = self.vault_io.vault_path / "Exocortex_Interactive.canvas"
        self.assertTrue(canvas_path.exists())

    def test_mutate_node_actions(self):
        # 1. STRENGTHEN
        res = self.store.mutate_node("CST_001", action="STRENGTHEN", delta=0.5)
        self.assertEqual(res["new_weight"], 1.5)

        # 2. DECAY
        res = self.store.mutate_node("CST_001", action="DECAY", delta=0.3)
        self.assertEqual(res["new_weight"], 1.2)

        # 3. SET_WEIGHT
        res = self.store.mutate_node("CST_001", action="SET_WEIGHT", delta=2.5)
        self.assertEqual(res["new_weight"], 2.5)

        # 4. UPDATE
        res = self.store.mutate_node("CST_001", action="UPDATE", payload_update="Updated Guardrail Axiom")
        self.assertEqual(res["updated_payload"], "Updated Guardrail Axiom")
        self.assertEqual(self.store.graph.nodes["CST_001"]["payload"], "Updated Guardrail Axiom")

        # 5. PRUNE
        res = self.store.mutate_node("CST_001", action="PRUNE")
        self.assertFalse(self.store.graph.has_node("CST_001"))

    def test_freeze_snapshot(self):
        res = self.store.freeze_snapshot(tag="test_freeze")
        self.assertTrue(Path(res["json_path"]).exists())
        self.assertTrue(Path(res["canvas_path"]).exists())
        
    def test_imprint_node_comprehensive(self):
        """Verifiziert deterministische ID, Embedding, Kanten und Persistence."""
        # 1. Erster Imprint
        res1 = self.store.imprint_node(
            node_type="Rule",
            label="Test_Operator_A",
            content_payload="Erster Test-Payload",
            links=["CST_001"]
        )
        node_id_1 = res1["node_id"]
        self.assertTrue(node_id_1.startswith("RUL_"))
    
        node_data_1 = self.store.graph.nodes[node_id_1]
        self.assertEqual(node_data_1["label"], "Test_Operator_A")
        self.assertEqual(node_data_1["weight"], 1.0)
        self.assertIn("created_at", node_data_1)
    
        # 2. Zweiter Imprint (Prüfung der ID-Inkrementierung & Kanten)
        res2 = self.store.imprint_node(
            node_type="Rule",
            label="Test_Operator_B",
            content_payload="Zweiter Test-Payload",
            links=[node_id_1]
        )
        node_id_2 = res2["node_id"]
        idx1 = int(node_id_1.split("_")[1])
        idx2 = int(node_id_2.split("_")[1])
        self.assertEqual(idx2, idx1 + 1)
    
        # Kantenprüfung
        self.assertTrue(self.store.graph.has_edge(node_id_2, node_id_1))
        edge = self.store.graph.edges[node_id_2, node_id_1]
        self.assertEqual(edge.get("relation"), "relates_to")
        self.assertEqual(edge.get("weight"), 0.85)
        
    def test_get_graph_stats(self):
        stats = self.store.get_graph_stats()
        self.assertEqual(stats["name"], "default")
        self.assertEqual(stats["node_count"], 2)
        self.assertEqual(stats["edge_count"], 0)

    def test_assemble_field_context_with_1hop_links(self):
        # 1. Zweiten Knoten und gerichtete Kante anlegen
        self.store.graph.add_node(
            "RUL_001",
            type="Rule",
            label="Decoupling_Operator",
            payload="Isolate dependencies",
            weight=1.0
        )
        self.store.graph.add_edge("CNC_001", "RUL_001", relation="grounds_in", weight=0.85)
        
        # 2. Query zielt semantisch auf CNC_001 ('Modular architecture')
        xml_context = self.store.assemble_context_frame("Modular software architecture and components")
        
        # 3. Assertions: XML-Struktur, Ähnlichkeit und 1-Hop-Nachbar
        self.assertIn("<active_context", xml_context)
        self.assertIn("CNC_001", xml_context)
        self.assertIn("RUL_001", xml_context)
        self.assertIn("graph_neighbor", xml_context)
        self.assertIn("<graph_links>", xml_context)
        self.assertIn("relation='grounds_in'", xml_context)

    def test_compute_telemetry_mechanics(self):
        prompt_vec = [1.0, 0.0, 0.0]
        resp_echo = [1.0, 0.0, 0.0]
        resp_diff = [0.0, 1.0, 0.0]
        well_vec = [0.0, 1.0, 0.0]
        
        self.assertAlmostEqual(cosine_similarity(prompt_vec, resp_echo), 1.0)
        self.assertAlmostEqual(cosine_similarity(prompt_vec, resp_diff), 0.0)
        
        lift_positive = cosine_similarity(resp_diff, well_vec) - cosine_similarity(prompt_vec, well_vec)
        self.assertAlmostEqual(lift_positive, 1.0)
        
        lift_neutral = cosine_similarity(prompt_vec, well_vec) - cosine_similarity(prompt_vec, well_vec)
        self.assertAlmostEqual(lift_neutral, 0.0)


class TestCompilerAndPrompts(unittest.TestCase):
    def test_declarative_schema_normalization(self):
        declarative_data = {
            "topology_name": "TEST_DECLARATIVE",
            "boundary_constraints": [
                {"id": "BC_001", "name": "Strict Typing", "description": "No any types allowed", "strictness": 0.95}
            ],
            "potential_wells": [
                {"id": "PW_001", "name": "Simplicity", "description": "KISS principle", "energy_depth": 0.90}
            ]
        }
        normalized = _normalize_topology_schema(declarative_data)
        self.assertIn("nodes", normalized)
        self.assertEqual(len(normalized["nodes"]), 2)
        # Überprüft automatische Normalisierung auf neue Typen
        self.assertEqual(normalized["nodes"][0]["type"], "Constraint")
        self.assertEqual(normalized["nodes"][1]["type"], "Concept")

    def test_compile_manifold_prompt(self):
        sample = {
            "topology_name": "TEST_TOPO",
            "nodes": [
                {"id": "CST_001", "type": "Constraint", "label": "Immutability", "payload": "Pure functions only", "weight": 1.0}
            ],
            "edges": []
        }
        prompt = compile_topology_prompt(sample)
        self.assertIn("KNOWLEDGE TOPOLOGY: `TEST_TOPO`", prompt)
        self.assertIn("CST_001", prompt)
        self.assertIn("Pure functions only", prompt)

    def test_prompt_manager_profiles(self):
        pm = PromptManager()
        self.assertEqual(pm.active_profile, "default")
        
        self.assertTrue(pm.set_profile("architect"))
        self.assertEqual(pm.active_profile, "architect")
        self.assertIn("Architect Mode", pm.get_base_prompt())

        pm.set_custom("Custom Operator Override")
        self.assertEqual(pm.get_base_prompt(), "Custom Operator Override")

        pm.reset()
        self.assertEqual(pm.active_profile, "default")


if __name__ == "__main__":
    unittest.main()
