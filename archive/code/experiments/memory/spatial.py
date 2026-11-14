"""Persistence and optional semantic interpretation for ASCII perception."""
import argparse
import json
from pathlib import Path

from .perception import PERCEPTION_VERSION, component_relations, extract_components, validate_field
from .store import Memory
from .geometry import classify, load_dictionary


DEFAULT_DICTIONARY = Path(__file__).resolve().parents[2] / "data" / "spatial_forms.json"


def perceive_event(memory, observation_id):
    observation = memory.get(observation_id)
    if observation["kind"] != "observation":
        raise ValueError("Perception requires an observation event")
    field = observation["payload"].get("signal")
    components = extract_components(field)
    existing = memory.db.execute(
        "SELECT id, payload FROM events WHERE parent_id=? AND kind='perception' ORDER BY recorded_at",
        (observation_id,),
    ).fetchall()
    for row in existing:
        payload = json.loads(row["payload"])
        if payload.get("algorithm_version") == PERCEPTION_VERSION:
            return row["id"]
    derived_id = memory.add(
        "perception",
        {"algorithm_version": PERCEPTION_VERSION, "components": components,
         "relations": component_relations(components),
         "measurements_note": "Signal-derived measurements; no object labels assigned."},
        concepts=["perception", "connected_components"],
        source="ascii_sensor",
        parent_id=observation_id,
    )
    memory.link(derived_id, "perceives", observation_id)
    return derived_id


def interpret_perception(memory, perception_id, dictionary_path=DEFAULT_DICTIONARY):
    perception = memory.get(perception_id)
    if perception["kind"] != "perception":
        raise ValueError("Interpretation requires a perception event")
    dictionary = load_dictionary(dictionary_path)
    interpretation_source = f"spatial_dictionary_v{dictionary.get('version', 'unknown')}"
    existing = memory.db.execute(
        "SELECT id, payload FROM events WHERE parent_id=? AND kind='interpretation' AND source=?",
        (perception_id, interpretation_source),
    ).fetchall()
    for row in existing:
        if json.loads(row["payload"]).get("dictionary") == dictionary:
            return row["id"]
    results = []
    for component in perception["payload"]["components"]:
        for verdict in classify(component["features"], dictionary["rules"]):
            results.append({"component_id": component["id"], **verdict})
    interpretation_id = memory.add(
        "interpretation",
        {"dictionary": dictionary, "results": results,
         "evidence_event_id": perception_id,
         "method": "feature_rule_matching"},
        concepts=["spatial_form_interpretation"], source=interpretation_source,
        parent_id=perception_id,
    )
    memory.link(interpretation_id, "interprets", perception_id)
    return interpretation_id


def add_signal(memory, field, source=None):
    validate_field(field)  # validate before persisting input
    return memory.add("observation", {"signal": field, "format": "ascii_grid_v1"},
                      concepts=["signal", "ascii_grid"], source=source)


DEMO_FIELD = """............
..###.......
..#.#...@@..
..###...@@..
............"""


def demo(db_path):
    memory = Memory(db_path)
    try:
        original_id = add_signal(memory, DEMO_FIELD, source="spatial_demo")
        perception_id = perceive_event(memory, original_id)
        interpretation_id = interpret_perception(memory, perception_id)
        original = memory.get(original_id)
        perception = memory.get(perception_id)
        interpretation = memory.get(interpretation_id)
        print("Исходный сигнал:\n" + original["payload"]["signal"])
        print("Компоненты:", json.dumps(perception["payload"]["components"], ensure_ascii=False, indent=2))
        print("Отношения:", json.dumps(perception["payload"]["relations"], ensure_ascii=False, indent=2))
        print("Классификация:", json.dumps(interpretation["payload"]["results"], ensure_ascii=False, indent=2))
    finally:
        memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--db", default="ottt_spatial_demo.sqlite3")
    args = parser.parse_args()
    demo(args.db)
