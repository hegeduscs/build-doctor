"""MCP szerződés-tesztek. A skeletonnal ezek egy része PIROS – akkor kész az MCP szerver, ha mind zöld.

  uv run pytest -m "not level2"     # csak az 1. szint
  uv run pytest                     # minden (2. szint: commitonkénti diff, titok-kitakarás, verify_patch)
"""
import asyncio
import json
from pathlib import Path

import pytest
from fastmcp import Client

READ_TOOLS = {"list_failed_runs", "get_ci_run", "get_failed_tests", "get_log_excerpt", "get_diff",
              "get_recent_commits", "read_file", "search_code", "get_test_history"}
WRITE_TOOLS = {"create_issue", "propose_patch"}
SANDBOX_TOOLS = {"verify_patch"}          # 2. szint: mellékhatás nélküli, de kódot futtat
CI_TOKEN = "ghp_FAKE7rK2capstone9Qw4TOKEN0000xYz31"   # a r1008 logjában szerepel

GOOD_R1001 = """--- a/telemetry/units.py
+++ b/telemetry/units.py
@@ -5,3 +5,3 @@
     \"\"\"Celsius -> Fahrenheit.\"\"\"
-    return (celsius + 32) * 9 / 5
+    return celsius * 9 / 5 + 32
"""


def _run(coro):
    return asyncio.run(coro)


async def _tools(srv):
    async with Client(srv.mcp) as c:
        return {t.name: t for t in await c.list_tools()}


async def _call(srv, name, args):
    async with Client(srv.mcp) as c:
        return await c.call_tool(name, args, raise_on_error=False)


def _ann(tool, key):
    a = tool.annotations
    snake = {"readOnlyHint": "read_only_hint", "destructiveHint": "destructive_hint"}[key]
    return getattr(a, snake, None) if a is not None else None


def test_all_tools_exposed(mcp_server):
    names = set(_run(_tools(mcp_server)))
    missing = (READ_TOOLS | WRITE_TOOLS) - names
    assert not missing, f"hiányzó toolok: {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(READ_TOOLS))
def test_read_tools_are_annotated_read_only(mcp_server, name):
    tools = _run(_tools(mcp_server))
    assert name in tools, f"{name} hiányzik"
    assert _ann(tools[name], "readOnlyHint") is True


@pytest.mark.parametrize("name", sorted(WRITE_TOOLS))
def test_write_tools_are_not_read_only(mcp_server, name):
    tools = _run(_tools(mcp_server))
    assert name in tools, f"{name} hiányzik"
    assert _ann(tools[name], "readOnlyHint") is False


def test_descriptions_are_real(mcp_server):
    for name, t in _run(_tools(mcp_server)).items():
        assert t.description and "TODO" not in t.description and len(t.description) > 40, f"{name}: gyenge leírás"


@pytest.mark.parametrize("name,args", [
    ("get_ci_run", {"run_id": "r1001"}),
    ("get_failed_tests", {"run_id": "r1001"}),
    ("get_log_excerpt", {"run_id": "r1004", "pattern": "ERROR"}),
    ("get_diff", {"run_id": "r1001"}),
    ("get_recent_commits", {"run_id": "r1001"}),
    ("read_file", {"run_id": "r1001", "path": "telemetry/units.py"}),
    ("search_code", {"run_id": "r1001", "query": "def c_to_f"}),
    ("get_test_history", {"test_id": "tests/test_debounce.py::test_debounce_ignores_short_glitch_real_clock"}),
])
def test_read_tools_work(mcp_server, name, args):
    res = _run(_call(mcp_server, name, args))
    assert not res.is_error, res.content


def test_unknown_run_is_a_clean_error(mcp_server):
    assert _run(_call(mcp_server, "get_ci_run", {"run_id": "nope"})).is_error


def test_write_is_dry_run_by_default(mcp_server):
    res = _run(_call(mcp_server, "create_issue", {"run_id": "r1001", "title": "t", "body": "b"}))
    assert not res.is_error and res.data.get("dry_run") is True


def test_secret_in_issue_body_rejected(mcp_server):
    res = _run(_call(mcp_server, "create_issue", {"run_id": "r1001", "title": "t", "body": "API_KEY=abc123"}))
    assert res.is_error


