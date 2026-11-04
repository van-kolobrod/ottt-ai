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


## Queue update and Hyperon source inspection — 2026-11-04

**Execution status:** OpenNARS causal benchmark protocol in `docs/OPENNARS_CAUSAL_BENCHMARK.md` is QUEUED / NOT RUN. Codex quota unavailable; do not begin implementation or imply measurements exist. Resume when resources permit. Continue static prior-art analysis meanwhile.

### Hyperon evidence (source-level)

- [hyperon-atom/src/matcher.rs](https://github.com/trueagi-io/hyperon-experimental/blob/main/hyperon-atom/src/matcher.rs): Rust bindings, binding sets, variable resolution and matching infrastructure; structural unification is an implemented mechanism.
- [hyperon-space/src/lib.rs](https://github.com/trueagi-io/hyperon-experimental/blob/main/hyperon-space/src/lib.rs): Space abstraction for atom storage and querying; modification events Add/Remove/Replace and observers. This is mutable knowledge storage, not by itself an append-only evidence log.
- [docs/minimal-metta.md](https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/minimal-metta.md): interpreter state includes atomspace and variable bindings; nondeterministic interpretation maintains multiple branches; reduction searches rewrite equations in atomspace and supports grounded foreign functions. Specification explicitly states it is not final.
- [python/hyperon/base.py](https://github.com/trueagi-io/hyperon-experimental/blob/main/python/hyperon/base.py): Python AbstractSpace and GroundingSpace wrappers expose query/add/remove/replace. Python interface exists in source; installation and platform compatibility not tested.

**Interpretation:** Hyperon offers reusable mechanisms for typed symbolic structures, structural matching and rewrite execution, but inspected code does not establish automatic induction of new cross-domain operators. A generic `compose` operator would still need domain-specific constraints (chemical bonds versus human social ties versus grammar). Distinguish structural analogy from valid transfer of causal mechanisms. No code changes or integration proposed yet.

**Next inspection:** MeTTa rewriting semantics and atom type system, representation of structural relations and their constraints, mechanisms (if any) for learning new rules, scalability, license and maintenance. Then compare with Soar and NARS at the level of implemented cognition loops.


## Hyperon rule discovery versus rule execution — 2026-11-04

**Evidence inspected:** [docs/metta.md](https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/metta.md), [docs/minimal-metta.md](https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/minimal-metta.md), [lib/src/metta/interpreter.rs](https://github.com/trueagi-io/hyperon-experimental/blob/main/lib/src/metta/interpreter.rs), [python/hyperon/base.py](https://github.com/trueagi-io/hyperon-experimental/blob/main/python/hyperon/base.py), [README.md](https://github.com/trueagi-io/hyperon-experimental/blob/main/README.md).

- MeTTa represents rewrite/function definitions as `(= <call-pattern> <body>)`, supports variable matching and nondeterministic alternative reductions. The `:` and `->` forms specify atom/function types. Grounded operations can delegate to external implementations.
- The minimal interpreter specification explicitly states it is not final. It describes an interpretation plan containing alternative atom/bindings pairs, and rewrite lookup in atomspace.
- Python bindings exist and README documents `python3 -m pip install hyperon`; installation and runtime were NOT tested here.
- **Critical distinction:** a rewrite engine can execute a newly inserted rule, but this does not by itself provide a rule-induction objective, hypothesis search, experiment design, evidence calibration or out-of-domain transfer. No general autonomous rule-induction algorithm was established from inspected files. Absence of a code-search hit for `learning` or `induction` is not evidence of absence across the entire ecosystem.
- For OTTT, an external learner could propose candidate MeTTa rules from observations, test them on held-out examples, and add only verified rules with provenance and confidence to a separate space. The learner, not the interpreter, would supply the discovery mechanism. This is an architectural hypothesis, NOT implemented.
- Proposed evaluation when Codex is available: compare explicit rewrite rules, simple grammar enumeration plus held-out testing, and relation-aware candidate generation on identical tasks. No experiment run.

**Status:** OpenNARS causal benchmark remains QUEUED / NOT RUN due to Codex quota. Continue source analysis of Hyperon learning-related components and compare Soar next.


## Soar explanation-based chunking and RL — source inspection (2026-11-04)

Sources: [ebc.cpp](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/explanation_based_chunking/ebc.cpp), [ebc_build.cpp](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/explanation_based_chunking/ebc_build.cpp), [ebc_settings.h](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/explanation_based_chunking/ebc_settings.h), [reinforcement_learning.cpp](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/reinforcement_learning/reinforcement_learning.cpp).

- Soar has a concrete Explanation_Based_Chunker, rule generation and settings for controlling learning. It excludes top-level instantiations from EBC learning and can restrict learning by goal/problem-space settings. Its build code gathers result preferences and tracks/unifies identity sets, providing a mechanism for explanation-based rule compilation/generalization.
- Soar also has a separate reinforcement-learning subsystem with configurable SARSA, Q-learning and GQ-lambda policies; source defaults include learning off, discount rate 0.9, learning rate 0.3. This is distinct from EBC chunking and must not be conflated with it.
- **Important limit:** EBC can compile/generalize consequences of an existing reasoning trace; it is not evidence that Soar autonomously invents novel ontological primitives or discovers arbitrary physical causal laws from raw data. The original task representation, available productions and reasoning path matter.
- Relevance to OTTT: consider a two-stage process (i) solve D0→D1 with a transparent trace and (ii) distill the necessary conditions and transformations into a reusable rule with provenance, validity domain and negative tests. This is a candidate architecture, not a code integration decision.
- Follow-up research: inspect the exact backtrace, variablization, chunk-validation and failure/repair paths; test whether a chunk genuinely transfers across structurally isomorphic domains and how invalid generalization is detected. No Soar executable experiment has been run.

OpenNARS causal benchmark remains queued, not executed.


## Soar EBC: how relevant conditions are selected (2026-11-04)

Source inspection: [ebc_backtrace.cpp](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/explanation_based_chunking/ebc_backtrace.cpp), [ebc_variablize.cpp](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/explanation_based_chunking/ebc_variablize.cpp), [ebc_repair.cpp](https://github.com/SoarGroup/Soar/blob/master/Core/SoarKernel/src/explanation_based_chunking/ebc_repair.cpp).

- Backtracing explicitly tracks `grounds`, `locals` and `negateds`, and marks instantiations to avoid traversing them twice. Relevance is computed from dependencies in a reasoning trace, not a statistical test of physical causation.
- Variablization handles symbol identities and replaces eligible literal symbols with shared variables; not all symbols can or should be generalized.
- Repair path includes `reorder_and_validate_chunk`, `reorder_and_validate_lhs_and_rhs`, and an attempted repair of unconnected conditions/RHS ordering. This is **structural/operational validation**, not evidence of empirical validation against unseen worlds.
- Key distinction for OTTT: *derivational relevance* (used in a proof), *causal relevance* (changes outcome under intervention), and *transfer validity* (holds in new contexts) are three different predicates. A reusable rule needs provenance of derivation plus independent outcome checks and explicit scope. EBC addresses mainly the first and some syntactic/generalization safety.
- Proposed architecture hypothesis: store a proof/dependency DAG for D0→D1, extract candidate rule by backward slicing, variablize with preserved equality/identity constraints, validate structurally, then test interventions and held-out transfer. No implementation or benchmark executed.

OpenNARS benchmark remains queued due to Codex limit.


## BACON scientific-discovery lineage — literature review (2026-11-04)

Primary sources: [Langley 1977 BACON](https://ijcai.org/proceedings/1977/77); [Langley 1981 BACON.3](https://doi.org/10.1016/S0364-0213(81)80025-0); [Langley, Bradshaw & Simon 1981 BACON.5](https://ijcai.org/proceedings/1981/26); [Bradshaw, Langley & Simon 1983 Science](https://pubmed.ncbi.nlm.nih.gov/17776217/); [Langley et al. 1983 GLAUBER/BACON/DALTON](https://ijcai.org/proceedings/1983/114).

- BACON employs a small set of data-driven heuristics: identify constancies/trends, generate derived quantities (ratios/products), recursively analyze derived quantities, and postulate theoretical terms or intrinsic properties. This is **search in a human-specified operation language**, not invention of arithmetic primitives.
- Versions differ materially: 1977 early BACON used programmer-specified primitive attributes in an artificial world and acknowledged inability to express conditional laws; BACON.3 reports experiments, irrelevant-variable handling and rediscovery of Kepler, Ohm, ideal gas etc.; BACON.5 reports conservation/symmetry laws, but explicitly flags inability to handle noise and irrelevant variables and restricted law class. Do not merge version-specific capabilities.
- Rediscovery of a known empirical equation on curated data is not evidence of general causal discovery or novel physical theory; no independent replication or original code execution performed in this review.
- Of special relevance to OTTT: recursively construct *new descriptive quantities* and then apply the same invariance-search operator to them. Distinguish discovery of a new descriptor from discovery of a new operation, and mathematical fit from causal mechanism.
- Related complementary systems described by authors: GLAUBER (qualitative classes/laws) and DALTON (structural models of reactions). These merit investigation because OTTT seeks relations and transformations, not only numerical laws.

OpenNARS benchmark remains queued / NOT RUN; no Codex tasks executed.


## GLAUBER and DALTON: qualitative concepts and latent structural models (2026-11-04)

Primary: Langley, Zytkow, Bradshaw & Simon, *Three Facets of Scientific Discovery*, IJCAI 1983, https://ijcai.org/proceedings/1983/114 ; further GLAUBER: Langley et al., *Discovering qualitative empirical laws* (1985), https://escholarship.org/uc/item/1rc2v2sm ; DALTON later comparison: https://cdn.aaai.org/AAAI/1993/AAAI93-071.pdf .

- GLAUBER starts from explicitly encoded qualitative predicate/attribute-value facts, identifies shared values/patterns, creates classes, merges classes with overlapping membership and recursively abstracts patterns over newly formed classes. Authors report rediscovery of acid/alkali/salt concepts and reaction laws. Crucially, inputs and relation vocabulary are supplied; this is not autonomous sensory concept grounding.
- DALTON heuristically searches latent molecule/particle counts and structural models that explain observed reactions, using assumptions such as conservation and simplicity, with backtracking and revision on additional reactions. One observation may underdetermine the true structure; the 1983 paper explicitly illustrates a model consistent with water reaction data that is revised on ammonia evidence.
- Distinguish **concept induction** (GLAUBER), **numeric law induction** (BACON), **latent structural explanation** (DALTON). These are distinct inference problems. Authors explicitly stated that their computational integration was not yet implemented in 1983, though proposed bidirectional constraints between them.
- Key lesson for OTTT research, not an adoption decision: test whether a shared representational substrate can support all three and whether learned class structure can constrain hypotheses about transformations without silently assuming chemical conservation applies to social systems.
- Limits: prepared symbolic/chemical data, human-provided operators/assumptions, no demonstrated general cross-domain transfer, no original runtime or independent replication here.
- Future predecessors worth studying: STAHL (element/compound decomposition and historical phlogiston models), DENDRAL (knowledge-intensive constrained structural search), AM/Eurisko (concept/heuristic discovery), DreamCoder (library learning and program abstraction).


## CYRANO / Ken Haase: closure, abstraction and research status (2026-11-04)

Primary source: Kenneth Haase, *Discovery Systems: From AM to CYRANO*, MIT AI Lab Working Paper 293 (March 1987), https://dspace.mit.edu/bitstream/handle/1721.1/41178/AI_WP_293.pdf . This is explicitly a preliminary working paper, not a demonstrated mature general discovery engine.

- Central thesis: **closure of concept formation**. Newly formed concepts must themselves be valid inputs to the same concept-formation mechanism. A fixed nonrecursive combinatorial vocabulary has limited reach; recursive concept formation expands the space rapidly, necessitating heuristic search.
- Explicitly distinguish **closure** from **usefulness**: closure makes recursive discovery representationally possible but does not guarantee informative or valid concepts.
- Detailed diagnosis of AM `CANONIZE`: it helped create a representation of numbers from list equivalences, but generated tokens rather than first-class equivalence classes accessible to the same discovery mechanism. Haase argues the implementation thereby made the heuristic effectively one-shot. This is his diagnosis, not an experimentally established unique cause of AM's termination.
- CYRANO replaces earlier frame/RLL designs with `TYPICAL`, a compositional type/predicate language with subsumption lattice. Concepts are types or mappings; abstraction functions map between vocabularies. Example: list concatenation APPEND is transported via cardinality abstraction to addition PLUS. Formal reading: A(f(x,y)) = g(A(x), A(y)) **when the abstraction preserves the operation**, not in general.
- Discovery loop also tries to generate positive/negative instances for candidate regularities. Paper says an implemented heuristic prunes some partition abstractions based on statistical spread. **Major open limit acknowledged by author:** no sufficiently general criterion for pruning abstraction spaces; no complete measure of vocabulary coherence. Do not claim CYRANO achieved sustained autonomous discovery or solved search explosion.
- Research lesson for OTTT: study which operators preserve invariants across levels, record abstraction maps and their validity conditions, and ensure newly induced concepts remain first-class operands. This is research comparison, not an adoption decision.
- Distinguish historical status: this is a 1987 experimental project; current ongoing development or comprehensive performance benchmarks not established by the source.


## Cross-level goal re-planning and persistence (2026-11-04)

User-derived OTTT hypothesis: when a chosen method fails because it violates physical/material/organizational constraints, ascend the goal hierarchy to the nearest parent goal, then search for an alternative transformation satisfying that parent goal's postconditions. Example mechanical: turn a seized bolt -> remove the bolt by another method -> separate parts. Example social: train an underperforming employee -> reassign or replace them -> ensure organizational function is fulfilled. Social case adds rights, contracts, stakeholder welfare and uncertainty; the analogy transfers **goal-functional structure**, not treatment of people as objects.

Model: state S with entities, properties, relations and constraints; action applicability preconditions; effects; target predicate G; alternatives equivalent only **relative to G and all additional constraints**, not physically or ethically identical. Distinguish impossible under known laws, unreachable with available actions, and unknown. Ontological noncontradiction is necessary but not sufficient for reachable plans. Persist important goals separately from methods: failure of one method should not imply abandonment of goal. Method enumeration is task-typed and constraint-pruned; consider changes to action parameters, alternative actions, ascent to parent goals, and reformulation of the goal decomposition. Persistence depends on goal importance; do not conflate goal persistence with repeated use of a failed method. These are architectural proposals, not empirically validated OTTT behavior.


## FOIL, Progol, Popper: inductive logic programming (2026-11-04)

Primary references: Quinlan, *Learning Logical Definitions from Relations*, Machine Learning 5:239–266 (1990), https://courses.cs.washington.edu/courses/cse546/10wi/hw2/quinlan90.pdf ; Muggleton, *Inverse Entailment and Progol*, New Generation Computing 13:245–286 (1995), https://www.doc.ic.ac.uk/~shm/Papers/InvEnt.pdf ; Cropper & Morel, *Learning programs by learning from failures*, Machine Learning 110:801–856 (2021), https://link.springer.com/article/10.1007/s10994-020-05934-z . These are literature findings, not locally executed benchmarks.

- ILP induces logic program H from examples E and background knowledge B so that B∧H entails positives and not negatives, under assumptions. Unlike purely attribute-value classification, it can compose relations and learn recursion. Example: grandparent(X,Z) :- parent(X,Y), parent(Y,Z). Predicate semantics and data are supplied, not invented ex nihilo.
- FOIL (Quinlan 1990): top-down greedy addition of relational literals using information gain; can learn Horn clauses, including recursion in certain cases. Vulnerable to greedy local optima, supplied vocabulary and closed-world/negative-example assumptions.
- Progol (Muggleton 1995): mode-directed inverse entailment, builds a constrained bottom clause from an example/background and searches generalisations. Mode declarations/type/input-output restrictions shape candidate hypothesis space. Logical/syntactic validity is not a proof of physical reachability.
- Popper (Cropper/Morel 2021): generate -> test -> constrain. When candidate H is overgeneral (entails negatives), prune its generalisations; when underspecific (fails positives), prune its specialisations. Formally justified under stated assumptions; supports recursive definite programs and hypothesis-level constraints, combining ASP and Prolog. Published experiments in toy games, robot strategies, list transformations showed improved search time/accuracy relative to selected ILP baselines. Does not autonomously invent physical ontology or ensure causal truth from observations.
- OTTT comparison: ontology-informed combinatorial pruning; failure as information about *regions* of method/hypothesis space, not just one failed method. Separate (i) syntactic/type compatibility, (ii) physical/causal admissibility, (iii) technological feasibility with available actions, (iv) goal satisfaction. Preserve parent goal when method fails; ILP mainly induces rules, not automatically plans physical interventions.


## Causal discovery: Pearl, PC, FCI and interventions (2026-11-04)

Sources: Judea Pearl, *An Introduction to Causal Inference* (2010), https://pmc.ncbi.nlm.nih.gov/articles/PMC2836213/ ; Peter Spirtes and Kun Zhang, *Causal discovery and inference: concepts and recent methodological advances* (2016), https://link.springer.com/article/10.1186/s40535-016-0018-x ; Spirtes, *An Anytime Algorithm for Causal Inference* (2001), https://proceedings.mlr.press/r3/spirtes01a.html ; Spirtes, Glymour and Scheines, *Causation, Prediction, and Search*, https://www.cs.cmu.edu/afs/cs.cmu.edu/project/learn-43/lib/photoz/.g/web/.g/group/group2/g/scottd/fullbook.pdf . Literature study, not locally executed experiments.

- Pearl's three causal query levels: association P(Y|X=x), intervention P(Y|do(X=x)), counterfactuals conditional on actual evidence. Observational association is not equivalent to intervention effect; counterfactual claims generally require additional structural assumptions beyond interventional marginals.
- PC: conditional-independence tests prune a candidate graph and orient some edges; under causal Markov, faithfulness, acyclicity, causal sufficiency and reliable tests, outputs a Markov equivalence class (CPDAG), generally not a uniquely identified causal DAG. Assumptions are substantive, not automatically guaranteed by an ontology.
- FCI: allows latent common causes and selection bias, represents remaining uncertainty via partial ancestral graph (PAG); does not automatically identify the semantic nature of hidden causes. Worst-case complexity and finite-sample sensitivity remain significant.
- Distinguish: logical rule induction (FOIL/Progol/Popper) vs causal graph discovery (PC/FCI) vs intervention-effect identification (Pearl's SCM/do-calculus) vs executable goal-directed planning. These are complementary, not interchangeable.
- OTTT relevance: model action preconditions and effects as causal hypotheses with provenance/confidence; before searching methods, distinguish observed correlations from predicted intervention effects; treat failed interventions as evidence to update causal structure and prune classes of actions only when justified; revisit hidden variables/ontology when interventions violate predictions. Example: seized bolt may have rust, galling, thread deformation; diagnosis is uncertain. Goal-relative equivalence of turning/removing a bolt must honor constraints such as preservation of parts, safety and available tools. No guarantee a goal is reachable merely because not logically contradictory.


## Dual search: learn entities while pruning methods (2026-11-04)

User-derived architectural principle: while pursuing a goal, simultaneously (a) enrich and correct knowledge about the relevant entities, their properties, relations and causal mechanisms, and (b) reduce uncertainty about which methods can satisfy the goal. These are coupled processes, not a monotone guarantee that the set of known candidate methods shrinks. Discoveries may add previously unknown methods; disconfirmed assumptions may reinstate excluded methods. Distinguish total known method repertoire, currently admissible methods, and belief/confidence about method effectiveness.

Model action as (world state D_t, belief/knowledge state K_t) -> (D_{t+1}, K_{t+1}). An action may have no immediate external effect yet be useful diagnostically. Evaluate experiments both for goal progress and *task-relevant* information gain, not unbounded encyclopedic knowledge accumulation. Failures should update the causal model and prune only classes of methods excluded by justified constraints; preserve ability to retract erroneous constraints. Goal persistence (importance-linked) is separate from method persistence. Related fields: Bayesian experimental design, value of information, active causal learning, dual control.

## Research comparison: Bayesian experimental design, active causal discovery, dual control

- **Lindley (1956)**, *On a Measure of the Information Provided by an Experiment*, https://doi.org/10.1214/aoms/1177728425 : Bayesian information gain as expected posterior-versus-prior divergence. An experiment is chosen to discriminate hypotheses, not necessarily to accomplish the external task immediately. Selection depends on prior, likelihood and design constraints.
- **Chaloner & Verdinelli (1995)**, *Bayesian Experimental Design: A Review*, https://doi.org/10.1214/ss/1177009939 : expected utility of experiment under posterior predictive outcomes, including parameter information and decision-oriented criteria; maximising generic information is not necessarily optimal for task success.
- **Tong & Koller (2001)**, *Active Learning for Structure in Bayesian Networks*, https://ai.stanford.edu/~koller/Papers/Tong+Koller:IJCAI01.pdf : choose interventions to discriminate among candidate Bayesian-network structures; intervention target and possible outcomes matter. Model assumptions and ability to intervene are externally provided.
- **Hauser & Bühlmann (2012)**, *Characterization and Greedy Learning of Interventional Markov Equivalence Classes of Directed Acyclic Graphs*, https://jmlr.org/papers/v13/hauser12a.html : interventional data can distinguish DAGs observationally equivalent under assumptions; not unrestricted causal discovery.
- **Feldbaum (1960–1961)** dual control: actions simultaneously control a dynamic system and probe unknown dynamics. **Klenske & Hennig (2016)**, *Dual Control for Approximate Bayesian Reinforcement Learning*, https://jmlr.org/papers/v17/15-162.html : approximate Bayesian control trades off immediate reward and information useful for future control. Exploration is instrumental to reaching goals; no need to maximize information without relevance.

Critical distinctions for OTTT: hypothesis-space entropy vs action-space feasibility; intervention discovery vs decision-making; observability/identifiability vs reachability; an experiment may destroy or irreversibly alter an object, so physical safety and goal constraints are required. No guarantee that all task-relevant unknowns are identifiable or that a solvable task is recognizable as such in finite time. These are literature findings, not executed benchmarks or a decision to adopt any architecture.


## Ontological discipline: prevent phantom explanations (2026-11-04)

User principle: when available ontological explanations are exhausted, the system must not manufacture unsupported entities or mechanisms to close an explanatory gap. Preserve the explicit state **unknown / model incomplete**. Distinguish (1) established entities and causal relations, (2) hypotheses about latent entities or mechanisms, (3) untestable speculation; never promote (2) to (1) merely because it explains existing observations. The absence of a known explanation does not prove impossibility, nor does it prove the existence of an invented cause.

Candidate new concepts should have explicit provenance, independent empirical implications (preferably discriminating predictions), compatibility checks with established constraints, and tests capable of refutation or revision. Penalize ad hoc complexity but do not ban latent-variable discovery outright: novel entities can be scientifically legitimate if supported by discriminating evidence. Keep uncertainty calibrated and allow abstention rather than confabulation. In goal-directed action, don't plan irreversible interventions on unverified hypothetical mechanisms as if they were established facts. Research connections: abduction / inference to best explanation, model selection and minimum description length, Bayesian model comparison, open-world reasoning, epistemic logic and truth-maintenance systems. These are proposed OTTT requirements, not a validated implementation.


## Goal-sufficient ontological explanation by elimination (2026-11-04; user clarification)

The intended anti-phantom principle is **not** a blanket prohibition on novel latent hypotheses. Given a sufficiently constrained ontology, infer the most probable *existing mechanism class* by excluding alternatives, and proceed at the coarsest explanatory level sufficient for the goal. Example: a threaded bolt that does not rotate, given credible evidence of applied transmitted torque and absence of separate locks, is most plausibly resisting rotation due to mechanical interaction (friction, galling, corrosion-induced binding, deformation); the particular subtype need not be known to plan a next action. This is a defeasible, conditional inference, not a deductive proof that no other cause exists: inspect the torque transmission, object geometry and reliability of observations; distinguish mechanical equilibrium/insufficient net torque (condition) from the underlying source of resistance (cause).

Hierarchical confidence: high confidence in a broad mechanism class may coexist with low confidence in its specific subtype. The system should not invent an ad hoc entity when a supported explanation exists within the ontology. When all plausible hypotheses predict the same safe, goal-compatible next action, further diagnosis can have low decision value; if preservation/safety constraints differ, diagnosis remains necessary. This principle supersedes any interpretation of the prior 'ontological discipline' entry as requiring full causal identification or forced ontology expansion before action. Related literature to examine: abductive diagnosis, Reiter 1987 consistency-based diagnosis, de Kleer and Williams 1987 model-based diagnosis / GDE, ATMS and nonmonotonic reasoning.


## Model-based autonomy predecessors: GDE+, Livingstone, Burton, Remote Agent (2026-11-04)

Primary sources: Struss & Dressler (1989) GDE+ https://ijcai.org/proceedings/1989/211 ; Williams & Nayak (1996) Livingstone https://www.aiinternational.org/Library/AAAI/1996/aaai96-144.php ; Williams & Nayak (1997) Burton https://ijcai.org/proceedings/1997/170 ; Muscettola, Nayak, Pell & Williams (1998) Remote Agent https://www.sciencedirect.com/science/article/pii/S000437029800068X ; NASA JPL report (1999) https://www.jpl.nasa.gov/news/remote-agent-experiment-meets-all-objectives/ .

- GDE+ (Struss, Dressler, IJCAI 1989) enriches consistency-based GDE with explicit faulty-behavior models: simply relaxing constraints on a component marked faulty can produce logically consistent yet physically implausible diagnoses. Assumption of completeness of known fault modes should be explicit and revisable, preserving unknown-fault possibilities. Strong historical match for user's ontology-grounded elimination and anti-phantom requirement.
- Livingstone (Williams & Nayak 1996): component-based declarative finite-state/qualitative transition models, conflict-based mode identification and reconfiguration within reactive control. A shared model supports diagnosis and response; not an unrestricted learner of new ontologies.
- Burton (Williams & Nayak 1997): model-based reactive planner bridges identified current and desired target modes; offline compilation and constrained model classes support fast online control. Does not imply general planning completeness for arbitrary physics or concepts.
- NASA Deep Space 1 Remote Agent flight test May 1999 integrated planning/scheduling, executive, and Livingstone diagnosis/reconfiguration. NASA reports 35 hours total over two sessions, with simulated spacecraft equipment faults injected in actual flight (camera, sensor, electronics, thruster) and successful compensation. A real timing-related software issue prevented normal engine-off; Remote Agent supplied diagnostic clues, humans diagnosed/fixed handling, then experiment resumed. Distinguish simulated hardware failures from actual software bug and onboard autonomy from human ground intervention.
- OTTT: model component structure, normal and plausible faulty modes, action preconditions/effects and hierarchical goals; rank physically supported explanation classes, permit incomplete diagnosis when it does not change the preferred action; track model-completeness assumptions and do not infer novel causes from mere consistency. Known limitations: hand-built domain models, state-space complexity, incomplete sensing, and limited open-world concept discovery. Literature review only, no benchmark.


## Fundamental laws, qualitative physics and automated abstraction (2026-11-04)

Question: can a compact AI derive object behavior and feasible goal-directed transformations from mathematics, thermodynamics and general physical laws rather than storing many domain-specific scripts?

- Forbus (1984), *Qualitative Process Theory*, https://doi.org/10.1016/0004-3702(84)90038-9 : reusable process schemas (heat flow, liquid flow etc.), conditional activation, qualitative influences. Requires domain primitives and modeled processes; does not derive all physical laws from axioms.
- Kuipers (1986), *Qualitative Simulation*, https://doi.org/10.1016/0004-3702(86)90073-1 : QSIM generates qualitative behaviors from constraints, signs, landmarks and derivatives; may admit spurious qualitative behaviors; abstraction trades precision for computational tractability.
- Cyc (Lenat et al., since 1984): large explicit common-sense ontology and inference, a contrasting knowledge-rich strategy rather than deriving daily world knowledge solely from a few physical axioms.
- Schmidt & Lipson (2009), *Distilling Free-Form Natural Laws from Experimental Data*, https://doi.org/10.1126/science.1165893 : symbolic regression finds mathematical regularities/invariants from data; formulas alone do not establish causal mechanisms or semantic ontology.
- Udrescu & Tegmark (2020), *AI Feynman*, https://arxiv.org/abs/1905.11481 : symbolic regression guided by physics-inspired structure (dimensional analysis, symmetries, separability), reduces search, but requires candidate variables, data and operator repertoire.

Architectural interpretation (hypothesis, not validated design): distinguish (i) mathematics/logical machinery, (ii) empirical fundamental laws and conservation constraints, (iii) effective domain-level mechanisms (friction, phase changes, material properties), (iv) task-specific model and goals. Fundamental laws rule out many impossible transitions but rarely uniquely predict useful action without geometry, initial/boundary conditions, constitutive laws and scale-specific abstractions. Entropy of an isolated system is not a universal goal or measure of task success; open systems can locally organize while producing entropy elsewhere. Use hierarchical effective models and choose the least detailed level adequate for decision, with escalation when observations conflict. Dimensional consistency is necessary but not sufficient for physical truth. A purely bottom-up deduction from microscopic physics is usually computationally intractable for practical macroscopic planning. No universal autonomous ontology-from-physics system has been demonstrated by these predecessors.


## Copycat and Metacat: context-sensitive analogy and metacognition (2026-11-04)

Primary research: Melanie Mitchell, *Analogy-Making as Perception* (MIT Press, 1993), https://mitpress.mit.edu/9780262631863/analogy-making-as-perception/ ; Hofstadter & Mitchell (1994), *The Copycat Project: A Model of Mental Fluidity and Analogy-Making*, https://arxiv.org/abs/cond-mat/9409103 ; James B. Marshall, *Metacat: A Self-Watching Cognitive Architecture for Analogy-Making and High-Level Perception* (2002 dissertation), https://www.cs.pomona.edu/~jmarshall/metacat/ . References offered for study; do not claim that a live experimental replication was performed.

- Copycat: toy-domain analogies between short letter strings (e.g., abc -> abd; ijk -> ?). Distinct competing descriptions can imply distinct answers. Slipnet is a weighted, activation-spreading concept network; workspace holds provisional groups/bonds/correspondences; coderack schedules small stochastic codelets to construct, test and break structures. Context-sensitive concept activation influences perception and search. Temperature is an algorithmic control of stochasticity/coherence, not literal thermodynamics.
- Metacat (Marshall): extends the research programme with self-monitoring, episodic memory and representations of how analogies are made, enabling comparisons among analogies and strategies within a constrained domain.
- Crucial limitations: small hand-engineered letter-string microworld; concept vocabulary and codelet types largely designer-specified; no demonstration of general autonomous physical ontology, law derivation, robust causal inference or universal task planning. Distinguish apparent novelty in answers from truly creating new fundamental concepts.
- OTTT lesson: treat relevance/activation of ontological properties as task- and context-dependent; preserve competing interpretations; shift exploration intensity with evidence, not merely elapsed time; store not just action outcomes but abstract relational structure of successful/failed methods. Analogy should propose candidate transformations, while causal constraints and physical laws must validate them. Metacognitive strategy selection is complementary to (not a replacement for) model-based diagnosis and goal-directed planning.
