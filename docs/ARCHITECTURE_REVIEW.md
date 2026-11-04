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


## Preliminary source inspection — 2026-11-04

Scope: initial examination, not a benchmark or full audit.

### OpenNARS for Applications

Directly inspected [src/Memory.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Memory.c): implemented priority queues for concepts and cycling belief/goal events; term-keyed concept hash table; temporal occurrence index; bounded storage arrays; operation registry. The source header identifies MIT licensing; repository-wide license and dependency obligations remain to be verified. Documentation describes priority selection, usefulness-based eviction, semantic and sensorimotor inference, which still require code-path and test verification. Potential reuse: working-memory scheduling and indexing; do not confuse bounded active concepts with append-only episodic provenance.

### Hyperon Experimental / MeTTa

Directly inspected [lib/src/metta/interpreter.rs](https://github.com/trueagi-io/hyperon-experimental/blob/main/lib/src/metta/interpreter.rs): Rust implementation has an explicit evaluation stack, variable bindings and shared state for alternative reductions. This provides source-level evidence of nondeterministic execution machinery. Hyperon documentation describes AtomSpace as a typed metagraph and MeTTa as structural transformations; these claims require further source/test review. Potential reuse: unification, typed symbolic representation and structural transformations in an isolated prototype. Licensing and Windows installation burden not yet verified.

### Provisional conclusion

ONA already implements concrete concept/event scheduling; MeTTa already has machinery for alternative symbolic matches. Neither establishes autonomous discovery of concepts or general intelligence. Next: inspect ONA inference/revision/evidence code and tests; Hyperon matcher/Space API/tests; check licenses, maintenance and Python bindings; compare runnable examples with ОТТТ. No integration decision yet.


## OpenNARS decision cycle — source trace (2026-11-04)

Inspected code in [src/Cycle.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Cycle.c), [src/Decision.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Decision.c), and [src/Memory.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Memory.c).

- Cycle_Perform (~line 1104): selects belief/goal events from priority queues, processes belief sequences and goal propagation, performs inference, then applies relative forgetting. This is a concrete bounded-resource cognition loop.
- Cycle_ProcessSensorimotorEvent (~line 84): conceptualizes incoming events, finds related concepts, unifies terms and activates sensorimotor processing.
- Decision_Suggest (~line 814): evaluates Decision_BestCandidate and may instead select Decision_MotorBabbling. Motor babbling samples a registered operation; it is exploration among available actions, not demonstrated invention of a new primitive operation.
- Memory_Conceptualize (~line 109): retrieves a concept by term or inserts it in a bounded priority queue, evicting an existing concept if necessary; updates hash and inverted-atom indices. This active memory differs from ОТТТ's append-only event archive.
- Decision_Execute and Decision_Anticipate exist, but causal learning, prediction error, evidential revision and operation invention require deeper trace and runnable tests before claims of demonstrated behavior.

**Architectural implication:** compare NARS's priority-driven active conceptual memory and exploration/exploitation policy with ОТТТ's event store and hand-coded attention. Do not conflate creation of a concept record with discovery of a genuinely new semantic concept. No code integration authorized by this finding.


## OpenNARS learning from action outcomes — code trace (2026-11-04)

Sources inspected: [src/Cycle.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Cycle.c) (Cycle_ProcessBeliefEvents, around line 676); [src/Decision.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Decision.c) (Decision_Anticipate, around line 556); [src/Truth.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Truth.c) (Truth_Revision, around line 46); [src/Memory.c](https://github.com/opennars/OpenNARS-for-Applications/blob/master/src/Memory.c) (belief revision path, around line 377).

- Cycle_ProcessBeliefEvents examines time-ordered precondition, registered operation and postcondition events and calls Cycle_ReinforceLink to derive temporal implication candidates. Code applies temporal-distance and evidence-stamp overlap checks.
- Decision_Anticipate traverses stored implications, filtering invalid ones and examining conditions for anticipated consequences. Its precise negative-evidence update path still needs tracing and tests.
- Truth_Revision combines frequency and confidence using confidence-to-evidence-weight conversions and weighted frequency; special handling exists for confidence=1 when configured. Memory.c calls Inference_RevisionAndChoice and records a revised event when revision occurs. The stamp-based independence condition needs verification in that function.
- The system therefore has code for learning temporal action-outcome regularities and revising quantitative beliefs, but **temporal correlation is not proof of causal identification**. No evidence yet that it invents primitive operations or generalizes causal rules to unseen ontological domains.

Next controlled experiment: construct paired environments with true action causation versus spurious temporal correlation, independent held-out episodes, negative outcomes and distribution shift. Measure chosen actions, predictive calibration, false causal rules, memory pressure and forgetting. Compare to a simple frequency-table learner and to ОТТТ's existing approach under the same data budget.
