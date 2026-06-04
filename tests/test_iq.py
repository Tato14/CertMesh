"""Foundry IQ retrieval/grounding, Fabric IQ ontology, Work IQ capacity."""

from certmesh.iq.foundry_iq import supports


def test_foundry_retrieves_and_grounds(foundry):
    res = foundry.retrieve("Key Vault managed identity", certification="AZ-204", top_k=3)
    assert not res.is_empty
    top = res.chunks[0]
    assert "key vault" in top.text.lower()
    # the retrieved snippet is grounded in the corpus by construction
    assert supports(top.text, foundry.all_chunk_texts)


def test_supports_rejects_fabricated_text(foundry):
    assert not supports("AZ-204 requires a blockchain ledger to store secrets.",
                        foundry.all_chunk_texts)


def test_supports_needs_min_length(foundry):
    assert not supports("Azure", foundry.all_chunk_texts)  # too short to count


def test_known_certifications(foundry):
    certs = foundry.known_certifications()
    assert {"AZ-204", "DP-203", "CLIN-SAFE-1", "GDPR-HC-2"} <= certs


def test_fabric_ontology(fabric):
    assert fabric.is_known_cert("AZ-204")
    assert not fabric.is_known_cert("AWS Solutions Architect")
    assert fabric.prerequisite_chain("AZ-400") == ["AZ-900", "AZ-204"]
    assert fabric.pass_threshold("GDPR-HC-2") == 0.80
    assert "Key Vault and managed identity" in fabric.skills_for("AZ-204")
    assert fabric.next_certification("DevOps Engineer", "AZ-204") == "AZ-400"


def test_fabric_resolves_title_and_role(fabric):
    assert fabric.resolve_cert("Developing Solutions for Microsoft Azure") == "AZ-204"
    assert fabric.resolve_role("devops engineer") == "DevOps Engineer"


def test_fabric_skill_difficulty_orders(fabric):
    skills = fabric.skills_for("AZ-204")
    assert fabric.skill_difficulty("AZ-204", skills[0]) == "foundational"
    assert fabric.skill_difficulty("AZ-204", skills[-1]) == "advanced"


def test_work_iq_capacity(work):
    assert work.available_focus_hours("EMP-012") == 3.0
    assert work.is_capacity_constrained("EMP-012")
    assert not work.is_capacity_constrained("EMP-005")
    cap = work.team_capacity(["EMP-010", "EMP-011", "EMP-012", "EMP-013", "EMP-014"])
    assert cap.constrained and cap.n == 5


def test_work_iq_unknown_employee_defaults(work):
    sig = work.signal(None)
    assert sig.focus_hours_per_week > 0
