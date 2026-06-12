"""HTTP gateway: graph/calendar/progress presentation endpoints + privacy guard.

These endpoints are additive presentation layers over the IQ layers; the tests
pin their shape for the dashboard and hold the aggregate progress endpoints to
the same PII contract the critic enforces on manager insights.
"""

import re

import pytest
from app.api import app
from fastapi.testclient import TestClient

_PII = re.compile(r"\bL-\d{4}\b|\bEMP-\d{3}\b")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# ── graph ────────────────────────────────────────────────────────────────────

def test_graph_elements_and_types(client):
    d = client.get("/api/graph").json()
    nodes = d["elements"]["nodes"]
    edges = d["elements"]["edges"]
    types = {n["data"]["type"] for n in nodes}
    assert types == {"role", "certification", "skill"}
    assert {e["data"]["type"] for e in edges} == {"requires", "covers", "prerequisite"}
    az204 = next(n["data"] for n in nodes if n["data"]["id"] == "cert:AZ-204")
    assert az204["threshold"] == 0.70 and az204["hours"] == 60 and az204["track"] == "technical"
    assert any(e["data"]["source"] == "cert:AZ-900" and e["data"]["target"] == "cert:AZ-204"
               and e["data"]["type"] == "prerequisite" for e in edges)
    assert d["synthetic"] is True


def test_graph_role_paths_ordered(client):
    d = client.get("/api/graph").json()
    devops = d["roles"]["DevOps Engineer"]
    assert devops["certs"] == ["AZ-900", "AZ-204", "AZ-400"]   # prerequisite order
    assert devops["total_hours"] == 160 and devops["prerequisite_edges"] == 2
    assert any(lr["learner_id"] == "L-1012" for lr in d["learners"])
    # roles carry the seed's declared track (deterministic, not majority-voted)
    assert d["roles"]["Information Governance Lead"]["track"] == "compliance"


def test_graph_roster_has_no_team_join_keys(client):
    """The graph roster must not expose team/track, so it cannot be joined
    against the manager view's k-anonymity-suppressed groups."""
    for lr in client.get("/api/graph").json()["learners"]:
        assert "team" not in lr and "track" not in lr


def test_graph_extended_ecosystem(client):
    """The expanded ontology: full Microsoft catalogue + internal certs, with
    levels and prerequisite chains for the new entries."""
    d = client.get("/api/graph").json()
    certs = {n["data"]["label"]: n["data"] for n in d["elements"]["nodes"]
             if n["data"]["type"] == "certification"}
    assert len(certs) >= 30
    assert certs["AI-900"]["level"] == "fundamentals"
    assert certs["AZ-305"]["level"] == "expert"
    assert certs["MEDDEV-AI-1"]["level"] == "internal"
    assert certs["SC-200"]["track"] == "security"
    edges = d["elements"]["edges"]
    assert any(e["data"]["source"] == "cert:SC-200" and e["data"]["target"] == "cert:SC-100"
               and e["data"]["type"] == "prerequisite" for e in edges)
    assert d["roles"]["Security Architect"]["certs"] == ["AZ-900", "AZ-104", "AZ-500", "SC-900", "SC-200", "SC-100"]


def test_scorecard_and_live_eval_run(client):
    d = client.post("/api/evals/run").json()
    assert d["metrics"]["total_cases"] >= 65
    assert all(d["gates"].values()), f"gate failure: {d['gates']}"
    assert d["by_kind"]["redteam"]["passed"] == d["by_kind"]["redteam"]["total"]
    sc = client.get("/api/scorecard").json()
    assert sc["scorecard"]["gates"]["redteam_block==1.0"] is True


def test_source_endpoint_serves_verbatim_chunks(client):
    r = client.post("/api/run", json={"view": "learner", "goal": "Prepare for AZ-204"}).json()
    cite = r["curated_path"]["resources"][0]["citation"]
    src = client.get("/api/source", params={"id": cite["source_id"]}).json()
    assert cite["snippet"].lower().split()[0] in src["text"].lower()
    assert src["locator"] == cite["locator"]
    assert client.get("/api/source", params={"id": "nope#99"}).status_code == 404


