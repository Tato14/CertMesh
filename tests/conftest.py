"""Shared fixtures. Force the deterministic offline backend so tests never need
cloud credentials and are fully reproducible."""

import os

os.environ.setdefault("CERTMESH_MODEL_BACKEND", "offline")

import pytest

from certmesh.iq.fabric_iq import get_fabric_iq
from certmesh.iq.foundry_iq import get_foundry_iq
from certmesh.iq.work_iq import get_work_iq
from certmesh.orchestrator import get_orchestrator


@pytest.fixture(scope="session")
def orch():
    return get_orchestrator()


@pytest.fixture(scope="session")
def fabric():
    return get_fabric_iq()


@pytest.fixture(scope="session")
def foundry():
    return get_foundry_iq()


@pytest.fixture(scope="session")
def work():
    return get_work_iq()
