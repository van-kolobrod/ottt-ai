"""Empirical parameter search for unchanged tracker 5A. Run as a module with demo."""
from dataclasses import asdict
from itertools import product
import argparse
import json

from .attention import canonical, digest, timestamp
from .identity import VERSION as TRACKER_VERSION, add_frame, configuration, match_components, track
from .identity_data import VERSION as GENERATOR_VERSION, dataset_splits
from .perception import extract_components
from .store import Memory


VERSION = "identity_learning_5b_v1"
TUNABLE = ("max_speed", "max_area_change", "max_shape_change")
GRID = {"max_speed": (2., 3., 5.), "max_area_change": (.6, .8), "max_shape_change": (.6, .8, .9)}
LOSS_WEIGHTS = {"false_matches": 10., "missed_decisive": 1., "avoidable_unknown": .5}


def empty_metrics():
    return dict(correct_matches=0, false_matches=0, missed_correspondences=0,
                missed_decisive=0, justified_unknown=0, avoidable_unknown=0,
                unknown_negative_pairs=0, true_correspondences=0, transitions=0)


def loss(metrics):
    return sum(metrics[key]*weight for key, weight in LOSS_WEIGHTS.items())


def _labels(components, controls):
    occupancy = {tuple(cell): entity for entity, cells in controls.items() for cell in cells}
    result = {}
    for component in components:
        identities = {occupancy.get(tuple(cell)) for cell in component["cells"]}
        if None in identities or len(identities) != 1:
            raise ValueError("Control labeling does not resolve a single synthetic object")
        result[component["id"]] = identities.pop()
    return result


def score_transition(comparison, left_labels, right_labels, ambiguous=False):
    metrics = empty_metrics()
    metrics["transitions"] = 1
    states = {(pair["from_component"], pair["to_component"]): pair["status"]
              for pair in comparison["pairs"]}
    for left, identity in left_labels.items():
        for right, other in right_labels.items():
            state = states.get((left, right), "unknown_identity")
            truth = identity == other
            if state == "same_entity":
                metrics["correct_matches" if truth else "false_matches"] += 1
            elif truth:
                metrics["missed_correspondences"] += 1
                if state == "unknown_identity":
                    metrics["justified_unknown" if ambiguous else "avoidable_unknown"] += 1
                else:
                    metrics["missed_decisive"] += 1
            elif state == "unknown_identity":
                metrics["unknown_negative_pairs"] += 1
            metrics["true_correspondences"] += int(truth)
    return metrics


def evaluate(sequences, config):
    config = configuration(config)
    totals = empty_metrics()
    details = []
    for sequence in sequences:
        # The tracker receives only existing perception outputs and elapsed time.
        components = [extract_components(frame.signal) for frame in sequence.frames]
        sequence_metrics = empty_metrics()
        for index in range(1, len(sequence.frames)):
            interval = (timestamp(sequence.frames[index].occurred_at)-
                        timestamp(sequence.frames[index-1].occurred_at)).total_seconds()
            comparison = match_components(components[index-1], components[index], interval, config)
            # Independent labels are consulted only after ordinary matching finishes.
            metrics = score_transition(comparison, _labels(components[index-1], sequence.controls[index-1]),
                                       _labels(components[index], sequence.controls[index]),
                                       index in sequence.ambiguous_transitions)
            for key in totals:
                totals[key] += metrics[key]
                sequence_metrics[key] += metrics[key]
        details.append({"seed": sequence.seed, "scenario": sequence.scenario,
                        "metrics": sequence_metrics})
    return {"metrics": totals, "loss": loss(totals), "per_sequence": details}


def parameter_grid():
    return [configuration(dict(zip(TUNABLE, values)))
            for values in product(*(GRID[key] for key in TUNABLE))]


def describe(splits):
    return {name: [{"seed": s.seed, "scenario": s.scenario, "content_hash": digest(asdict(s))}
                   for s in rows] for name, rows in splits.items()}


def fit(training, validation, candidates=None):
    if not training or not validation:
        raise ValueError("Both training and validation data are required")
    if {s.seed for s in training} & {s.seed for s in validation}:
        raise ValueError("Training and validation seeds overlap")
    baseline = configuration()
    candidates = [baseline] + (parameter_grid() if candidates is None else list(candidates))
    unique = {canonical(configuration(config)): configuration(config) for config in candidates}
    scores = []
    for key, config in sorted(unique.items()):
        if any(config[name] != baseline[name] for name in baseline if name not in TUNABLE):
            raise ValueError("Search may only alter the declared tunable parameters")
        result = evaluate(training, config)
        scores.append({"config": config, "training": result})
    best_loss = min(row["training"]["loss"] for row in scores)
    finalists = [row for row in scores if row["training"]["loss"] == best_loss]
    for row in finalists:
        row["validation"] = evaluate(validation, row["config"])
    # Validation resolves training ties. Baseline/fewer changes wins otherwise equal results.
    selected = min(finalists, key=lambda row: (
        row["validation"]["loss"], sum(row["config"][key] != baseline[key] for key in TUNABLE),
        canonical(row["config"])))
    return {"algorithm_version": VERSION, "tracker_version": TRACKER_VERSION,
            "baseline_config": baseline, "selected_config": selected["config"],
            "selection": "baseline_retained" if selected["config"] == baseline else "adapted",
            "selection_rule": "minimum training loss; validation breaks ties; fewer changed parameters then canonical order",
            "loss_weights": LOSS_WEIGHTS, "search_scores": scores,
            "baseline_training": next(row["training"] for row in scores if row["config"] == baseline),
            "baseline_validation": evaluate(validation, baseline),
            "selected_training": selected["training"], "selected_validation": selected["validation"]}


