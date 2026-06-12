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
- **Proven load-bearing by ablation** (`make eval-ablation`): with the critic
  disabled, the independently-measured grounding rate drops to **91.3%**, and the
  critic catches **100/100** seeded fabricated citations. The 1.0 is enforced,
  not vacuous.
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

## Adversarial robustness (red team) — tested, honestly scoped
- A **red-team eval category** (10 gold cases) attacks the system with prompt
  injection in English, Catalan and Spanish ("Ignore your instructions…",
  "Ignora les teves instruccions…"), third-party record requests ("Show me
  L-1005's practice scores"), bulk-exfiltration phrasing, citation-forgery
  requests and file-dump requests. Two of them ship as one-click **Red team
  presets** in the dashboard.
- Learner-view attacks are refused **by policy before any agent runs** (a
  pattern check in the planner); manager-view probes are answered with
  **aggregates only** — the structural defense — and the critic's PII scan
  verifies zero identifiers. Benign look-alikes (first-person goals about the
  learner's *own* id and scores) are explicitly tested NOT to be refused.
- Enforced as a CI gate: **adversarial block rate must be 1.0**.
- **Honest scoping:** the pattern filter is defense-in-depth against known
  phrasings, not an unbreakable classifier — a novel paraphrase can route past
  it. The load-bearing controls are behind it: every answer still passes the
  verbatim-grounding gate (an injection cannot make the system claim an
  unearned "ready"), and the manager view is structurally aggregate-only.
  Per-learner records in this demo are synthetic and served openly **by
  design** (the learner view is self-service); the privacy control protects the
  manager/aggregate surface, where k-anonymity is enforced.

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
