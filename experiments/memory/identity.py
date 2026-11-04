"""Bounded global component tracking, experiment 5A. Run as a module with demo."""
import argparse
import json
import math
import uuid

from .attention import digest, timestamp
from .perception import validate_field
from .spatial import perceive_event
from .store import Memory


VERSION = "entity_identity_5a_v1"
DEFAULT_CONFIG = {"max_speed": 3.0, "min_interval": .001, "max_interval": 5.0,
                  "max_area_change": .6, "max_shape_change": .6,
                  "max_pair_cost": .8, "ambiguity_margin": .15, "max_components": 6,
                  "weights": {"distance": .45, "area": .15, "dimensions": .15,
                              "shape": .20, "signal": .05}}


def configuration(overrides=None):
    config = {**DEFAULT_CONFIG, **(overrides or {})}
    config["weights"] = {**DEFAULT_CONFIG["weights"], **config["weights"]}
    if set(config) != set(DEFAULT_CONFIG) or set(config["weights"]) != set(DEFAULT_CONFIG["weights"]):
        raise ValueError("Unknown identity configuration")
    for key, value in config.items():
        if key == "weights":
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid {key}")
    if (config["max_speed"] <= 0 or config["min_interval"] <= 0 or
            config["max_interval"] < config["min_interval"] or
            type(config["max_components"]) is not int or not 1 <= config["max_components"] <= 7):
        raise ValueError("Invalid temporal, speed or bounded search limits")
    if any(not 0 <= config[key] <= 1 for key in
           ("max_area_change", "max_shape_change", "max_pair_cost", "ambiguity_margin")):
        raise ValueError("Relative thresholds must be in [0,1]")
    weights = config["weights"]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in weights.values()):
        raise ValueError("Weights must be finite and nonnegative")
    if not math.isclose(sum(weights.values()), 1):
        raise ValueError("Weights must sum to one")
    return config


def add_frame(memory, field, occurred_at, *, source="ascii_frame_sensor", frame_id=None):
    validate_field(field)
    if timestamp(occurred_at) is None:
        raise ValueError("A frame requires an ISO timestamp with timezone")
    return memory.add("observation", {"signal": field, "format": "ascii_grid_v1",
                                       "frame_id": frame_id or uuid.uuid4().hex},
                      source=source, occurred_at=occurred_at, concepts=["ascii_frame"])


def _shape(component):
    box = component["bounding_box"]
    return {(x-box["min_x"], y-box["min_y"]) for x, y in component["cells"]}


def _appearance(component):
    return (component["signal"], component["width"], component["height"], tuple(sorted(_shape(component))))


def pair_metrics(a, b, interval, config):
    distance = math.hypot(a["center"]["x"]-b["center"]["x"], a["center"]["y"]-b["center"]["y"])
    area = abs(a["cell_count"]-b["cell_count"]) / max(a["cell_count"], b["cell_count"])
    dimensions = sum(abs(a[key]-b[key])/max(a[key], b[key]) for key in ("width", "height"))/2
    sa, sb = _shape(a), _shape(b)
    shape = 1-len(sa & sb)/len(sa | sb)
    temporal = config["min_interval"] <= interval <= config["max_interval"]
    metrics = {"distance": distance/(config["max_speed"]*interval) if interval > 0 else None,
               "area": area, "dimensions": dimensions, "shape": shape,
               "signal": float(a["signal"] != b["signal"])}
    cost = sum(config["weights"][key]*value for key, value in metrics.items()) if temporal else None
    reasons = []
    if temporal:
        if distance > config["max_speed"]*interval:
            reasons.append("movement_exceeds_speed_limit")
        if area > config["max_area_change"]:
            reasons.append("area_change_exceeds_limit")
        if shape > config["max_shape_change"]:
            reasons.append("shape_change_exceeds_limit")
        if cost > config["max_pair_cost"]:
            reasons.append("pair_cost_exceeds_limit")
    else:
        reasons.append("insufficient_temporal_resolution_or_gap_too_large")
    return {"from_component": a["id"], "to_component": b["id"], "metrics": metrics,
            "center_distance": distance, "time_interval": interval, "cost": cost,
            "admissible": temporal and not reasons, "reasons": reasons,
            "changes": {"cell_count": b["cell_count"]-a["cell_count"],
                        "width": b["width"]-a["width"], "height": b["height"]-a["height"],
                        "signal_from": a["signal"], "signal_to": b["signal"]}}


