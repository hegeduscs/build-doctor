"""Mock CI szerver a Build Doctor capstone-hoz.

A forgatókönyveket (scenarios/<run_id>/) tölti be, és egy egyszerű, GitHub Actions-szerű REST API-t ad.
A célrepó (target_repo/) az alapállapot; minden futás = alapállapot + a forgatókönyv overlay-e.

Indítás:  uvicorn mock_ci.app:app --port 9000
Környezeti változók:
  SCENARIO_DIRS  pontosvesszővel elválasztott mappák (alap: scenarios;hidden)
  BASE_REPO      a célrepó mappája (alap: target_repo)
  DATA_DIR       ide kerülnek a létrehozott issue-k és PR-ek (alap: .mockci-data)
"""
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
BASE_REPO = Path(os.environ.get("BASE_REPO", ROOT / "target_repo"))
SCENARIO_DIRS = [Path(p.strip()) for p in os.environ.get("SCENARIO_DIRS", f"{ROOT / 'scenarios'};{ROOT / 'hidden'}").split(";")
                 if p.strip()]
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / ".mockci-data"))
SKIP_PARTS = {"__pycache__", ".pytest_cache"}

app = FastAPI(title="Mock CI – Build Doctor capstone", version="1.0")


# ----------------------------------------------------------------------------- betöltés
def _load_runs() -> dict:
    runs = {}
    for d in SCENARIO_DIRS:
        if not d.exists():
            continue
        for sdir in sorted(p for p in d.iterdir() if (p / "scenario.yaml").exists()):
            meta = yaml.safe_load((sdir / "scenario.yaml").read_text(encoding="utf-8"))
            meta["_dir"] = sdir
            runs[meta["run_id"]] = meta
    return runs


RUNS = _load_runs()


def _run(run_id: str) -> dict:
    if run_id not in RUNS:
        raise HTTPException(404, f"unknown run_id: {run_id}")
    return RUNS[run_id]


def _overlay(run: dict) -> Path:
    return run["_dir"] / "overlay"


def _file_text(run: dict, path: str) -> str | None:
    path = path.lstrip("/").replace("\\", "/")
    if ".." in Path(path).parts:
        raise HTTPException(400, "path traversal is not allowed")
    for base in (_overlay(run), BASE_REPO):
        p = base / path
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None


def _tree(run: dict) -> list[str]:
    files = set()
    for base in (BASE_REPO, _overlay(run)):
        if base.exists():
            for p in base.rglob("*"):
                if p.is_file() and not SKIP_PARTS & set(p.parts):
                    files.add(p.relative_to(base).as_posix())
    return sorted(files)


_LOC = re.compile(r"^((?:tests|telemetry|config)/[\w/.-]+\.py):(\d+):", re.M)


def _parse_junit(run: dict) -> list[dict]:
    jf = run["_dir"] / "junit.xml"
    if not jf.exists():
        return []
    out = []
    for tc in ET.parse(jf).getroot().iter("testcase"):
        res, node = "passed", None
        for kind in ("failure", "error", "skipped"):
            node = tc.find(kind)
            if node is not None:
                res = {"failure": "failed", "error": "error", "skipped": "skipped"}[kind]
                break
        cls = tc.get("classname", "")
        file = cls.replace(".", "/") + ".py" if cls else ""
        item = {"test_id": f"{file}::{tc.get('name')}", "file": file, "name": tc.get("name"), "result": res,
                "time_s": float(tc.get("time", 0) or 0)}
        if node is not None and res in ("failed", "error"):
            text = (node.text or "").strip()
            locs = _LOC.findall(text)
            item["message"] = (node.get("message") or "")[:500]
            item["locations"] = [{"file": f, "line": int(l)} for f, l in locs][-4:]
            item["traceback"] = "\n".join(text.splitlines()[-40:])
        out.append(item)
    return out


