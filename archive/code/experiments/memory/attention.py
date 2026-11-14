"""Research attention 4A, adapted from C:/OTTT-AI/ottt_attention_v1.py.

Retains transparent weighted assessment, eligibility gates, abstention and stable
tie breaking. Adds memory-derived candidates and measurable scoring inputs.
Run: python -m experiments.memory.attention demo
"""
from dataclasses import asdict, dataclass
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
import argparse
import hashlib
import json
import math

from .store import Memory


VERSION = "research_attention_4a_v1"
WEIGHTS = {
    "exploratory": dict(novelty=.25, recurrence=.20, explanatory_power=.20,
                        testability=.15, evidence_strength=.10, affordability=.10,
                        relevance=0),
    "goal_directed": dict(novelty=.05, recurrence=.05, explanatory_power=.10,
                          testability=.10, evidence_strength=.10, affordability=.05,
                          relevance=.55),
}
THRESHOLD = .60
GENERATION = {"rare_min_comparable": 4, "rare_min_marginal": 2, "rare_max_frequency": .25}
GATES = {"min_evidence_ids": 2, "min_testability": .35, "min_observation_coverage": .25}
METRIC_DEFINITIONS = {
    "novelty": "Sample rarity: repeated=1-support/N; rare=1-support/expected; conflict=1-dominant_value_count/object_feature_count.",
    "recurrence": "repeated=support/N; rare=min(marginal_counts)/comparable_count; conflict=2/object_feature_count.",
    "explanatory_power": "Proxy only: evidence observation count / feature-bearing observation count N.",
    "testability": "Proxy only: fraction of evidence observations carrying a source ID.",
    "evidence_strength": "Distinct nonempty source IDs / evidence count; does not establish source independence.",
    "affordability": "N/(N+evidence_count); cost proxy is the number of records to inspect, not runtime or external experiment cost.",
    "relevance": "Number of candidate feature names explicitly listed by the goal / number of candidate feature names.",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def observations(memory):
    """Read all primary observations, including archived ones; never decisions."""
    return [memory.get(row[0]) for row in memory.db.execute(
        "SELECT id FROM events WHERE kind='observation' ORDER BY id").fetchall()]


def scalar_features(event):
    payload = event["payload"]
    features = payload.get("features", {}) if isinstance(payload, dict) else {}
    if not isinstance(features, dict):
        return {}
    return {key: int(value) if isinstance(value, float) and value.is_integer() else value
            for key, value in features.items()
            if isinstance(key, str) and key and value is not None
            and isinstance(value, (str, bool, int, float))
            and (not isinstance(value, float) or math.isfinite(value))}


def timestamp(value):
    try:
        time = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return time.astimezone(timezone.utc) if time.tzinfo else None
    except (AttributeError, ValueError):
        return None


@dataclass(frozen=True)
class Candidate:
    id: str
    type: str
    question: str
    evidence_ids: tuple
    features: dict
    measurements: dict
    metrics: dict
    verification: str
    uncertainty: tuple


def build_candidate(kind, features, evidence, population, novelty, recurrence,
                    measurements, question, verification, uncertainty=()):
    evidence = sorted(evidence, key=lambda event: event["id"])
    ids = tuple(event["id"] for event in evidence)
    count = len(ids)
    sources = {event["source"] for event in evidence if event["source"]}
    metrics = dict(
        novelty=novelty, recurrence=recurrence,
        explanatory_power=count / population,
        testability=sum(bool(event["source"]) for event in evidence) / count,
        evidence_strength=len(sources) / count,
        affordability=population / (population + count),
    )
    measurements = {**measurements, "population_size": population,
                    "evidence_count": count, "source_count": len(sources),
                    "estimated_record_reads": count}
    identity = dict(type=kind, features=features, evidence_ids=ids,
                    measurements=measurements, uncertainty=uncertainty)
    return Candidate(digest(identity), kind, question, ids, features, measurements,
                     metrics, verification, tuple(uncertainty))


def generate_candidates(events):
    """Only infer research questions about explicit scalar feature records."""
    records = [(event, scalar_features(event)) for event in events]
    records = [(event, features) for event, features in records if features]
    n = len(records)
    if not n:
        return []
    candidates = []
    groups = {}
    for event, features in records:
        for key, value in sorted(features.items()):
            groups.setdefault((key, canonical(value)), []).append(event)
    for (key, encoded), evidence in sorted(groups.items()):
        if len(evidence) < 2:
            continue
        support = len(evidence)
        candidates.append(build_candidate(
            "repeated_property", {key: json.loads(encoded)}, evidence, n,
            1 - support / n, support / n, {"support_count": support},
            f"Why does {key}={encoded} recur in different observations?",
            "Collect independent observations; compare frequency across objects, times and sources."))

    keys = sorted({key for _, features in records for key in features})
    for first, second in combinations(keys, 2):
        comparable = [(event, features) for event, features in records
                      if first in features and second in features]
        total = len(comparable)
        if total < GENERATION["rare_min_comparable"]:
            continue
        pairs = {}
        for event, features in comparable:
            pair = (canonical(features[first]), canonical(features[second]))
            pairs.setdefault(pair, []).append(event)
        for (a, b), supporting in sorted(pairs.items()):
            count_a = sum(canonical(f[first]) == a for _, f in comparable)
            count_b = sum(canonical(f[second]) == b for _, f in comparable)
            expected = count_a * count_b / total
            support = len(supporting)
            # Rare relative to frequent marginal properties and their independence baseline.
            if (min(count_a, count_b) < GENERATION["rare_min_marginal"] or
                    support / total > GENERATION["rare_max_frequency"] or support >= expected):
                continue
            candidates.append(build_candidate(
                "rare_combination", {first: json.loads(a), second: json.loads(b)},
                [event for event, _ in comparable], n,
                1 - support / expected, min(count_a, count_b) / total,
                {"support_count": support, "support_ids": sorted(e["id"] for e in supporting),
                 "comparable_count": total, "marginal_counts": [count_a, count_b],
                 "expected_count_under_independence": expected},
                f"Why is the combination {first}={a}, {second}={b} relatively rare?",
                "Collect more paired measurements; test the independence baseline and sampling bias."))

    objects = {}
    for event, features in records:
        obj = event["payload"].get("object_id")
        if not isinstance(obj, str) or not obj:
            continue
        for key, value in features.items():
            objects.setdefault((obj, key), []).append((event, value))
    for (obj, key), values in sorted(objects.items()):
        value_counts = Counter(canonical(value) for _, value in values)
        for (left, a), (right, b) in combinations(values, 2):
            if canonical(a) == canonical(b):
                continue
            ta, tb = timestamp(left["occurred_at"]), timestamp(right["occurred_at"])
            uncertainty = []
            if ta is None or tb is None:
                uncertainty.append("insufficient_time_context")
            elif ta != tb:
                uncertainty.append("possible_state_change_between_times")
            if not left["source"] or not right["source"]:
                uncertainty.append("missing_source")
            elif left["source"] == right["source"]:
                uncertainty.append("same_source_not_independent")
            candidates.append(build_candidate(
                "potential_contradiction", {key: [a, b]}, [left, right], n,
                1 - max(value_counts.values()) / len(values), 2 / len(values),
                {"object_id": obj, "occurred_at": [left["occurred_at"], right["occurred_at"]],
                 "sources": [left["source"], right["source"]],
                 "context_status": "uncertain" if uncertainty else "simultaneous_source_disagreement"},
                f"Do the different values of {key} for {obj} reflect a source disagreement or state change?",
                "Verify object identity, timestamp precision, measurement context and source reliability; repeat measurement.",
                uncertainty))
    return sorted(candidates, key=lambda candidate: candidate.id)


def assess(candidate, *, mode="exploratory", goal_features=()):
    metrics = {**candidate.metrics,
               "relevance": len(set(candidate.features) & set(goal_features)) / len(candidate.features)}
    for key, value in metrics.items():
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{candidate.id}.{key} must be finite in [0,1]")
    reasons = []
    if len(set(candidate.evidence_ids)) < GATES["min_evidence_ids"]:
        reasons.append("insufficient_evidence_ids")
    if metrics["testability"] < GATES["min_testability"]:
        reasons.append("insufficient_provenance_for_testing")
    if metrics["explanatory_power"] < GATES["min_observation_coverage"]:
        reasons.append("low_observation_coverage")
    if candidate.uncertainty:
        reasons.extend(candidate.uncertainty)
    if mode == "goal_directed" and metrics["relevance"] == 0:
        reasons.append("not_relevant_to_goal_features")
    contributions = {key: value * WEIGHTS[mode][key] for key, value in metrics.items()}
    return {"id": candidate.id, "score": sum(contributions.values()),
            "eligible": not reasons, "reasons": reasons, "metrics": metrics,
            "weighted_contributions": contributions,
            "evidence_ids": list(candidate.evidence_ids)}


def choose(candidates, *, mode="exploratory", goal=None, threshold=THRESHOLD):
    if mode not in WEIGHTS:
        raise ValueError("Unknown attention mode")
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite in [0,1]")
    goal = goal or {}
    if not isinstance(goal, dict):
        raise ValueError("Goal must be an object with explicit feature names")
    goal_features = goal.get("features", [])
    if (not isinstance(goal_features, list) or
            any(not isinstance(key, str) or not key for key in goal_features)):
        raise ValueError("Goal features must be a list of nonempty feature names")
    if mode == "goal_directed" and not goal_features:
        raise ValueError("Goal-directed attention requires explicit goal features")
    if mode == "exploratory" and goal:
        raise ValueError("Exploratory mode does not take an external goal")
    if len({candidate.id for candidate in candidates}) != len(candidates):
        raise ValueError("Candidate IDs must be unique")
    assessments = sorted((assess(c, mode=mode, goal_features=goal_features) for c in candidates),
                         key=lambda assessment: (-assessment["score"], assessment["id"]))
    for assessment in assessments:
        assessment["meets_threshold"] = assessment["score"] >= threshold
    qualified = [a for a in assessments if a["eligible"] and a["score"] >= threshold]
    return {"mode": mode, "goal": goal, "algorithm_version": VERSION,
            "threshold": threshold, "weights": WEIGHTS[mode],
            "metric_definitions": METRIC_DEFINITIONS,
            "eligibility_gates": GATES, "generation_config": GENERATION,
            "candidates": [asdict(c) for c in candidates], "assessments": assessments,
            "selected_id": qualified[0]["id"] if qualified else None,
            "reason": "highest_scoring_eligible_candidate" if qualified
                      else "no_candidate_passed_evidence_quality_and_score_gates",
            "score_meaning": "Heuristic research priority, not probability of truth."}


def attend(memory, *, mode="exploratory", goal=None, threshold=THRESHOLD):
    events = observations(memory)
    decision = choose(generate_candidates(events), mode=mode, goal=goal, threshold=threshold)
    # Identity uses the complete primary event snapshot, mode, goal and assessment configuration.
    snapshot = [{key: e[key] for key in ("id", "payload", "source", "occurred_at")}
                for e in events]
    key = digest({"observations": snapshot, "version": VERSION, "mode": mode,
                  "goal": decision["goal"], "threshold": threshold, "weights": WEIGHTS[mode],
                  "generation": GENERATION, "gates": GATES})
    with memory.db:
        memory.db.execute("BEGIN IMMEDIATE")
        for row in memory.db.execute("SELECT id,payload FROM events WHERE kind='research_decision'"):
            if json.loads(row["payload"]).get("decision_key") == key:
                return row["id"]
        decision["decision_key"] = key
        decision["input_observation_ids"] = [event["id"] for event in events]
        decision["supported_observation_ids"] = [e["id"] for e in events if scalar_features(e)]
        decision["unsupported_observation_ids"] = [e["id"] for e in events if not scalar_features(e)]
        event_id = memory.add("research_decision", decision, source=VERSION,
                              concepts=["research_attention", mode],
                              links=[("considers", event["id"]) for event in events])
    return event_id


def demo(path=":memory:"):
    memory = Memory(path)
    try:
        # Frequent properties also yield a rare pair; the target feature is goal-relevant.
        for index in range(5):
            memory.add("observation", {"features": {
                "stable": True, "target": index < 2,
                "color": "red" if index < 3 else "blue",
                "surface": "smooth" if index in (0, 3, 4) else "rough"}},
                source=f"sensor-{index}")
        for mode, goal in (("exploratory", None), ("goal_directed", {"features": ["target"]})):
            event_id = attend(memory, mode=mode, goal=goal)
            decision = memory.get(event_id)["payload"]
            selected = next((c for c in decision["candidates"] if c["id"] == decision["selected_id"]), None)
            print(json.dumps({"mode": mode, "selected": selected,
                              "assessment": next((a for a in decision["assessments"]
                                                  if a["id"] == decision["selected_id"]), None),
                              "considered_candidates": len(decision["candidates"]),
                              "reason": decision["reason"]}, ensure_ascii=False, indent=2))
    finally:
        memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--db", default=":memory:")
    demo(parser.parse_args().db)
