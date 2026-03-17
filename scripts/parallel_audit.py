#!/usr/bin/env python3
"""parallel_audit.py - Fire audit skills in parallel subagents.

Launches the FastAPI server, then concurrently executes 8 audit-relevant
skills against a project context summary.  Collects all results and
writes a consolidated JSON report to stdout / audit_report.json.

Usage:
    python scripts/parallel_audit.py [--base-url http://localhost:8000]
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)

# ── Audit skill IDs and their focused prompts ─────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Build a compact project context summary for the audit prompts
PROJECT_CONTEXT = """
Project: AuDHD Cognitive Swarm (audhd-agents)
Stack: Python 3.11+, FastAPI, Pydantic v2, 3 LLM providers (OpenAI, Google, Anthropic removed)
Skills: 51 skills across 10 capabilities (research, analyze, synthesize, generate, transform, evaluate, plan, orchestrate, audit, optimize)
Runtime: cognitive pipeline with energy-adaptive routing, sk_hooks, output validation
Deployment: GCP Cloud Run via GitHub Actions CI/CD
Recent changes:
  - Gemini 3.1 Pro Preview (G-PRO31) set as primary model across all skills
  - Frozen Pydantic schemas (frozen=True) on all request/response models
  - Strict JSON extraction from LLM markdown code blocks
  - Word boundary regex fix for trigger matching
  - 91 unit tests passing
Known incomplete items per CAPABILITIES.md:
  - API validation (live provider calls) - partially done
  - Runtime planner - implemented but CAPABILITIES.md not updated
  - Capability-aware routing - implemented but CAPABILITIES.md not updated
  - Skill-level capability tags - done but CAPABILITIES.md not updated
"""

AUDIT_SKILLS = {
    "engineering-code-reviewer": (
        f"Review the following project for code quality, maintainability, and patterns. "
        f"Identify the top 3 issues and recommend specific fixes.\n\n{PROJECT_CONTEXT}"
    ),
    "engineering-security-engineer": (
        f"Perform a security audit of the following project. Focus on API key handling, "
        f"input validation, injection risks, and authentication gaps.\n\n{PROJECT_CONTEXT}"
    ),
    "compliance-auditor": (
        f"Audit the following project for compliance with its own stated contracts "
        f"(PROFILE.md, AGENT.md). Check if documentation matches implementation.\n\n{PROJECT_CONTEXT}"
    ),
    "testing-accessibility-auditor": (
        f"Audit the following project for accessibility of its API design and documentation. "
        f"Check error messages, response formats, and developer experience.\n\n{PROJECT_CONTEXT}"
    ),
    "testing-reality-checker": (
        f"Reality-check the following project state. Validate assumptions about completeness, "
        f"identify gaps between claimed and actual status.\n\n{PROJECT_CONTEXT}"
    ),
    "engineering-software-architect": (
        f"Evaluate the architecture of the following project. Identify structural risks, "
        f"coupling issues, and recommend the next 3 architectural improvements.\n\n{PROJECT_CONTEXT}"
    ),
    "testing-api-tester": (
        f"Design a test plan for the /execute API endpoint of the following project. "
        f"Identify untested edge cases and missing integration tests.\n\n{PROJECT_CONTEXT}"
    ),
    "automation-governance": (
        f"Evaluate the automation governance of the following project. Check CI/CD pipelines, "
        f"deployment safety, and operational readiness.\n\n{PROJECT_CONTEXT}"
    ),
}


async def call_skill(client: httpx.AsyncClient, base_url: str, skill_id: str, prompt: str) -> dict:
    """Execute a single skill and return its result dict."""
    payload = {
        "skill_id": skill_id,
        "input_text": prompt,
        "options": {
            "cognitive_state": {
                "energy_level": "high",
                "attention_state": "focused",
                "session_context": "new",
            }
        },
    }
    t0 = time.monotonic()
    try:
        resp = await client.post(f"{base_url}/execute", json=payload, timeout=120.0)
        elapsed = time.monotonic() - t0
        if resp.status_code != 200:
            return {
                "skill_id": skill_id,
                "status": "error",
                "http_status": resp.status_code,
                "error": resp.text[:500],
                "latency_s": round(elapsed, 2),
            }
        data = resp.json()
        return {
            "skill_id": skill_id,
            "status": "ok",
            "provider": data.get("provider"),
            "model_used": data.get("model_used"),
            "output": data.get("output", {}),
            "latency_s": round(elapsed, 2),
        }
    except Exception as exc:
        elapsed = time.monotonic() - t0
        return {
            "skill_id": skill_id,
            "status": "exception",
            "error": str(exc),
            "latency_s": round(elapsed, 2),
        }


async def run_audit(base_url: str) -> dict:
    """Fire all audit skills concurrently and collect results."""
    print(f"\n{'='*60}")
    print(f"  PARALLEL AUDIT - {len(AUDIT_SKILLS)} skills firing concurrently")
    print(f"  Target: {base_url}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient() as client:
        # Fire all skills simultaneously
        tasks = [
            call_skill(client, base_url, skill_id, prompt)
            for skill_id, prompt in AUDIT_SKILLS.items()
        ]
        results = await asyncio.gather(*tasks)

    # Build summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = len(results) - ok_count
    total_latency = sum(r["latency_s"] for r in results)

    report = {
        "audit_summary": {
            "total_skills": len(results),
            "succeeded": ok_count,
            "failed": err_count,
            "wall_clock_s": round(max(r["latency_s"] for r in results), 2),
            "cumulative_latency_s": round(total_latency, 2),
        },
        "skill_results": results,
    }

    # Print summary
    print(f"\n{'='*60}")
    print(f"  AUDIT COMPLETE: {ok_count}/{len(results)} skills succeeded")
    print(f"  Wall clock: {report['audit_summary']['wall_clock_s']}s")
    print(f"  Cumulative: {report['audit_summary']['cumulative_latency_s']}s")
    print(f"{'='*60}\n")

    for r in results:
        icon = "OK" if r["status"] == "ok" else "FAIL"
        print(f"  [{icon}] {r['skill_id']} ({r['latency_s']}s)")
        if r["status"] == "ok":
            out = r.get("output", {})
            # Print first ~200 chars of raw output for quick scan
            raw = out.get("raw", str(out))[:200]
            if raw:
                print(f"        {raw}...")
        else:
            print(f"        Error: {r.get('error', 'unknown')[:200]}")
    print()

    return report


def main():
    parser = argparse.ArgumentParser(description="Run parallel audit skills")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Base URL of the running runtime server")
    parser.add_argument("--output", default="audit_report.json",
                        help="Output file for the full JSON report")
    parser.add_argument("--start-server", action="store_true",
                        help="Auto-start the uvicorn server before auditing")
    args = parser.parse_args()

    server_proc = None
    if args.start_server:
        print("Starting uvicorn server...")
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "runtime.app:app",
             "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(PROJECT_ROOT),
        )
        time.sleep(3)  # Give server time to start

    try:
        report = asyncio.run(run_audit(args.base_url))

        # Write full report
        out_path = PROJECT_ROOT / args.output
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Full report written to: {out_path}")

    finally:
        if server_proc:
            server_proc.terminate()
            server_proc.wait()
            print("Server stopped.")


if __name__ == "__main__":
    main()
