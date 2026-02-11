import importlib.util
import pathlib
import copy
import sys

from fastapi.testclient import TestClient


# Load app module from src/app.py
ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "src" / "app.py"
spec = importlib.util.spec_from_file_location("app", str(APP_PATH))
app_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_mod)

app = app_mod.app
activities = app_mod.activities


import pytest


@pytest.fixture(autouse=True)
def isolate_activities():
    # Make a deep copy and restore after each test to avoid cross-test pollution
    snapshot = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(snapshot)


def test_get_activities():
    client = TestClient(app)
    r = client.get("/activities")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    # Check a known activity exists
    assert "Soccer Team" in data


def test_signup_and_unregister_flow():
    client = TestClient(app)
    activity_name = "Chess Club"
    test_email = "tester@example.com"

    # Ensure email not already present
    assert test_email not in activities[activity_name]["participants"]

    # Signup
    r = client.post(f"/activities/{activity_name}/signup", params={"email": test_email})
    assert r.status_code == 200
    assert test_email in activities[activity_name]["participants"]

    # Unregister
    r = client.delete(f"/activities/{activity_name}/signup", params={"email": test_email})
    assert r.status_code == 200
    assert test_email not in activities[activity_name]["participants"]


def test_duplicate_signup_returns_400():
    client = TestClient(app)
    activity_name = "Art Club"
    test_email = "dup@example.com"

    # First signup OK
    r = client.post(f"/activities/{activity_name}/signup", params={"email": test_email})
    assert r.status_code == 200

    # Second signup should fail with 400
    r = client.post(f"/activities/{activity_name}/signup", params={"email": test_email})
    assert r.status_code == 400


def test_unregister_nonexistent_returns_404():
    client = TestClient(app)
    activity_name = "Drama Club"
    test_email = "notfound@example.com"

    r = client.delete(f"/activities/{activity_name}/signup", params={"email": test_email})
    assert r.status_code == 404


def test_capacity_limit_blocks_extra_signup():
    client = TestClient(app)
    temp_name = "Temp Limited"
    # create temporary activity with capacity 1
    activities[temp_name] = {
        "description": "Temp",
        "schedule": "Now",
        "max_participants": 1,
        "participants": []
    }

    r1 = client.post(f"/activities/{temp_name}/signup", params={"email": "a@example.com"})
    assert r1.status_code == 200

    r2 = client.post(f"/activities/{temp_name}/signup", params={"email": "b@example.com"})
    assert r2.status_code == 400
