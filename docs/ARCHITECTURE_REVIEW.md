# Architecture review — ОТТТ-ИИ

Status: research plan, **not a completed audit**. Recorded 2026-11-04 after experiment 5B (`b9fe59e`).

## Purpose

Before implementing experiment 5C or adding a neural Metaoperator, compare ОТТТ-ИИ against existing open-source cognitive and symbolic AI systems. Avoid reinventing established mechanisms and distinguish engineering progress from evidence of general intelligence.

## Systems to inspect

1. OpenNARS — https://github.com/opennars/OpenNARS-for-Applications — uncertain reasoning, attention/task priorities, belief revision.
2. OpenCog Hyperon / MeTTa — https://github.com/trueagi-io/hyperon-experimental — typed knowledge representation, structural matching, transformations.
3. Soar — https://github.com/SoarGroup/Soar — operator selection, working memory, impasses/subgoals, learning.
4. miniKanren / kanren — https://github.com/pythological/kanren — unification and relational programming.
5. PyReason — https://github.com/lab-v2/pyreason — temporal logical inference.
6. Clingo — https://github.com/potassco/clingo — answer-set solving and constrained search.
7. AIMA Python — https://github.com/aimacode/aima-python — baseline implementations for comparison.

## Review protocol

For each candidate: verify repository and license; inspect actual implementation and tests, not just README claims; identify concrete algorithms and interfaces; compare with ОТТТ modules (memory, perception, attention, research cycle, identity tracking and parameter learning); estimate dependencies, integration effort and runtime footprint on an HP Z620 CPU / 48 GB RAM / GTX 1050 Ti 4 GB; document known limits and maintenance status. Distinguish reuse as a library, borrowing a design principle, and rejecting integration. Do not merge code until license and evaluation are checked.

## Research questions

- Which existing mechanisms duplicate ours, and which can be reused directly?
- Can a compact logic/ontology-driven system learn transferable structural operations with less data and compute than meaningful baselines?
- What is truly novel, if anything, in ОТТТ? Do not infer novelty from a new combination of familiar labels.
- What evidence would falsify the central hypothesis?

## Evaluation discipline

Compare against simple fixed-rule, search/solver, and small learned baselines under identical tasks and budgets. Use held-out scenarios, negative controls, metrics for error/abstention, compute and memory. Separate **implemented**, **experimentally verified**, and **hypothesized**. Experiment 5B currently demonstrates bounded parameter calibration, not autonomous discovery of identity criteria; generalization was tested within scenario families on independent seeds.

## Deliverables (pending)

A per-project evidence table with source file references, licenses, mechanisms, technical feasibility, overlap and recommendation; a shortlist of minimal integration spikes; a clear list of unresolved original research questions. Update this document with dated findings after source inspection. Do not treat this plan as completed findings.
