import httpx


def test_runs_loaded(ci_url):
    runs = httpx.get(f"{ci_url}/runs").json()
    assert {r["run_id"] for r in runs} >= {"r1001", "r1002", "r1003", "r1004", "r1005", "r1006"}


def test_failed_tests_have_locations(ci_url):
    tests = httpx.get(f"{ci_url}/runs/r1001/tests").json()
    assert tests and tests[0]["locations"][0]["file"] == "tests/test_units.py"


def test_install_failure_has_no_tests(ci_url):
    run = httpx.get(f"{ci_url}/runs/r1004").json()
    assert run["failed_stage"] == "install" and run["tests"]["ran"] is False


def test_diff_and_files(ci_url):
    diff = httpx.get(f"{ci_url}/runs/r1001/diff").json()
    assert "+    return (celsius + 32) * 9 / 5" in diff["diff"]
    f = httpx.get(f"{ci_url}/runs/r1001/files", params={"path": "telemetry/units.py"}).json()
    assert any("(celsius + 32)" in l["text"] for l in f["lines"])


def test_path_traversal_blocked(ci_url):
    assert httpx.get(f"{ci_url}/runs/r1001/files", params={"path": "../mock_ci/app.py"}).status_code == 400


def test_only_draft_pulls(ci_url):
    r = httpx.post(f"{ci_url}/pulls", json={"run_id": "r1001", "title": "t", "body": "b", "diff": "d", "draft": False})
    assert r.status_code == 403
