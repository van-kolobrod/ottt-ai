"""Bounded numerical research cycle 4B. Run with python -m experiments.memory.research demo."""
import argparse
import json
import math

from experiments.discovery_symbolic import Researcher, grammar
from .attention import choose, digest, generate_candidates, observations
from .store import Memory


VERSION = "numerical_research_4b_v1"
DEFAULT_CONFIG = {"min_training": 3, "min_holdout": 2, "top_k": 3,
                  "absolute_tolerance": 1e-8, "relative_tolerance": 1e-6}
EQUIVALENCE_PROBES = (.73, 1.31, 2.71, 5.13)


def numeric_observations(memory, series, independent, dependent):
    records = []
    for event in observations(memory):
        payload = event["payload"]
        if not isinstance(payload, dict) or payload.get("series_id", "default") != series:
            continue
        features = payload.get("features", {})
        if not isinstance(features, dict):
            continue
        pair = [features.get(key) for key in (independent, dependent)]
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) for value in pair):
            continue
        records.append(event)
    return sorted(records, key=lambda event: (event["recorded_at"], event["id"]))


def _events(memory, kind, parent=None):
    sql = "SELECT id FROM events WHERE kind=?"
    args = [kind]
    if parent is not None:
        sql += " AND parent_id=?"
        args.append(parent)
    sql += " ORDER BY recorded_at,id"
    return [memory.get(row[0]) for row in memory.db.execute(sql, args).fetchall()]


def _once(memory, kind, payload, evidence_ids, parent=None, links=()):
    """Append an event with atomic evidence links; resume safely after interruption."""
    evidence_ids = sorted(set(evidence_ids))
    payload = {**payload, "algorithm_version": VERSION, "evidence_ids": evidence_ids}
    key = digest({"kind": kind, "parent": parent, "payload": payload})
    with memory.db:
        memory.db.execute("BEGIN IMMEDIATE")
        for event in _events(memory, kind, parent):
            if event["payload"].get("event_key") == key:
                return event["id"]
        return memory.add(kind, {**payload, "event_key": key}, parent_id=parent,
                          source=VERSION, concepts=["numerical_research"],
                          links=[("evidence", eid) for eid in evidence_ids] + list(links))


def _config(config):
    result = {**DEFAULT_CONFIG, **(config or {})}
    if set(result) != set(DEFAULT_CONFIG):
        raise ValueError("Unknown research configuration")
    for key in ("min_training", "min_holdout", "top_k"):
        if type(result[key]) is not int or result[key] < (3 if key == "min_training" else 1):
            raise ValueError(f"Invalid {key}")
    for key in ("absolute_tolerance", "relative_tolerance"):
        if not isinstance(result[key], (int, float)) or not math.isfinite(result[key]) or result[key] < 0:
            raise ValueError(f"Invalid {key}")
    return result