def match_components(left, right, interval, config=None):
    config = configuration(config)
    temporal = config["min_interval"] <= interval <= config["max_interval"]
    bounded = max(len(left), len(right)) <= config["max_components"]
    if not bounded:
        return {"pairs": [], "alternatives": [], "reason": "component_search_limit",
                "status": "unknown_identity", "unmatched_previous": [c["id"] for c in left],
                "unmatched_current": [c["id"] for c in right]}
    pairs = {(i, j): pair_metrics(a, b, interval, config)
             for i, a in enumerate(left) for j, b in enumerate(right)}
    assignments = []

    def search(i, used, mapping, cost):
        if i == len(left):
            assignments.append((len(used), cost, tuple(mapping)))
            return
        search(i+1, used, mapping+[None], cost)
        for j in range(len(right)):
            if j not in used and pairs[i, j]["admissible"]:
                search(i+1, used | {j}, mapping+[j], cost+pairs[i, j]["cost"])

    search(0, set(), [], 0)
    cardinality = max(item[0] for item in assignments)
    assignments = sorted((item for item in assignments if item[0] == cardinality),
                         key=lambda item: (item[1], tuple(-1 if j is None else j for j in item[2])))
    best = assignments[0]
    alternatives = []
    for _, cost, mapping in assignments:
        changed = [i for i in range(len(left)) if mapping[i] != best[2][i]]
        appearances = {_appearance(left[i]) for i in changed}
        for i in changed:
            for j in (mapping[i], best[2][i]):
                if j is not None:
                    appearances.add(_appearance(right[j]))
        indistinguishable = bool(changed) and len(appearances) == 1
        if cost <= best[1]+config["ambiguity_margin"]+1e-12 or indistinguishable:
            alternatives.append({"cost": cost, "mapping": mapping,
                                 "reason": "indistinguishable_exchange_within_speed_limit" if indistinguishable
                                           else "within_global_cost_margin"})
    confirmed = set()
    for (i, j), pair in pairs.items():
        occurrences = sum(alternative["mapping"][i] == j for alternative in alternatives)
        if not temporal:
            state = "unknown_identity"
        elif not pair["admissible"]:
            state = "different_entity"
        elif occurrences == len(alternatives):
            state = "same_entity"
            confirmed.add((i, j))
        elif occurrences:
            state = "unknown_identity"
            pair["reasons"].append("competing_global_assignments")
        else:
            state = "different_entity"
            pair["reasons"].append("excluded_by_global_one_to_one_assignment")
        pair["status"] = state
        if state == "same_entity":
            pair["reasons"].append("shared_by_all_retained_global_assignments")
    # Convert index mappings into stable component references for external consumers.
    for alternative in alternatives:
        alternative["matches"] = [{"from_component": left[i]["id"], "to_component": right[j]["id"]}
                                  for i, j in enumerate(alternative.pop("mapping")) if j is not None]
    return {"pairs": list(pairs.values()), "alternatives": alternatives,
            "reason": "global_maximum_cardinality_then_minimum_cost" if temporal else "unresolved_time",
            "status": "same_entity" if confirmed else "unknown_identity",
            "unmatched_previous": [c["id"] for i, c in enumerate(left) if not any(k == i for k, _ in confirmed)],
            "unmatched_current": [c["id"] for j, c in enumerate(right) if not any(k == j for _, k in confirmed)],
            "absence_meaning": "not observed or ambiguous; no destruction claim"}


def _persist(memory, kind, payload, frames, parent=None):
    key = digest({"kind": kind, "payload": payload, "frames": frames, "parent": parent, "version": VERSION})
    with memory.db:
        memory.db.execute("BEGIN IMMEDIATE")
        for row in memory.db.execute("SELECT id,payload FROM events WHERE kind=?", (kind,)):
            if json.loads(row["payload"]).get("event_key") == key:
                return row["id"]
        return memory.add(kind, {**payload, "event_key": key, "algorithm_version": VERSION},
                          source=VERSION, parent_id=parent, concepts=["entity_identity"],
                          links=[("evidence", eid) for eid in frames])


