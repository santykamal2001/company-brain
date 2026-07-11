"""
End-to-end evaluation runner.

Usage:
  TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \\
    -H 'Content-Type: application/json' \\
    -d '{"email":"admin@company-brain.local","password":"<pw>"}' \\
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  # All questions:
  cd backend && python -m eval.run_eval --token "$TOKEN"

  # Specific groups:
  python -m eval.run_eval --token "$TOKEN" --groups fact decision

  # Skip adversarial (for quick checks):
  python -m eval.run_eval --token "$TOKEN" --skip-groups unanswerable adversarial

  # A/B comparison: hybrid vs vector-only
  python -m eval.run_eval --token "$TOKEN" --out eval_hybrid.json
  # Set GRAPH_ENABLED=false + restart backend, then:
  python -m eval.run_eval --token "$TOKEN" --out eval_vector.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Any

import httpx

from eval.golden_set import REFUSE_SENTINEL, is_refuse_question, load_golden_set
from eval.metrics import hallucination_check, llm_judge, refusal_accuracy


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
            timeout=90,
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
    if actual == expected:
        return True
    if expected in ("hybrid", "graph") and actual in ("hybrid", "graph"):
        return True
    return False


async def evaluate(
    base_url: str,
    token: str,
    groups: list[str] | None,
    skip_groups: list[str] | None,
) -> dict[str, Any]:
    golden = load_golden_set()
    if groups:
        golden = [q for q in golden if q.get("group") in groups]
    if skip_groups:
        golden = [q for q in golden if q.get("group") not in skip_groups]

    all_results: list[dict] = []
    # Separate tracking for answerable vs refusal questions
    judge_scores: list[float] = []
    refusal_scores: list[float] = []
    hallucination_scores: list[float] = []
    mode_hits = 0
    mode_total = 0
    total_latency = 0

    async with httpx.AsyncClient() as client:
        for item in golden:
            qid = item["id"]
            question = item["question"]
            expected = item["expected"]
            expected_mode = item.get("mode", "vector")
            is_refuse = is_refuse_question(item)

            print(f"  [{qid}] ({item.get('group','?'):12}) {question[:65]}...")
            actual = await _query(client, base_url, question, token)

            if "error" in actual:
                print(f"    ERROR: {actual['error']}")
                all_results.append({**item, "error": actual["error"], "llm_score": 0.0,
                                     "refusal_score": None, "hallucination_score": None,
                                     "mode_match": False})
                continue

            answer = actual.get("answer", "")
            actual_mode = actual.get("retrieval_mode", "unknown")
            latency = actual.get("latency_ms", 0)
            source_excerpts = [s.get("excerpt", "") for s in actual.get("sources", [])]

            total_latency += latency

            if is_refuse:
                # Score is whether the model correctly refused
                r_score = refusal_accuracy(answer)
                refusal_scores.append(r_score)
                h_score = None
                llm_score = r_score  # refusal accuracy IS the score for these questions

                star = "★" if r_score >= 1.0 else "✗"
                verdict = "refused (correct)" if r_score >= 1.0 else "hallucinated (wrong)"
                print(f"    {star} refusal={r_score:.2f}  {verdict}  {latency}ms")
            else:
                # Score answerable question: LLM judge + hallucination check in parallel
                llm_score, h_score = await asyncio.gather(
                    llm_judge(question, answer, expected),
                    hallucination_check(question, answer, source_excerpts),
                )
                judge_scores.append(llm_score)
                hallucination_scores.append(h_score)

                mode_ok = _mode_matches(actual_mode, expected_mode)
                if mode_ok:
                    mode_hits += 1
                mode_total += 1

                star = "★" if llm_score >= 0.75 else ("~" if llm_score >= 0.5 else "✗")
                h_flag = "" if h_score >= 0.9 else " ⚠ HALLUCINATION"
                print(f"    {star} score={llm_score:.2f}  halluc={h_score:.2f}  mode={actual_mode}({'✓' if mode_ok else '✗'})  {latency}ms{h_flag}")

            all_results.append({
                **item,
                "actual_answer": answer[:400],
                "actual_mode": actual_mode,
                "mode_match": _mode_matches(actual_mode, expected_mode) if not is_refuse else None,
                "llm_score": round(llm_score, 3),
                "refusal_score": round(refusal_scores[-1], 3) if is_refuse else None,
                "hallucination_score": round(h_score, 3) if h_score is not None else None,
                "latency_ms": latency,
                "chunks_used": actual.get("chunks_used", 0),
                "graph_entities": actual.get("graph_entities_used", []),
                "decision_trail": actual.get("decision_trail_used", False),
            })

    n = len(all_results)
    scored = [r for r in all_results if "error" not in r]
    ns = len(scored)
    answerable = [r for r in scored if r.get("refusal_score") is None]
    refusals = [r for r in scored if r.get("refusal_score") is not None]

    summary: dict[str, Any] = {
        "total": n,
        "scored": ns,
        "errors": n - ns,
        "answerable_questions": len(answerable),
        "refusal_questions": len(refusals),
        # Answerable quality
        "avg_llm_score": round(sum(judge_scores) / len(judge_scores), 3) if judge_scores else 0,
        "hallucination_rate": round(1.0 - (sum(hallucination_scores) / len(hallucination_scores)), 3) if hallucination_scores else 0,
        # Refusal/adversarial quality
        "refusal_accuracy": round(sum(refusal_scores) / len(refusal_scores), 3) if refusal_scores else None,
        # Routing
        "mode_accuracy": round(mode_hits / mode_total, 3) if mode_total else 0,
        # Latency
        "avg_latency_ms": round(total_latency / ns) if ns else 0,
        # Breakdowns
        "by_group": _group_summary(scored),
        "results": all_results,
    }
    return summary


def _group_summary(scored: list[dict]) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for r in scored:
        g = r.get("group", "unknown")
        groups.setdefault(g, []).append(r["llm_score"])
    return {
        g: {"count": len(scores), "avg_score": round(sum(scores) / len(scores), 3)}
        for g, scores in groups.items()
    }


def _print_summary(s: dict) -> None:
    bar = "=" * 66
    print(f"\n{bar}")
    print("  EVALUATION SUMMARY")
    print(f"  Questions total:     {s['scored']}/{s['total']}  ({s['errors']} errors)")
    print(f"  Answerable (n={s['answerable_questions']}):  LLM judge score    {s['avg_llm_score']:.3f}  (0=wrong, 1=perfect)")
    print(f"  Answerable (n={s['answerable_questions']}):  Hallucination rate {s['hallucination_rate']:.1%}  (lower is better)")
    if s.get("refusal_accuracy") is not None:
        print(f"  Refusals   (n={s['refusal_questions']}):  Refusal accuracy   {s['refusal_accuracy']:.1%}  (IDK when should IDK)")
    print(f"  Mode routing:        {s['mode_accuracy']:.0%}  ({s['answerable_questions']} answerable questions)")
    print(f"  Avg latency:         {s['avg_latency_ms']}ms")
    if s["by_group"]:
        print("\n  By category:")
        for g, info in sorted(s["by_group"].items()):
            bar_width = int(info["avg_score"] * 20)
            bar_str = "█" * bar_width + "░" * (20 - bar_width)
            print(f"    {g:<14} [{bar_str}]  {info['avg_score']:.3f}  ({info['count']} q)")
    print("=" * 66)


def main() -> None:
    parser = argparse.ArgumentParser(description="Company Brain evaluation suite")
    parser.add_argument("--url",    default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--token",  required=True,                   help="Admin JWT access token")
    parser.add_argument("--groups", nargs="*",                       help="Run only these groups")
    parser.add_argument("--skip-groups", nargs="*", dest="skip_groups",
                        help="Skip these groups (e.g. unanswerable adversarial)")
    parser.add_argument("--out",    default="eval_results.json",     help="Output JSON file path")
    args = parser.parse_args()

    print(f"\nCompany Brain evaluation  →  {args.url}")
    print(f"Groups:      {args.groups or 'all'}")
    print(f"Skip groups: {args.skip_groups or 'none'}\n")

    results = asyncio.run(evaluate(args.url, args.token,
                                   groups=args.groups, skip_groups=args.skip_groups))
    _print_summary(results)

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results → {args.out}")


if __name__ == "__main__":
    main()