def _history() -> dict:
    hist: dict[str, list] = {}
    for rid, run in RUNS.items():
        for t in _parse_junit(run):
            hist.setdefault(t["test_id"], []).append({"run_id": rid, "result": t["result"]})
        for tid, entries in (run.get("test_history") or {}).items():
            hist.setdefault(tid, []).extend(entries)
    for v in hist.values():
        v.sort(key=lambda e: e["run_id"])
    return hist


# ----------------------------------------------------------------------------- API
@app.get("/health")
def health():
    return {"ok": True, "runs": len(RUNS)}


@app.get("/runs")
def list_runs(status: str | None = None, limit: int = 20):
    rows = [{k: v for k, v in r.items() if k in ("run_id", "repo", "branch", "commit", "status", "failed_stage", "created_at")}
            for r in RUNS.values() if not status or r["status"] == status]
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows[:limit]


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    r = _run(run_id)
    tests = _parse_junit(r)
    return {
        **{k: v for k, v in r.items() if not k.startswith("_") and k not in ("commits", "test_history")},
        "head_commit": r["commits"][0],
        "tests": {"total": len(tests), "failed": sum(t["result"] in ("failed", "error") for t in tests),
                  "ran": bool(tests)},
    }


@app.get("/runs/{run_id}/log")
def get_log(run_id: str, start: int = 1, max_lines: int = Query(200, le=1000), pattern: str | None = None,
            context: int = 3):
    lines = (_run(run_id)["_dir"] / "log.txt").read_text(encoding="utf-8").splitlines()
    total = len(lines)
    if pattern:
        rx = re.compile(pattern, re.I)
        keep = set()
        for i, ln in enumerate(lines):
            if rx.search(ln):
                keep.update(range(max(0, i - context), min(total, i + context + 1)))
        sel = sorted(keep)[:max_lines]
        return {"total_lines": total, "lines": [{"n": i + 1, "text": lines[i]} for i in sel]}
    sel = range(max(0, start - 1), min(total, start - 1 + max_lines))
    return {"total_lines": total, "lines": [{"n": i + 1, "text": lines[i]} for i in sel]}


@app.get("/runs/{run_id}/tests")
def get_tests(run_id: str, only_failed: bool = True):
    tests = _parse_junit(_run(run_id))
    return [t for t in tests if not only_failed or t["result"] in ("failed", "error")]


@app.get("/runs/{run_id}/commits")
def get_commits(run_id: str):
    return _run(run_id)["commits"]


@app.get("/runs/{run_id}/diff")
def get_diff(run_id: str, commit: str | None = None):
    """Egy commit diffje (alap: a fejcommit). Több commitos futásnál a hibát egy korábbi commit is behozhatta."""
    r = _run(run_id)
    c = next((c for c in r["commits"] if c["sha"].startswith(commit)), None) if commit else r["commits"][0]
    if c is None:
        raise HTTPException(404, f"no such commit in this run: {commit}")
    stored = r["_dir"] / "diffs" / f"{c['sha']}.diff"
    if stored.exists():
        return {"commit": c["sha"], "message": c["message"].splitlines()[0], "files": c["files"],
                "diff": stored.read_text(encoding="utf-8")}
    chunks = []
    for path in c["files"]:
        old = (BASE_REPO / path).read_text(encoding="utf-8").splitlines(keepends=True) if (BASE_REPO / path).exists() else []
        new_p = _overlay(r) / path
        new = new_p.read_text(encoding="utf-8").splitlines(keepends=True) if new_p.exists() else []
        chunks.append("".join(difflib.unified_diff(old, new, f"a/{path}", f"b/{path}")))
    return {"commit": c["sha"], "message": c["message"].splitlines()[0], "files": c["files"], "diff": "".join(chunks)}


@app.get("/runs/{run_id}/tree")
def get_tree(run_id: str):
    return _tree(_run(run_id))


@app.get("/runs/{run_id}/files")
def get_file(run_id: str, path: str, start_line: int = 1, end_line: int | None = None):
    txt = _file_text(_run(run_id), path)
    if txt is None:
        raise HTTPException(404, f"file not found at this run: {path}")
    lines = txt.splitlines()
    end = min(len(lines), end_line or len(lines))
    return {"path": path, "total_lines": len(lines),
            "lines": [{"n": i + 1, "text": lines[i]} for i in range(max(0, start_line - 1), end)]}