def track(memory, frame_ids, config=None):
    config = configuration(config)
    if len(set(frame_ids)) != len(frame_ids):
        raise ValueError("A sequence must not contain the same frame twice")
    frames = [memory.get(eid) for eid in frame_ids]
    times = [timestamp(frame["occurred_at"]) for frame in frames]
    if any(time is None for time in times) or any(a > b for a, b in zip(times, times[1:])):
        raise ValueError("Frames need timezone-aware timestamps in nondecreasing order")
    if any(frame["kind"] != "observation" for frame in frames):
        raise ValueError("Tracking requires primary observation frames")
    perception_ids = [perceive_event(memory, frame["id"]) for frame in frames]
    components = [memory.get(eid)["payload"]["components"] for eid in perception_ids]
    entities = {}
    pair_ids, identity_ids = [], []
    for index in range(1, len(frames)):
        evidence = frame_ids[index-1:index+1]
        comparison = match_components(components[index-1], components[index],
                                      (times[index]-times[index-1]).total_seconds(), config)
        pair_id = _persist(memory, "identity_matching", {
            "frame_ids": evidence, "perception_ids": perception_ids[index-1:index+1],
            "config": config, **comparison}, evidence)
        pair_ids.append(pair_id)
        if comparison["unmatched_previous"] or comparison["unmatched_current"]:
            unresolved_id = _persist(memory, "identity_hypothesis", {
                "entity_id": None, "status": "unknown_identity", "frame_ids": evidence,
                "matching_event_id": pair_id, "alternatives": comparison["alternatives"],
                "unmatched_previous": comparison["unmatched_previous"],
                "unmatched_current": comparison["unmatched_current"],
                "previous_entity_hypothesis_ids": {
                    component: entities[component][2] for component in comparison["unmatched_previous"]
                    if component in entities},
                "reason": "unobserved_or_ambiguous; no persistent identity or destruction inferred"},
                evidence, parent=pair_id)
            identity_ids.append(unresolved_id)
        next_entities = {}
        for pair in comparison["pairs"]:
            if pair["status"] != "same_entity":
                continue
            previous = entities.get(pair["from_component"])
            if previous:
                entity_id, history, prior_id = previous
            else:
                entity_id = "entity_"+digest({"frame": evidence[0], "component": pair["from_component"],
                                              "config": config, "version": VERSION})[:24]
                history = [{"frame_id": evidence[0], "occurred_at": frames[index-1]["occurred_at"],
                            "component_id": pair["from_component"]}]
                prior_id = None
            history = history + [{"frame_id": evidence[1], "occurred_at": frames[index]["occurred_at"],
                                  "component_id": pair["to_component"]}]
            identity_id = _persist(memory, "identity_hypothesis", {
                "entity_id": entity_id, "history": history, "status": "same_entity",
                "matching_event_id": pair_id, "previous_hypothesis_id": prior_id,
                "support": pair, "alternatives": comparison["alternatives"],
                "meaning": "supported tracking hypothesis, not proof of individual identity"},
                [step["frame_id"] for step in history], parent=pair_id)
            next_entities[pair["to_component"]] = (entity_id, history, identity_id)
            identity_ids.append(identity_id)
        entities = next_entities
    return {"matching_ids": pair_ids, "identity_hypothesis_ids": identity_ids,
            "current_entities": {component: {"entity_id": value[0], "history": value[1]}
                                 for component, value in entities.items()}}


def demo():
    scenarios = {
        "movement": ["#.........", ".#........", "..#......."],
        "two_identical": ["#........#..", ".#........#.", "..#........#"],
        "crossing": ["#......#..", "..#..#....", "..#..#...."],
        "disappearance": [".#....", "......"],
        "shape_change": [".#....", "..##.."],
    }
    for name, fields in scenarios.items():
        memory = Memory(":memory:")
        try:
            ids = [add_frame(memory, field, f"2026-11-04T00:00:0{i}Z", frame_id=f"{name}_{i}")
                   for i, field in enumerate(fields)]
            run = track(memory, ids)
            comparisons = [memory.get(eid)["payload"] for eid in run["matching_ids"]]
            print(json.dumps({"scenario": name, "current_entities": run["current_entities"],
                              "comparisons": [
                                  {"pairs": [{key: pair[key] for key in
                                              ("from_component", "to_component", "status", "cost", "reasons")}
                                             for pair in event["pairs"]],
                                   "alternatives": event["alternatives"],
                                   "unmatched_previous": event["unmatched_previous"],
                                   "absence_meaning": event.get("absence_meaning")}
                                  for event in comparisons]},
                             ensure_ascii=False, indent=2))
        finally:
            memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo"])
    parser.parse_args()
    demo()