def test_new_cert_runs_grounded_end_to_end(client):
    """A certification added in the catalogue extension must produce a fully
    grounded run: cited resources, accepted critic verdicts, an assessment."""
    r = client.post("/api/run", json={"view": "learner", "goal": "Help me prepare for AZ-104"}).json()
    assert not r["abstained"]
    assert r["curated_path"]["certification"] == "AZ-104"
    assert len(r["curated_path"]["resources"]) >= 4
    assert r["assessment"]["threshold"] == 0.70
    for step in r["trace"]["steps"]:
        if step["critic"]:
            assert step["critic"]["action"] in ("accept", "revise")  # never abstain
    # every cited resource for AZ-104 comes from the AZ-104 catalogue section
    for res in r["curated_path"]["resources"]:
        if res["citation"]["kind"] == "foundry_iq":
            assert "AZ-104" in res["citation"]["locator"]


# ── calendar ─────────────────────────────────────────────────────────────────

def test_calendar_blocks_consistent(client):
    d = client.get("/api/calendar/L-1012").json()
    assert d["employee_id"] == "EMP-012" and d["certification"] == "CLIN-SAFE-2"
    kinds = {b["kind"] for b in d["blocks"]}
    assert {"meeting", "focus", "study"} <= kinds
    # study sessions never overlap meetings
    for day in d["days"]:
        meetings = [b for b in d["blocks"] if b["day"] == day and b["kind"] == "meeting"]
        studies = [b for b in d["blocks"] if b["day"] == day and b["kind"] == "study"]
        for s in studies:
            for m in meetings:
                assert (_minutes(s["end"]) <= _minutes(m["start"])
                        or _minutes(s["start"]) >= _minutes(m["end"]))
    # meeting hours approximate the Work IQ signal
    meet_min = sum(_minutes(b["end"]) - _minutes(b["start"])
                   for b in d["blocks"] if b["kind"] == "meeting")
    assert abs(meet_min / 60 - d["signal"]["meeting_hours_per_week"]) <= 2.0
    assert d["synthetic"] is True


def test_calendar_contrast_l1012_vs_l1005(client):
    slow = client.get("/api/calendar/L-1012").json()
    fast = client.get("/api/calendar/L-1005").json()
    slow_study = [b for b in slow["blocks"] if b["kind"] == "study"]
    fast_study = [b for b in fast["blocks"] if b["kind"] == "study"]
    # different slots (lunch vs early morning) and different session counts
    assert {b["start"] for b in slow_study} != {b["start"] for b in fast_study}
    assert len(fast_study) != len(slow_study) or slow_study[0]["start"] != fast_study[0]["start"]


def test_calendar_accepts_employee_id_and_404s(client):
    assert client.get("/api/calendar/EMP-012").json()["learner_id"] == "L-1012"
    assert client.get("/api/calendar/NOPE-1").status_code == 404


# ── progress ─────────────────────────────────────────────────────────────────

def test_progress_individual_consistent_with_roster(client):
    d = client.get("/api/progress/L-1001").json()
    assert d["certification"] == "AZ-204" and d["threshold"] == 0.70
    weeks = d["weeks"]
    assert len(weeks) >= 6
    assert weeks[-1]["practice_score"] == 0.78          # == practice_score_avg
    assert weeks[-1]["hours_studied_cumulative"] == 42  # == hours_studied
    hours = [w["hours_studied_cumulative"] for w in weeks]
    assert hours == sorted(hours)
    assert d["feedback"]
    assert client.get("/api/progress/L-9999").status_code == 404


def test_team_progress_aggregate_only_no_pii(client):
    for team in ["TEAM-A", "TEAM-B", "TEAM-C", "TEAM-D"]:
        r = client.get(f"/api/progress/team/{team}")
        assert r.status_code == 200
        assert not _PII.search(r.text), f"PII leaked in team progress for {team}"
        assert r.json()["pii_safe"] is True


def test_team_progress_k_anonymity_suppression(client):
    d = client.get("/api/progress/team/TEAM-A").json()
    # TEAM-A has one compliance learner -> that track must be suppressed
    compliance = next(t for t in d["by_track"] if t["track"] == "compliance")
    assert compliance["suppressed"] is True and "weeks" not in compliance
    technical = next(t for t in d["by_track"] if t["track"] == "technical")
    assert technical["n"] >= 3 and technical["weeks"]
    assert "compliance" in d["suppressed_tracks"]
    assert client.get("/api/progress/team/TEAM-X").status_code == 404


# ── shell ────────────────────────────────────────────────────────────────────

def test_index_and_presets_serve(client):
    assert client.get("/").status_code == 200
    d = client.get("/api/presets").json()
    assert len(d["presets"]) == 11
    assert sum(1 for p in d["presets"] if "ui" in p) == 2
    assert sum(1 for p in d["presets"] if p["label"].startswith("Red team")) == 2
    assert all("request" in p or "ui" in p for p in d["presets"])