def experiment(splits=None, candidates=None):
    splits = dataset_splits() if splits is None else splits
    if any({s.seed for s in splits[a]} & {s.seed for s in splits[b]}
           for a, b in (("training", "validation"), ("training", "test"), ("validation", "test"))):
        raise ValueError("Dataset splits overlap")
    if not splits["test"]:
        raise ValueError("Independent test data is required")
    fitted = fit(splits["training"], splits["validation"], candidates)
    before = evaluate(splits["test"], fitted["baseline_config"])
    after = evaluate(splits["test"], fitted["selected_config"])
    return {**fitted, "generator_version": GENERATOR_VERSION,
            "dataset_description": describe(splits),
            "test_baseline": before, "test_selected": after,
            "test_outcome": "improved" if after["loss"] < before["loss"] else
                            "worse" if after["loss"] > before["loss"] else "no_improvement"}


def persist_experiment(memory, result, splits):
    if result["dataset_description"] != describe(splits):
        raise ValueError("Result and labeled dataset do not match")
    frame_ids = []
    descriptions = []
    # Stable input description permits replay without duplicating sensor events.
    description = {"version": VERSION, "generator_version": GENERATOR_VERSION, "sequences": {
        name: [asdict(sequence) for sequence in rows] for name, rows in splits.items()}}
    dataset_key = digest(description)
    for row in memory.db.execute("SELECT id,payload FROM events WHERE kind='identity_training_dataset'"):
        payload = json.loads(row["payload"])
        if payload["dataset_key"] == dataset_key:
            frame_ids = payload["frame_ids"]
            dataset_id = row["id"]
            break
    else:
        for role, sequences in splits.items():
            for sequence in sequences:
                ids = [add_frame(memory, frame.signal, frame.occurred_at, source="synthetic_identity_sensor")
                       for frame in sequence.frames]
                frame_ids.extend(ids)
                descriptions.append({"role": role, "seed": sequence.seed, "scenario": sequence.scenario,
                                     "frame_ids": ids, "controls": sequence.controls,
                                     "ambiguous_transitions": sequence.ambiguous_transitions})
        dataset_id = memory.add("identity_training_dataset", {
            "dataset_key": dataset_key, "generator_version": GENERATOR_VERSION,
            "sequences": descriptions, "frame_ids": frame_ids,
            "control_note": "Independent synthetic labels; never tracker inputs"},
            source=VERSION, links=[("evidence", eid) for eid in frame_ids])
    study_key = digest({"version": VERSION, "dataset_id": dataset_id, "result": result})
    with memory.db:
        memory.db.execute("BEGIN IMMEDIATE")
        for row in memory.db.execute("SELECT id,payload FROM events WHERE kind='identity_parameter_study'"):
            if json.loads(row["payload"]).get("study_key") == study_key:
                return row["id"]
        return memory.add("identity_parameter_study", {**result, "study_key": study_key},
                          source=VERSION, parent_id=dataset_id,
                          links=[("evidence", eid) for eid in frame_ids]+[("evaluates", dataset_id)])


def demo(path=":memory:"):
    splits = dataset_splits()
    result = experiment(splits)
    print("metric | baseline | adapted")
    for key, value in result["test_baseline"]["metrics"].items():
        print(f"{key} | {value} | {result['test_selected']['metrics'][key]}")
    print("weighted_loss |", result["test_baseline"]["loss"], "|", result["test_selected"]["loss"])
    print("selected_parameters:", {key: result["selected_config"][key] for key in TUNABLE})
    print("test_outcome:", result["test_outcome"])
    print("scenario | baseline_loss | adapted_loss")
    for scenario in sorted({row["scenario"] for row in result["test_baseline"]["per_sequence"]}):
        print(scenario, "|", sum(loss(row["metrics"]) for row in result["test_baseline"]["per_sequence"]
                                  if row["scenario"] == scenario),
              "|", sum(loss(row["metrics"]) for row in result["test_selected"]["per_sequence"]
                       if row["scenario"] == scenario))
    memory = Memory(path)
    try:
        study_id = persist_experiment(memory, result, splits)
        dataset = memory.get(memory.get(study_id)["parent_id"])["payload"]
        for sequence in dataset["sequences"]:
            if (sequence["role"] != "test" or sequence["seed"] != 211 or
                    sequence["scenario"] not in ("reshape", "crossing")):
                continue
            ids = sequence["frame_ids"]
            for label, config in (("baseline", result["baseline_config"]), ("adapted", result["selected_config"])):
                run = track(memory, ids, config)
                states = [[pair["status"] for pair in memory.get(eid)["payload"]["pairs"]]
                          for eid in run["matching_ids"]]
                print(sequence["scenario"], label, states)
    finally:
        memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--db", default=":memory:")
    demo(parser.parse_args().db)
