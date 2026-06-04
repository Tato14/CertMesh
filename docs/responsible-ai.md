# Responsible AI & guardrails

CertMesh is decision-support for a workforce learning programme. The guardrails
below are real, tested controls — not aspirations.

## Transparency
- The dashboard shows an AI-disclosure banner on every page (*"You are interacting
  with an AI assistant. Recommendations are decision-support; a manager or
  learning lead has final oversight."*).
- Important recommendations carry a human-oversight note; abstentions are clearly
  labelled and "flagged for human review".

## Grounding guard (the critic) — a real control
- No fabricated certification facts or practice questions. Every cited snippet and
  every quoted summary claim must be a **verbatim substring** of a retrieved
  source (`agents/critic.py` + `iq/foundry_iq.supports`).
- Ungrounded output triggers a bounded **self-reflection** loop; if it still can't
  be grounded the agent **abstains**.
- Enforced as a CI gate: **citation grounding rate must be 1.0** or the build fails.
- Tested in `tests/test_critic.py` (accepts grounded, rejects fabricated, abstains
  after the retry budget).

## Privacy / PII (manager view)
- Manager insights are **aggregate and thresholded only**. Learners are grouped by
  (team, track); any group below `min_group_size = 3` is **suppressed**
  (k-anonymity) and never reported.
- No `learner_id`, `employee_id`, name, or individual figure is ever emitted.
- The critic independently scans every manager response for individual identifiers
  and sub-threshold groups; a finding forces an abstain.
- Enforced as a CI gate: **manager PII-leak total must be 0**.
- Tested in `tests/test_orchestrator.py::test_manager_views_never_leak_pii` across
  every team, and in `tests/test_critic.py`.

## Abstention under uncertainty
- Out-of-corpus certification (e.g. an AWS exam) → grounded abstain with a clear message.
- Ambiguous goal → ask the learner to clarify (does not guess).
- Tested + measured: **abstention correctness = 1.0** in the eval scorecard.

## Fairness / uneven outcomes
- The eval suite spans clinical, technical and compliance tracks and all four
  teams, so readiness and capacity behaviour is checked across cohorts rather than
  one happy path.
- The manager report explicitly flags capacity-constrained teams so that
  structural disadvantage (e.g. clinical staff with little focus time) is surfaced
  rather than read as under-performance.
- **Known limitation:** practice scores and work signals are synthetic; on real
  data, monitor for systematic gaps across roles/teams before acting on flags.

## Data hygiene & secrets
- All data, identifiers and documents are synthetic (fabricated ids like `L-1001`,
  `EMP-001`). No real PII anywhere in the repo. Stated in the README and LICENSE.
- `.env` is gitignored; only `.env.example` is committed. Managed identity
  (`DefaultAzureCredential`) is preferred over API keys; secrets stay out of the
  container image. Run the secret scan in the README before pushing.
- Dependencies are pinned (`pyproject.toml`).

## Human oversight
- The system never books an exam, changes a record, or makes an HR decision. It
  recommends; a learning lead or manager decides. Manager insights are framed as
  planning decision-support, explicitly "not performance management of
  individuals".
