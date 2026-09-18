"""Public-derivative checks; not the historical 642-test regression."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from nlc.formal.model import AuthorityDomain, AdmissionDecision  # noqa: E402
from nlc.m6.t1.constructor import RecoveryReject, RecoveryStore, slot  # noqa: E402
from nlc.m6.t1.fixtures import baseline as recovery_baseline  # noqa: E402
from verifier.rp1_verifier import PROPERTIES, verify  # noqa: E402

EVIDENCE = ROOT / "evidence"


def read(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def bundle() -> tuple[dict, ...]:
    return (
        read("NLC_RP1_Complete_Provenance_Graph_v1.json"),
        read("NLC_RP1_Gate_A_to_D_Audit_v1.json"),
        read("NLC_RP1_Final_Demo_Results_v1.json"),
        read("NLC_RP1_Eight_Property_Final_Status_v1.json"),
        read("NLC_RP1_Limitations_Register_v1.json"),
        read("NLC_RP1_Claim_Boundary_Audit_v1.json"),
        read("rp1_package.json"),
    )


class PublicDerivativeChecks(unittest.TestCase):
    def test_01_model_vocabulary(self) -> None:
        self.assertEqual("D_o", AuthorityDomain.OLD.value)
        self.assertEqual("QUARANTINE", AdmissionDecision.QUARANTINE.value)

    def test_02_eight_property_inventory(self) -> None:
        evidence = read("NLC_RP1_Eight_Property_Final_Status_v1.json")
        self.assertEqual("8/8", evidence["preserved"])
        self.assertEqual(0, evidence["contradictions"])
        self.assertEqual(PROPERTIES, tuple(row["property"] for row in evidence["rows"]))
        self.assertTrue(all(row["nonvacuous"] and not row["universal_proof_claimed"] for row in evidence["rows"]))

    def test_03_historical_evidence_consistency_verifier(self) -> None:
        result = verify(*bundle())
        self.assertEqual("ACCEPT", result["verdict"])
        self.assertEqual((18, 9, 9, 8), tuple(result[k] for k in ("hashes_checked", "gates_recomputed", "demos_recomputed", "properties_recomputed")))
        # This validates the copied records' internal structure, not omitted private-file hashes.

    def test_04_negative_property_mutation(self) -> None:
        data = list(copy.deepcopy(bundle()))
        data[3]["rows"][0]["contradiction"] = True
        self.assertIn("PROPERTIES", verify(*data)["findings"])

    def test_05_negative_demo_mutation(self) -> None:
        data = list(copy.deepcopy(bundle()))
        data[2]["demos"][0]["verdict"] = "FAIL"
        self.assertIn("DEMO_VERDICTS", verify(*data)["findings"])

    def test_06_negative_provenance_mutation(self) -> None:
        data = list(copy.deepcopy(bundle()))
        data[0]["mismatches"] = 1
        self.assertIn("PROVENANCE", verify(*data)["findings"])

    def test_07_tc3_captured_values(self) -> None:
        data = read("TC3_Finite_PreCutover_Expansion_Evidence_v1.json")
        self.assertEqual((8064, 8128), tuple(row["B_safe"] for row in data["capture_experiments"]))
        self.assertEqual((48, 49), tuple(row["exact_reachable_state_union"] for row in data["capture_experiments"]))
        self.assertEqual((7, 8), tuple(row["B_execution_reference"] for row in data["capture_experiments"]))

    def test_08_m8_projection_boundary(self) -> None:
        data = read("M8_T3_State_Explosion_Report_v1.json")
        self.assertEqual(16859136, data["strongest_projected_states"])
        self.assertTrue(data["resource_limited_variants"])

    def test_09_gate_e_record(self) -> None:
        data = read("Gate_E_Decision_Record_v1.json")
        self.assertEqual("CERBERUS_NLC_GATE_E_ACCEPTED", data["status"])
        self.assertEqual(0, data["property_contradictions"])

    def test_10_representative_negative_records(self) -> None:
        paths = (
            ("TC-2", ROOT / "counterexamples/t3/t3-toggle-unknown-clean/tc-2_counterexample_v1.json"),
            ("TC-4", ROOT / "counterexamples/t3/t3-toggle-old-scope-unfenced/tc-4_counterexample_v1.json"),
            ("NTC-1", ROOT / "counterexamples/t3/t3-toggle-closed-schema-removed/ntc-1_counterexample_v1.json"),
        )
        for property_id, path in paths:
            with self.subTest(property=property_id):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(property_id, data["property_id"])
                self.assertGreater(data["violation_count"], 0)

    def test_11_recovery_retry_single_output(self) -> None:
        material, templates = recovery_baseline()
        store = RecoveryStore()
        first = store.recover(material, templates, "Reviewer-A")
        second = store.recover(material, templates, "Reviewer-B")
        self.assertEqual((first["slot_id"], first["result_bytes"]), (second["slot_id"], second["result_bytes"]))
        self.assertEqual(1, store.metrics(first["slot_id"]).mint_count)

    def test_12_unknown_settlement_holds(self) -> None:
        material, templates = recovery_baseline()
        material["settlement_context"]["state"] = "UNKNOWN"
        result = RecoveryStore().recover(material, templates, "Reviewer")
        self.assertEqual("HOLD", result["verdict"])
        self.assertIsNone(result["result_bytes"])

    def test_13_old_authority_carrier_rejected(self) -> None:
        material, _ = recovery_baseline()
        material["sterile_checkpoint_identity"][0]["value"]["old_token"] = "synthetic-old-token"
        with self.assertRaises(RecoveryReject):
            slot(material)


if __name__ == "__main__":
    unittest.main(verbosity=2)
