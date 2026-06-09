"""Shared fixtures. Force the deterministic offline backends so tests never need
cloud credentials and are fully reproducible — even when a local ``.env`` points
at live Azure resources. We pin the model to the offline stub, blank the Azure
Search / Foundry endpoints, and use the Microsoft Learn offline cache, so the run
is hermetic and matches CI (which has no ``.env``). Set before any certmesh import
so the cached ``load_config()`` observes them."""

import os

os.environ["CERTMESH_MODEL_BACKEND"] = "offline"
os.environ["CERTMESH_MCP_ENABLED"] = "false"           # use the Learn offline cache
os.environ["AZURE_SEARCH_ENDPOINT"] = ""               # ignore any live creds in .env
os.environ["AZURE_SEARCH_API_KEY"] = ""
os.environ["AZURE_AI_PROJECT_ENDPOINT"] = ""
os.environ["AZURE_AI_API_KEY"] = ""

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