@app.get("/runs/{run_id}/search")
def search(run_id: str, q: str, max_results: int = Query(30, le=200)):
    r = _run(run_id)
    hits = []
    for path in _tree(r):
        txt = _file_text(r, path)
        if txt is None:
            continue
        for i, ln in enumerate(txt.splitlines(), 1):
            if q.lower() in ln.lower():
                hits.append({"path": path, "line": i, "text": ln.strip()[:200]})
                if len(hits) >= max_results:
                    return hits
    return hits


@app.get("/tests/history")
def test_history(test_id: str):
    return {"test_id": test_id, "history": _history().get(test_id, [])}


# ----------------------------------------------------------------------------- javítás ellenőrzése (sandbox)
class VerifyIn(BaseModel):
    patch: str  # unified diff, a/ és b/ előtaggal (git diff formátum)


_SKIP_RX = re.compile(r"^\+.*(pytest\.mark\.(skip|xfail)|pytest\.skip\(|@unittest\.skip)", re.M)


def _sandbox(run: dict, dst: Path) -> None:
    shutil.copytree(BASE_REPO, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    ov = _overlay(run)
    if ov.exists():
        shutil.copytree(ov, dst, dirs_exist_ok=True)


def _pytest(work: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TELEMETRY_", "OPENAI", "AZURE"))}
    junit = work / "_junit.xml"
    try:
        res = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
                              f"--junitxml={junit}"], cwd=work, env=env, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"ran": False, "error": "a tesztfutás 90 s után leállt"}
    passed, failed = 0, []
    if junit.exists():
        for tc in ET.parse(junit).getroot().iter("testcase"):
            cls = tc.get("classname", "").replace(".", "/") + ".py"
            if tc.find("failure") is not None or tc.find("error") is not None:
                failed.append(f"{cls}::{tc.get('name')}")
            elif tc.find("skipped") is None:
                passed += 1
    tail = (res.stdout + res.stderr).strip().splitlines()[-25:]
    return {"ran": True, "passed": passed, "failed": len(failed), "failed_tests": failed, "tail": "\n".join(tail)}


def _apply_loose(work: Path, patch: str) -> str | None:
    """Tartalék alkalmazás, ha a git apply elutasítja (pl. rossz sorszám vagy aszimmetrikus kontextus az LLM által
    írt diffben): hunkonként a régi blokkot (kontextus + törölt sorok) szó szerint megkeresi és kicseréli.
    Hibaüzenetet ad vissza, vagy None-t, ha sikerült."""
    files = re.split(r"^--- .*\n(?=\+\+\+ )", patch, flags=re.M)
    for chunk in files:
        m = re.match(r"\+\+\+ b/(\S+)\n", chunk)
        if not m:
            continue
        path = work / m.group(1)
        if not path.is_file():
            return f"nincs ilyen fájl: {m.group(1)}"
        text = path.read_text(encoding="utf-8")
        for hunk in re.split(r"^@@[^\n]*@@[^\n]*\n", chunk[m.end():], flags=re.M)[1:]:
            old, new = [], []
            for line in hunk.splitlines():
                if line.startswith("\\"):
                    continue
                tag, body = (line[:1], line[1:]) if line else (" ", "")
                if tag in (" ", "-"):
                    old.append(body)
                if tag in (" ", "+"):
                    new.append(body)
            old_s, new_s = "\n".join(old) + "\n", "\n".join(new) + "\n"
            if text.count(old_s) != 1:
                return f"{m.group(1)}: a hunk régi sorai {'nem' if not text.count(old_s) else 'többször'} találhatók a fájlban"
            text = text.replace(old_s, new_s)
        path.write_text(text, encoding="utf-8")
    return None


_BASELINE_TOTAL: dict[str, int] = {}


