#!/usr/bin/env python3
"""AI CV Screening - Proof of Concept.

LLM scores candidates against structured job criteria with quoted evidence.
The AI ranks and explains; a human always makes the decision.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python screen.py --job job.json --cvs sample_cvs/ --out report.md
"""
import argparse, datetime, hashlib, json, pathlib, re, sys

import anthropic

MODEL = "claude-sonnet-5"

SYSTEM = (
    "You are a recruitment screening assistant. Score a candidate CV against "
    "job criteria. Rules: (1) every score MUST cite a short verbatim quote from "
    "the CV as evidence, or state 'no evidence found'; (2) never consider name, "
    "gender, age, nationality, photos or gaps unrelated to the criteria; "
    "(3) be conservative - unsupported claims score low; (4) output JSON only."
)

PROMPT = """Job title: {title}

Criteria (score each 0-5):
{criteria}

Candidate CV:
---
{cv}
---

Return JSON exactly in this shape:
{{"scores": [{{"criterion": "...", "score": 0, "evidence": "verbatim quote or 'no evidence found'", "reasoning": "one sentence"}}],
  "summary": "two sentences, factual",
  "flags": ["anything a human reviewer should double-check"]}}"""


def redact_pii(text: str) -> str:
    """Strip direct identifiers before the CV reaches the model (bias guardrail)."""
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email removed]", text)
    text = re.sub(r"(\+?\d[\d\s().-]{7,}\d)", "[phone removed]", text)
    return text


def score_cv(client, job, cv_path):
    cv_text = redact_pii(cv_path.read_text(encoding="utf-8"))
    criteria = "\n".join(
        f"- {c['name']} (weight {c['weight']}%): {c['description']}"
        for c in job["criteria"]
    )
    prompt = PROMPT.format(title=job["title"], criteria=criteria, cv=cv_text)
    msg = client.messages.create(
        model=MODEL, max_tokens=1500, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
    result = json.loads(raw)
    weights = {c["name"]: c["weight"] for c in job["criteria"]}
    total = sum(s["score"] / 5 * weights.get(s["criterion"], 0) for s in result["scores"])
    result["weighted_score"] = round(total, 1)
    result["candidate"] = cv_path.stem
    audit(cv_path, prompt, raw)
    return result


def audit(cv_path, prompt, raw_response):
    """Append-only audit trail: what was asked, what the model said, when."""
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": MODEL,
        "cv_file": cv_path.name,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "raw_response": raw_response,
    }
    with open("audit_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", default="job.json")
    ap.add_argument("--cvs", default="sample_cvs")
    ap.add_argument("--out", default="report.md")
    args = ap.parse_args()

    job = json.loads(pathlib.Path(args.job).read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
    results = [
        score_cv(client, job, p)
        for p in sorted(pathlib.Path(args.cvs).glob("*.txt"))
    ]
    results.sort(key=lambda r: r["weighted_score"], reverse=True)

    lines = [
        f"# Screening report - {job['title']}",
        f"_Model: {MODEL} | Generated: {datetime.date.today()} | "
        "**AI ranks and explains; it does not reject anyone. "
        "Final decisions are made by a human reviewer.**_", "",
        "| Rank | Candidate | Weighted score /100 |", "|---|---|---|",
    ]
    lines += [
        f"| {i} | {r['candidate']} | {r['weighted_score']} |"
        for i, r in enumerate(results, 1)
    ]
    for r in results:
        lines += ["", f"## {r['candidate']} - {r['weighted_score']}/100", r["summary"], ""]
        lines += [
            f"- **{s['criterion']}**: {s['score']}/5 - {s['reasoning']} "
            f"_Evidence: \"{s['evidence']}\"_"
            for s in r["scores"]
        ]
        if r.get("flags"):
            lines += ["", "**For human review:** " + "; ".join(r["flags"])]
    pathlib.Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Ranked {len(results)} candidates -> {args.out} (audit: audit_log.jsonl)")


if __name__ == "__main__":
    sys.exit(main())
