# OpenNARS causal learning benchmark — experimental protocol v0.1

Status: **specified, not executed**. Date: 2026-11-04. This document is a preregistered plan, not evidence of an OpenNARS result.

## Question

Does OpenNARS for Applications (ONA) learn useful action-outcome relationships, reject spurious temporal correlations, and transfer rules to structurally equivalent domains better than a simple frequency-table learner under identical observation, action and compute budgets?

## Systems

- ONA: pin a precise upstream commit; build and run unmodified reference implementation first. Record platform, compiler, configuration, seed and logs.
- Baseline A: tabular empirical P(outcome | observed context, action), Laplace-smoothed. Choose action with maximum predicted goal frequency; tie-break with a seeded random policy. Do not give it hidden environment variables.
- Baseline B: random action policy (sanity check).
- Optional: existing OTTT learner only if its interface and information budget can be made identical; do not silently retrofit the task.

## Environment and input parity

A tiny deterministic-seed simulator with a finite observable state, two or three registered actions, binary outcome and explicit goal. Same initial states, observation streams, exploration opportunities, outcome delays and action budgets for all systems. Translate simulator events into ONA's Narsese via a documented adapter. Baselines receive semantically equivalent observations, not privileged state.

Keep **training**, **evaluation**, and **intervention** phases distinct. Evaluation must freeze learned parameters/beliefs where feasible; if ONA cannot freeze online updates, document this and compare in a matched online-evaluation mode instead. Report both modes separately if used.

## Scenario 1: true intervention

Binary context C, actions A/B. In C=0, A succeeds with probability 0.9 and B with 0.1; in C=1, reverse. All outcome draws are seeded. Agent sees C before action. Primary metric: held-out reward / regret; secondary: accuracy and calibration of outcome predictions if accessible. Include a control with delayed outcomes to test temporal credit assignment.

## Scenario 2: spurious correlation / confounding

Hidden Z influences both an observational action propensity and the outcome; **the action has no causal effect**. Observational logs contain a strong association between action A and reward. At test time, allow randomized interventions do(A)/do(B) while holding the distribution of Z fixed. A causally correct system should find no reliable intervention advantage. Report separately: association learned from logs, intervention policy performance, false causal claims, and uncertainty. **Do not infer causal identification merely from equal rewards**; use explicit interventional evidence and calibration.

## Scenario 3: structural transfer

Train in domain 1 with entities and predicates named X1/Y1, then evaluate domain 2 with new names and isomorphic relations. Provide two variants: (a) explicit mapping given to both learners, (b) no mapping given. A system cannot be expected to transfer from arbitrary renamed symbols without shared features or mapping. Compare to a relational-rule baseline as well as tabular baseline; otherwise a positive result is trivial.

## Reproducibility and fairness

- >=20 paired seeds per condition, same seeds for all systems.
- Fix budgets **before** observing results: observation count, action count, inference cycles, memory capacity, wall time and CPU utilization.
- Measure learning curves at 0, 25%, 50%, 100% of budget and after distribution shift.
- Report mean, median, dispersion, 95% bootstrap CI and per-seed paired differences. Do not overinterpret small samples.
- Explicitly record ONA motor-babbling rate, registered operations, concept capacity, forgetting parameters, and the Narsese encoding.
- Separate successful runs, failed runs, crashes and invalid adapter outputs. Never silently discard failures.
- Negative controls: shuffled action labels, shuffled outcomes, no-effect actions.
- Inspect ONA predictions and evidence stamps if accessible; do not mistake confidence in NARS for a calibrated frequentist probability.

## Implementation deliverables for Codex

1. `experiments/benchmarks/ona_causal/`: environment, baseline, ONA subprocess adapter, pinned setup instructions and unit tests.
2. A smoke test proving ONA input parsing and output extraction using a known upstream example.
3. Reproducible commands for all scenarios, machine-readable CSV/JSON results, raw logs and generated summary.
4. `docs/OPENNARS_CAUSAL_RESULTS.md` with source commit, commands, environment, metrics, failures and evidence-based conclusions; mark as NOT RUN until actually executed.
5. No changes to OTTT core or integration with ONA until experiment is reviewed.

## Decision rule

Recommend ONA reuse only if it delivers a repeatable, statistically and practically meaningful improvement on at least one nontrivial condition **without unacceptable complexity**, and its failure modes are understood. Otherwise extract useful ideas (priority queues, bounded working memory, evidence accounting) without adopting the whole architecture.

## Current evidence

Static inspection confirms ONA code paths for temporal pattern mining (`src/Cycle.c`), action selection/anticipation (`src/Decision.c`), and quantitative truth revision (`src/Truth.c`). No causal benchmark was executed as part of this document.