@app.post("/runs/{run_id}/verify")
def verify_patch(run_id: str, body: VerifyIn):
    """A javítás kipróbálása: a futás állapota + a patch egy eldobható másolaton, majd pytest. Mellékhatása nincs.

    tests_ok csak akkor igaz, ha minden teszt zöld, és nem kevesebb teszt futott, mint a javítás nélkül
    (teszt törlése / skip nem "javítás"). A telepítési hibákat (requirements) a sandbox nem tudja ellenőrizni.
    """
    run = _run(run_id)
    if run.get("failed_stage") == "install":
        return {"applied": False, "ran": False,
                "note": "telepítési hiba: a sandbox nem telepít csomagot (nincs hálózat) – a függőség-javítást nem tudja ellenőrizni"}
    touched = re.findall(r"^\+\+\+ b/(\S+)", body.patch, re.M)
    if not touched:
        raise HTTPException(400, "a patch nem unified diff (hiányzik a '+++ b/<fájl>' sor)")
    violations = []
    if any(p.startswith("tests/") for p in touched):
        violations.append("tesztfájlt módosít: " + ", ".join(p for p in touched if p.startswith("tests/")))
    if _SKIP_RX.search(body.patch):
        violations.append("tesztet kapcsol ki (skip/xfail)")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        if run_id not in _BASELINE_TOTAL:
            _sandbox(run, work)
            base = _pytest(work)
            _BASELINE_TOTAL[run_id] = base.get("passed", 0) + base.get("failed", 0)
            shutil.rmtree(work)
        _sandbox(run, work)
        patch = body.patch if body.patch.endswith("\n") else body.patch + "\n"
        try:
            ap = subprocess.run(["git", "apply", "--recount", "--whitespace=nowarn", "-"], cwd=work, input=patch,
                                capture_output=True, text=True)
            git_err = ap.stderr.strip()[-600:] if ap.returncode else None
        except FileNotFoundError:            # nincs git a gépen: csak a szó szerinti hunk-csere
            git_err = "git nem található"
        if git_err is not None:
            loose_err = _apply_loose(work, patch)
            if loose_err:
                return {"applied": False, "ran": False, "files": touched, "violations": violations,
                        "error": (git_err + "\n" + loose_err).strip()}
        result = _pytest(work)
    total = result.get("passed", 0) + result.get("failed", 0)
    result.update(applied=True, files=touched, violations=violations, tests_before=_BASELINE_TOTAL[run_id],
                  tests_ok=bool(result.get("ran")) and result.get("failed") == 0 and total >= _BASELINE_TOTAL[run_id]
                  and not violations)
    return result


# ----------------------------------------------------------------------------- írás (mellékhatás)
class IssueIn(BaseModel):
    run_id: str
    title: str
    body: str
    labels: list[str] = []


class PullIn(BaseModel):
    run_id: str
    title: str
    body: str
    diff: str
    draft: bool = True


def _append(name: str, obj: dict) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    f = DATA_DIR / f"{name}.jsonl"
    n = sum(1 for _ in f.open(encoding="utf-8")) + 1 if f.exists() else 1
    obj = {"id": n, "created_at": datetime.now(timezone.utc).isoformat(), **obj}
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return obj


def _read(name: str) -> list[dict]:
    f = DATA_DIR / f"{name}.jsonl"
    return [json.loads(l) for l in f.open(encoding="utf-8")] if f.exists() else []


@app.post("/issues")
def create_issue(issue: IssueIn):
    _run(issue.run_id)
    obj = _append("issues", issue.model_dump())
    return {"id": obj["id"], "url": f"http://mock-ci/issues/{obj['id']}"}


@app.get("/issues")
def list_issues():
    return _read("issues")


@app.post("/pulls")
def create_pull(pr: PullIn):
    _run(pr.run_id)
    if not pr.draft:
        raise HTTPException(403, "only draft pull requests are allowed")
    obj = _append("pulls", pr.model_dump())
    return {"id": obj["id"], "url": f"http://mock-ci/pulls/{obj['id']}", "draft": True}


@app.get("/pulls")
def list_pulls():
    return _read("pulls")
