# AI CV Screening - Proof of Concept

A working slice of "Initiative 2" from my recommendation for the AI-Native Engineering Challenge: LLM-based CV screening that **ranks and
explains, while a human always decides**.

Built in one evening with AI assistance - which is the point. The
recommendation argues that hosted LLMs turn CV screening from a
quarters-long ML project into a weeks-long integration; this PoC is the
existence proof.

## What it does

```
python screen.py --job job.json --cvs sample_cvs/ --out report.md
```

For each CV, the model scores every job criterion 0-5 and must cite a
**verbatim quote** from the CV as evidence (or say "no evidence found").
Scores are weighted into a ranking and written to a Markdown report.
See `example_output.md` for a real run on the bundled sample data.

## Guardrails (non-negotiable in hiring tech)

- **Human-in-the-loop**: the tool never rejects anyone; every report states
  this explicitly and includes "for human review" flags per candidate.
- **Explainability**: no score without quoted evidence - reviewable line by line.
- **Bias reduction**: direct identifiers (email, phone) are redacted before
  the CV reaches the model, and the system prompt forbids considering name,
  gender, age, nationality or photos. (Production next step: full name/address
  redaction and adversarial bias testing on matched CV pairs.)
- **Audit trail**: every model call is logged append-only to `audit_log.jsonl`
  (timestamp, model, prompt hash, raw response).

## Run it

```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python screen.py
```

Sample data is fictional. Cost: ~1 cent for the three bundled CVs.

## Production next steps (deliberately out of PoC scope)

Structured criteria authoring in the RMS UI - batch processing behind the
existing async job queue - recruiter feedback loop (accept/override each
score) feeding prompt iteration - fairness evaluation suite before any
customer pilot.