def _question(memory, records, series, independent, dependent, config):
    research_key = digest({"series": series, "independent": independent,
                           "dependent": dependent, "config": config, "version": VERSION})
    for event in reversed(_events(memory, "research_question")):
        if event["payload"].get("research_key") == research_key:
            if (len(event["payload"]["training_ids"]) >= config["min_training"] or
                    len(records) <= len(event["payload"]["training_ids"])):
                return event
    # Record-time split; neither expression ranking nor attention sees holdout labels.
    size = min(len(records), max(config["min_training"], len(records) * 2 // 3))
    training = records[:size]
    attention = choose(generate_candidates(training), mode="goal_directed",
                       goal={"features": [independent, dependent]})
    selected = next((candidate for candidate in attention["candidates"]
                     if candidate["id"] == attention["selected_id"]), None)
    suitable = selected is not None and set(selected["features"]) <= {independent, dependent}
    event_id = _once(memory, "research_question", {
        "research_key": research_key, "series_id": series,
        "independent": independent, "dependent": dependent, "config": config,
        "question": f"Which bounded symbolic expression predicts {dependent} from {independent}?",
        "direction_origin": "explicit x/y field contract; not inferred causality",
        "question_origin": "attention_adapter" if suitable else "numeric_dependency_adapter",
        "attention_decision": attention,
        "training_ids": [event["id"] for event in training],
        "split_method": "first max(min_training,floor(2*N/3)) records by recorded_at,id; frozen thereafter",
    }, [event["id"] for event in training])
    return memory.get(event_id)


def _propose(memory, question, records):
    existing = _events(memory, "hypothesis", question["id"])
    if existing and len(existing) == existing[0]["payload"]["batch_size"]:
        return sorted(existing, key=lambda event: event["payload"]["rank"])
    q = question["payload"]
    ids = q["training_ids"]
    by_id = {event["id"]: event for event in records}
    training = [by_id[eid] for eid in ids]
    if len(training) < q["config"]["min_training"]:
        return []
    researcher = Researcher(measure=None)
    researcher.data = [(event["payload"]["features"][q["independent"]],
                        event["payload"]["features"][q["dependent"]]) for event in training]
    ranked = []
    signatures = set()
    for candidate in researcher.hypotheses():
        score, mse, expression, a, b = candidate
        if not all(math.isfinite(value) for value in (score, mse, a, b)):
            continue
        try:
            signature = tuple(round(a*expression.fn(x)+b, 9) for x in EQUIVALENCE_PROBES)
        except (ValueError, OverflowError, ZeroDivisionError):
            continue
        if not all(math.isfinite(value) for value in signature) or signature in signatures:
            continue
        signatures.add(signature)
        ranked.append(candidate)
        if len(ranked) == q["config"]["top_k"]:
            break
    hypotheses = []
    for rank, (score, mse, expression, a, b) in enumerate(ranked, 1):
        event_id = _once(memory, "hypothesis", {
            "state": "proposed", "expression": expression.name,
            "formula": f"{q['dependent']} = a * {expression.name} + b",
            "parameters": {"a": a, "b": b}, "rank": rank, "batch_size": len(ranked),
            "training_normalized_mse": mse, "ranking_score": score,
            "complexity": expression.complexity,
            "ranking_criterion": "training normalized MSE + 1e-12 * expression complexity",
            "equivalence_filter": {"fixed_probe_x": EQUIVALENCE_PROBES, "round_digits": 9,
                                   "note": "Computational probes only, not held-out measurements or a proof of equivalence."},
            "independent": q["independent"], "dependent": q["dependent"],
            "training_ids": ids,
            "domain": {"series_id": q["series_id"],
                       "training_x_min": min(x for x, _ in researcher.data),
                       "training_x_max": max(x for x, _ in researcher.data),
                       "scope": "finite observed inputs where expression is defined; no universal law claim"},
        }, ids, parent=question["id"])
        hypotheses.append(memory.get(event_id))
    return hypotheses


def _check(memory, hypothesis, holdout, config):
    h = hypothesis["payload"]
    previous = _events(memory, "hypothesis_result", hypothesis["id"])
    ids = [event["id"] for event in holdout]
    prior = next((event for event in reversed(previous)
                  if event["payload"]["holdout_ids"] != ids), None)
    evidence = h["training_ids"] + ids
    checking_id = _once(memory, "hypothesis_check", {"state": "testing", "holdout_ids": ids},
                        evidence, parent=hypothesis["id"])
    expression = next(e for e in grammar() if e.name == h["expression"])
    predictions = []
    for event in holdout:
        features = event["payload"]["features"]
        x, actual = features[h["independent"]], features[h["dependent"]]
        tolerance = config["absolute_tolerance"] + config["relative_tolerance"] * abs(actual)
        try:
            predicted = h["parameters"]["a"] * expression.fn(x) + h["parameters"]["b"]
            error = predicted - actual
            if not all(math.isfinite(value) for value in (predicted, error, tolerance)):
                raise ValueError("nonfinite_prediction_or_error")
            result = {"predicted": predicted, "signed_error": error,
                      "absolute_error": abs(error), "passed": abs(error) <= tolerance}
        except (ValueError, OverflowError, ZeroDivisionError):
            result = {"predicted": None, "signed_error": None, "absolute_error": None,
                      "passed": False, "reason": "expression_undefined_or_nonfinite"}
        predictions.append({"observation_id": event["id"], "x": x, "actual": actual,
                            "tolerance": tolerance, **result})
    state = ("inconclusive" if len(holdout) < config["min_holdout"] else
             "supported" if all(item["passed"] for item in predictions) else "refuted")
    result_id = _once(memory, "hypothesis_result", {
        "state": state, "holdout_ids": ids, "predictions": predictions,
        "checking_event_id": checking_id, "criterion": config,
        "decision_rule": "insufficient holdout => inconclusive; otherwise all errors <= abs_tol+rel_tol*abs(actual) => supported; else refuted",
        "reason": "insufficient_holdout" if state == "inconclusive" else "held_out_prediction_test",
    }, evidence, parent=hypothesis["id"], links=[("completes", checking_id)])
    if prior and prior["payload"]["state"] != state:
        _once(memory, "hypothesis_revision", {
            "from_state": prior["payload"]["state"], "to_state": state,
            "previous_result_id": prior["id"], "new_result_id": result_id,
            "new_evidence_ids": [eid for eid in ids if eid not in prior["payload"]["holdout_ids"]],
        }, evidence, parent=hypothesis["id"],
            links=[("revises", prior["id"]), ("based_on", result_id)])
    return result_id


def research(memory, *, series="default", independent="x", dependent="y", config=None):
    if not all(isinstance(value, str) and value for value in (series, independent, dependent)):
        raise ValueError("Series and variable names must be nonempty strings")
    if independent == dependent:
        raise ValueError("Dependent and independent variables must differ")
    config = _config(config)
    records = numeric_observations(memory, series, independent, dependent)
    question = _question(memory, records, series, independent, dependent, config)
    hypotheses = _propose(memory, question, records)
    if not hypotheses:
        result_id = _once(memory, "research_result", {
            "state": "inconclusive", "reason": "insufficient_training_or_no_identifiable_expression",
        }, [event["id"] for event in records], parent=question["id"])
        return {"question_id": question["id"], "selected_hypothesis_id": None,
                "hypothesis_ids": [], "result_ids": [result_id]}
    training_ids = set(question["payload"]["training_ids"])
    holdout = [event for event in records if event["id"] not in training_ids]
    results = [_check(memory, hypothesis, holdout, config) for hypothesis in hypotheses]
    return {"question_id": question["id"], "selected_hypothesis_id": hypotheses[0]["id"],
            "hypothesis_ids": [h["id"] for h in hypotheses], "result_ids": results}


def demo():
    for label, size, changed in (("stable", 8, False), ("false_pattern", 8, True), ("insufficient", 4, False)):
        memory = Memory(":memory:")
        try:
            for x in range(1, size + 1):
                y = 2 * x if not changed or x <= 5 else 2 * x + 10
                memory.add("observation", {"features": {"x": x, "y": y}}, source="synthetic_demo")
            run = research(memory)
            selected = memory.get(run["hypothesis_ids"][0])["payload"]
            result = memory.get(run["result_ids"][0])["payload"]
            print(json.dumps({"scenario": label, "expression": selected["expression"],
                              "parameters": selected["parameters"], "state": result["state"],
                              "train_count": len(selected["training_ids"]),
                              "holdout_count": len(result["holdout_ids"]),
                              "competing_hypotheses": [
                                  {"expression": memory.get(hid)["payload"]["expression"],
                                   "parameters": memory.get(hid)["payload"]["parameters"],
                                   "training_normalized_mse": memory.get(hid)["payload"]["training_normalized_mse"],
                                   "state": memory.get(rid)["payload"]["state"]}
                                  for hid, rid in zip(run["hypothesis_ids"], run["result_ids"])]}, indent=2))
            if label == "stable":
                memory.add("observation", {"features": {"x": 9, "y": 999}}, source="new_demo_evidence")
                revised = research(memory)
                print("After new evidence:", memory.get(revised["result_ids"][0])["payload"]["state"])
        finally:
            memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo"])
    parser.parse_args()
    demo()
