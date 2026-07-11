"""
End-to-end evaluation runner. Sends each golden question to the live API
and scores the answer with the LLM judge.

Usage (from repo root):
  # First get a JWT token:
  TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \\
    -H 'Content-Type: application/json' \\
    -d '{"email":"admin@company-brain.local","password":"<password>"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  # Run all questions:
  cd backend && python -m eval.run_eval --token "$TOKEN"

  # Run only fact + decision groups:
  python -m eval.run_eval --token "$TOKEN" --groups fact decision

  # Compare hybrid vs vector-only (set GRAPH_ENABLED in .env between runs):
  python -m eval.run_eval --token "$TOKEN" --out eval_hybrid.json
  # then set GRAPH_ENABLED=false, restart backend, then:
  python -m eval.run_eval --token "$TOKEN" --out eval_vector.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Any

import httpx

from eval.golden_set import load_golden_set
from eval.metrics import llm_judge


async def _query(
    client: httpx.AsyncClient,
    base_url: str,
    question: str,
    token: str,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{base_url}/api/query/",
            json={"question": question},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}", "latency_ms": elapsed}
        data = resp.json()
        data.setdefault("latency_ms", elapsed)
        return data
    except Exception as exc:
        return {"error": str(exc), "latency_ms": 0}


def _mode_matches(actual: str, expected: str) -> bool:
    """Flexible mode match: 'hybrid' matches 'hybrid' or 'graph'."""
    if actual == expected:
        return True
    if expected in ("hybrid", "graph") and actual in ("hybrid", "graph"):
        return True
    return False


async def evaluate(
    base_url: str,
    token: str,
    groups: list[str] | None,
) -> dict[str, Any]:
    golden = load_golden_set()
    if groups:
        golden = [q for q in golden if q.get("group") in groups]

    all_results: list[dict] = []
    llm_scores: list[float] = []
    mode_hits = 0
    total_latency = 0

    async with httpx.AsyncClient() as client:
        for item in golden:
            qid = item["id"]
            question = item["question"]
            expected_answer = item["expected"]
            expected_mode = item.get("mode", "vector")

            print(f"  [{qid}] {question[:72]}...")
            actual = await _query(client, base_url, question, token)

            if "error" in actual:
                print(f"    ERROR: {actual['error']}")
                all_results.append({**item, "error": actual["error"], "llm_score": 0.0, "mode_match": False})
                continue

            answer = actual.get("answer", "")
            actual_mode = actual.get("retrieval_mode", "unknown")
            latency = actual.get("latency_ms", 0)

            score = await llm_judge(question, answer, expected_answer)
            llm_scores.append(score)
            total_latency += latency

            mode_ok = _mode_matches(actual_mode, expected_mode)
            if mode_ok:
                mode_hits += 1

            star = "★" if score >= 0.75 else ("~" if score >= 0.5 else "✗")
            print(f"    {star} score={score:.2f}  mode={actual_mode}({'✓' if mode_ok else '✗'})  {latency}ms")

            all_results.append({
                **item,
                "actual_answer": answer[:400],
                "actual_mode": actual_mode,
                "mode_match": mode_ok,
                "llm_score": round(score, 3),
                "latency_ms": latency,
                "chunks_used": actual.get("chunks_used", 0),
                "graph_entities": actual.get("graph_entities_used", []),
                "decision_trail": actual.get("decision_trail_used", False),
            })

    n = len(all_results)
    scored = [r for r in all_results if "error" not in r]
    ns = len(scored)

    summary: dict[str, Any] = {
        "total": n,
        "scored": ns,
        "errors": n - ns,
        "avg_llm_score":  round(sum(llm_scores) / ns, 3) if ns else 0,
        "mode_accuracy":  round(mode_hits / ns, 3)         if ns else 0,
        "avg_latency_ms": round(total_latency / ns)        if ns else 0,
        # Group breakdowns
        "by_group": _group_summary(scored),
        "results": all_results,
    }
    return summary


def _group_summary(scored: list[dict]) -> dict[str, Any]:
    groups: dict[str, list] = {}
    for r in scored:
        g = r.get("group", "unknown")
        groups.setdefault(g, []).append(r["llm_score"])
    return {
        g: {"count": len(scores), "avg_score": round(sum(scores) / len(scores), 3)}
        for g, scores in groups.items()
    }


def _print_summary(s: dict) -> None:
    bar = "=" * 60
    print(f"\n{bar}")
    print("  EVALUATION SUMMARY")
    print(f"  Questions:    {s['scored']}/{s['total']} scored ({s['errors']} errors)")
    print(f"  LLM score:    {s['avg_llm_score']:.3f}  (0=wrong, 1=perfect)")
    print(f"  Mode match:   {s['mode_accuracy']:.0%}  (router accuracy)")
    print(f"  Avg latency:  {s['avg_latency_ms']}ms")
    if s["by_group"]:
        print("  By group:")
        for g, info in s["by_group"].items():
            print(f"    {g:<12} {info['avg_score']:.3f}  ({info['count']} questions)")
    print(bar)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mnemo evaluation suite")
    parser.add_argument("--url",    default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--token",  required=True,                   help="Admin JWT access token")
    parser.add_argument("--groups", nargs="*",                       help="Filter groups: fact decision graph")
    parser.add_argument("--out",    default="eval_results.json",     help="Output JSON file path")
    args = parser.parse_args()

    print(f"\nMnemo evaluation  →  {args.url}")
    print(f"Groups: {args.groups or 'all'}\n")

    results = asyncio.run(evaluate(args.url, args.token, groups=args.groups))
    _print_summary(results)

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results → {args.out}")


if __name__ == "__main__":
    main()
