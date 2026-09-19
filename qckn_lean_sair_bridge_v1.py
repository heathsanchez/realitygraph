from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MATHGRAPH = Path(os.environ["MATHGRAPH_REPO"]).resolve()
SAIR = Path(os.environ["SAIR_REPO"]).resolve()
ARENA = Path(os.environ["ARENA_REPO"]).resolve()
LEAN4EXPORT_BIN = Path(os.environ["LEAN4EXPORT_BIN"]).resolve()
OUT = Path(os.environ.get("QCKN_LEAN_SAIR_BRIDGE_OUT", ROOT / "qckn-lean-sair-bridge-results")).resolve()
TARGET = int(os.environ.get("QCKN_LEAN_SAIR_TARGET", "6"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(cmd, *, cwd=None, env=None, timeout=300, check=False):
    start = time.perf_counter()
    proc = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed {cmd}:\nSTDOUT\n{proc.stdout[-4000:]}\nSTDERR\n{proc.stderr[-4000:]}"
        )
    return proc, elapsed


def _git_head(repo: Path) -> str:
    p, _ = _run(["git", "rev-parse", "HEAD"], cwd=repo, check=True)
    return p.stdout.strip()


def _load_mathgraph_modules():
    src = MATHGRAPH / "competitions" / "sair_stage2" / "src"
    if str(MATHGRAPH) not in sys.path:
        sys.path.insert(0, str(MATHGRAPH))
    from competitions.sair_stage2.src.equation_core import parse_equation
    from competitions.sair_stage2.src.false_constructors import prove_false
    from competitions.sair_stage2.src.lean_false_emitter import (
        build_false_certificate,
        emit_false_judge_call,
    )
    return parse_equation, prove_false, build_false_certificate, emit_false_judge_call


def _load_sair_verify():
    if str(SAIR) not in sys.path:
        sys.path.insert(0, str(SAIR))
    from judge.verify import JudgeConfig, verify_answer, _make_lean_env, LEAN_LINTER_FLAGS
    return JudgeConfig, verify_answer, _make_lean_env, LEAN_LINTER_FLAGS


def _problem_sets():
    for name in ("sample_20.json", "sample_200.json"):
        path = SAIR / "examples" / "problems" / name
        if path.exists():
            yield name, json.loads(path.read_text(encoding="utf-8"))


def _official_accept(problem, raw_answer, JudgeConfig, verify_answer):
    config = JudgeConfig(
        lean_bin=Path(shutil.which("lean") or "lean"),
        lake_bin=Path(shutil.which("lake") or "lake"),
        artifact_dir=OUT / "official-artifacts",
        lean_timeout_seconds=180,
    )
    start = time.perf_counter()
    result = verify_answer(problem, raw_answer, config=config)
    elapsed = time.perf_counter() - start
    return config, result, elapsed


def _compile_problem_olean(artifact_dir: Path, config, _make_lean_env, linter_flags):
    problem = artifact_dir / "Problem.lean"
    olean = artifact_dir / "Problem.olean"
    env = _make_lean_env(config, [str(artifact_dir)])
    proc, elapsed = _run(
        [
            config.lean_bin,
            f"--root={artifact_dir}",
            *linter_flags,
            "-o",
            olean,
            problem,
        ],
        cwd=artifact_dir,
        env=env,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Problem.olean compile failed: {proc.stderr[-4000:]} {proc.stdout[-4000:]}"
        )
    return env, elapsed


def _checked_decl(problem_source: str) -> str:
    m = re.search(r"theorem\s+(_judge_checked_[0-9a-f]+)\s*:", problem_source)
    if not m:
        raise RuntimeError("judge-owned checked theorem name not found")
    return m.group(1)


def _export_problem(artifact_dir: Path, env: dict[str, str], checked_decl: str, dest: Path):
    # Preserve the judge's artifact directory at the front of LEAN_PATH so
    # lean4export sees the exact JudgeProblem/Submission/Problem oleans.
    proc, elapsed = _run(
        [LEAN4EXPORT_BIN, "Problem", "--", checked_decl],
        cwd=SAIR,
        env=env,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"lean4export failed: {proc.stderr[-4000:]} {proc.stdout[-4000:]}"
        )
    dest.write_text(proc.stdout, encoding="utf-8")
    if not dest.read_text(encoding="utf-8").strip():
        raise RuntimeError("lean4export produced empty export")
    return elapsed


def _mathgraph_check(export_path: Path):
    main = ARENA / "checkers" / "mathgraph" / "main.mjs"
    proc, elapsed = _run(["node", main, export_path], cwd=ARENA, timeout=180)
    status = {0: "ACCEPT", 1: "REJECT", 2: "DECLINE"}.get(proc.returncode, "ERROR")
    return status, elapsed, proc


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    exports = OUT / "exports"
    exports.mkdir(parents=True, exist_ok=True)

    parse_equation, prove_false, build_false_certificate, emit_false_judge_call = (
        _load_mathgraph_modules()
    )
    JudgeConfig, verify_answer, _make_lean_env, linter_flags = _load_sair_verify()

    records = []
    searched = 0

    for set_name, problems in _problem_sets():
        for problem in problems:
            if len(records) >= TARGET:
                break
            searched += 1
            try:
                eq1 = parse_equation(problem["equation1"])
                eq2 = parse_equation(problem["equation2"])
                false = prove_false(eq1, eq2)
            except Exception:
                false = None
            if not false:
                continue

            table = false.get("certificate", {}).get("table")
            if table is None:
                continue
            cert = build_false_certificate(
                problem["eq1_id"],
                problem["eq2_id"],
                problem["equation1"],
                problem["equation2"],
                table,
            )
            call = emit_false_judge_call(cert)
            if not call:
                continue

            raw_answer = json.dumps(
                {"verdict": call["verdict"], "code": call["code"]},
                sort_keys=True,
            )
            config, official, official_seconds = _official_accept(
                problem, raw_answer, JudgeConfig, verify_answer
            )
            row = {
                "problem_id": problem["id"],
                "set": set_name,
                "official_status": official["status"],
                "official_error_code": official["error_code"],
                "official_seconds": official_seconds,
                "certificate_family": getattr(cert, "family", None),
                "certificate_n": int(getattr(cert, "n", 0)),
                "lean_code_bytes": len(call["code"].encode("utf-8")),
            }
            if official["status"] != "accepted":
                row["mathgraph_status"] = "NOT_RUN"
                records.append(row)
                continue

            artifact_dir = Path(official["artifact_path"])
            source = (artifact_dir / "Problem.lean").read_text(encoding="utf-8")
            checked_decl = _checked_decl(source)
            env, compile_seconds = _compile_problem_olean(
                artifact_dir, config, _make_lean_env, linter_flags
            )
            export_path = exports / f"{problem['id']}.ndjson"
            export_seconds = _export_problem(
                artifact_dir, env, checked_decl, export_path
            )
            mg_status, mg_seconds, mg_proc = _mathgraph_check(export_path)
            row.update(
                checked_decl=checked_decl,
                problem_compile_seconds=compile_seconds,
                export_seconds=export_seconds,
                export_sha256=_sha(export_path),
                export_bytes=export_path.stat().st_size,
                mathgraph_status=mg_status,
                mathgraph_seconds=mg_seconds,
                mathgraph_stderr=mg_proc.stderr[-1000:],
            )
            records.append(row)

        if len(records) >= TARGET:
            break

    accepted = [r for r in records if r["official_status"] == "accepted"]
    mg_accept = [r for r in accepted if r.get("mathgraph_status") == "ACCEPT"]
    mg_decline = [r for r in accepted if r.get("mathgraph_status") == "DECLINE"]
    mg_reject = [r for r in accepted if r.get("mathgraph_status") == "REJECT"]
    mg_error = [r for r in accepted if r.get("mathgraph_status") == "ERROR"]

    coverage = len(mg_accept) / len(accepted) if accepted else 0.0
    gates = {
        "PINNED_MATHGRAPH": _git_head(MATHGRAPH)
        == "e80fed62b6e58d2f4b62e2ceb012646c60dd1e28",
        "PINNED_SAIR": _git_head(SAIR)
        == "817a4653bf762584931d49c6714c9fcfab7df66a",
        "PINNED_ARENA_CHECKER": _git_head(ARENA)
        == "416cfb268ffeeda2d782120d169df1e1567d04d5",
        "OFFICIAL_ACCEPTED_NONTRIVIAL_CORPUS": len(accepted) >= 3,
        "NO_MATHGRAPH_FALSE_REJECTION": len(mg_reject) == 0,
        "NO_MATHGRAPH_RUNTIME_ERROR": len(mg_error) == 0,
        # This is a compatibility threshold only. It does not yet authorize
        # scheduler repricing because qualification still pays Lean export cost.
        "MATHGRAPH_ACCEPTS_AT_LEAST_ONE_OFFICIAL_PROOF": len(mg_accept) >= 1,
    }

    result = {
        "schema": "qckn-real-lean-sair-bridge-v1",
        "passed": all(gates.values()),
        "searched_problems": searched,
        "target_corpus": TARGET,
        "official_accepted": len(accepted),
        "mathgraph_accept": len(mg_accept),
        "mathgraph_decline": len(mg_decline),
        "mathgraph_reject": len(mg_reject),
        "mathgraph_error": len(mg_error),
        "mathgraph_coverage": coverage,
        "gates": gates,
        "records": records,
        "claim_boundary": (
            "This qualifies only a real shared proof-object compatibility boundary: "
            "MathGraph's independent Lean checker is tested on judge-owned theorem exports "
            "from officially accepted SAIR FALSE certificates. It does NOT yet establish "
            "a cost-saving Lean->SAIR bridge, because producing the export still uses Lean. "
            "Scheduler repricing remains forbidden until a destination acquisition cost is "
            "actually removed or an optimization transfers back to an external Arena workload."
        ),
    }
    (OUT / "result.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