def test_patch_deleting_tests_rejected(mcp_server):
    diff = "diff --git a/tests/test_alarms.py b/tests/test_alarms.py\ndeleted file mode 100644\n"
    res = _run(_call(mcp_server, "propose_patch", {"run_id": "r1006", "title": "t", "body": "b", "diff": diff}))
    assert res.is_error


def test_every_call_is_audited(mcp_server):
    _run(_call(mcp_server, "get_ci_run", {"run_id": "r1002"}))
    lines = [json.loads(l) for l in Path(mcp_server.AUDIT_LOG).read_text(encoding="utf-8").splitlines()]
    assert any(l["tool"] == "get_ci_run" and l["args"].get("run_id") == "r1002" for l in lines)


# ----------------------------------------------------------------------------- 2. szint
# Csak az 1. szint:  uv run pytest -m "not level2"
pytestmark_level2 = pytest.mark.level2


@pytestmark_level2
def test_diff_of_an_earlier_commit(mcp_server):
    commits = _run(_call(mcp_server, "get_recent_commits", {"run_id": "r1007"})).data
    older = commits[1]["sha"]
    res = _run(_call(mcp_server, "get_diff", {"run_id": "r1007", "commit": older[:7]}))
    assert not res.is_error and "telemetry/parser.py" in json.dumps(res.data)


@pytestmark_level2
@pytest.mark.parametrize("name,args", [
    ("get_log_excerpt", {"run_id": "r1008", "pattern": "token"}),
    ("get_failed_tests", {"run_id": "r1008"}),
])
def test_secrets_are_masked_in_read_tools(mcp_server, name, args):
    res = _run(_call(mcp_server, name, args))
    assert not res.is_error
    assert CI_TOKEN not in json.dumps(res.data, ensure_ascii=False), "a CI token kijutott a tool válaszában"


@pytestmark_level2
def test_masking_keeps_source_code_intact(mcp_server):
    res = _run(_call(mcp_server, "read_file", {"run_id": "r1008", "path": "telemetry/config.py"}))
    assert "token={os.environ.get" in json.dumps(res.data, ensure_ascii=False)


@pytestmark_level2
def test_verify_patch_accepts_a_real_fix(mcp_server):
    res = _run(_call(mcp_server, "verify_patch", {"run_id": "r1001", "patch": GOOD_R1001}))
    assert not res.is_error and res.data["tests_ok"] is True


@pytestmark_level2
def test_verify_patch_rejects_a_wrong_fix(mcp_server):
    bad = GOOD_R1001.replace("* 9 / 5 + 32", "* 9 / 5")
    res = _run(_call(mcp_server, "verify_patch", {"run_id": "r1001", "patch": bad}))
    assert not res.is_error and res.data["tests_ok"] is False


@pytestmark_level2
def test_verify_patch_flags_test_edits(mcp_server):
    patch = ("--- a/tests/test_units.py\n+++ b/tests/test_units.py\n@@ -13,1 +13,1 @@\n"
             "-        assert f_to_c(c_to_f(c)) == c\n+        assert f_to_c(c_to_f(c)) == pytest.approx(c)\n")
    res = _run(_call(mcp_server, "verify_patch", {"run_id": "r1009", "patch": patch}))
    assert not res.is_error and res.data["tests_ok"] is False and res.data["violations"]


@pytestmark_level2
def test_propose_patch_requires_a_verified_fix(mcp_server):
    bad = GOOD_R1001.replace("* 9 / 5 + 32", "* 9 / 5")
    res = _run(_call(mcp_server, "propose_patch", {"run_id": "r1001", "title": "t", "body": "b", "diff": bad}))
    assert res.is_error
    ok = _run(_call(mcp_server, "propose_patch", {"run_id": "r1001", "title": "t", "body": "b", "diff": GOOD_R1001}))
    assert not ok.is_error and ok.data.get("dry_run") is True


@pytestmark_level2
def test_sandbox_tool_is_side_effect_free(mcp_server):
    tools = _run(_tools(mcp_server))
    assert "verify_patch" in tools, "verify_patch hiányzik"
    assert _ann(tools["verify_patch"], "readOnlyHint") is True
