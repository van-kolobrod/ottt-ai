"""ОТТТ-ИИ: ретроспективная классификация геометрических наблюдений.
Python 3.10+, только стандартная библиотека.
Поместите рядом с OTTT_memory_v1.py.
Запуск: python OTTT_geometry_audit_v1.py demo
"""
import argparse
import json
from pathlib import Path
try:  # Support both `python -m experiments.memory.geometry` and direct script execution.
    from .store import Memory
except ImportError:
    from store import Memory

DEFAULT_DICTIONARY = Path(__file__).resolve().parents[2] / "data" / "geometry.json"

def load_dictionary(path=DEFAULT_DICTIONARY):
    """Load and minimally validate a concept/rule dictionary from JSON."""
    with open(path, encoding="utf-8") as source:
        dictionary = json.load(source)
    if not isinstance(dictionary.get("rules"), dict):
        raise ValueError("Dictionary must contain a rules object")
    for name, rule in dictionary["rules"].items():
        if not isinstance(rule.get("required"), dict) or not rule["required"]:
            raise ValueError(f"Rule {name!r} must contain non-empty required features")
        if not isinstance(rule.get("parent"), str):
            raise ValueError(f"Rule {name!r} must contain a parent concept")
    return dictionary

RULES = load_dictionary()["rules"]

def classify(features, rules):
    """Трёхзначная логика: совпадение, опровержение, недостаточно данных."""
    results = []
    for name, rule in rules.items():
        absent = [key for key in rule["required"] if key not in features]
        conflicts = [key for key, value in rule["required"].items()
                     if key in features and features[key] != value]
        status = "rejected" if conflicts else ("unknown" if absent else "matched")
        results.append({"concept": name, "status": status,
                        "missing": absent, "conflicts": conflicts})
    return results

def audit_geometry(memory, rules=None):
    """Пишет только новые выводы. Исходные события не меняются."""
    rules = rules or RULES
    observations = [e for e in memory.search(include_archive=True, limit=100000)
                    if e["kind"] == "observation"
                    and isinstance(e["payload"].get("features"), dict)]
    created = []
    for event in observations:
        for verdict in classify(event["payload"]["features"], rules):
            if verdict["status"] != "matched":
                continue
            concept = verdict["concept"]
            existing = memory.db.execute(
                """SELECT e.id FROM events e
                   WHERE e.parent_id=? AND e.kind='classification'""",
                (event["id"],)).fetchall()
            if any(memory.get(row[0])["payload"].get("concept") == concept
                   for row in existing):
                continue
            # Semantic indexing enriches retrieval without changing the source payload.
            memory.tag(event["id"], ["геометрия", concept, rules[concept]["parent"]])
            derived = memory.add(
                "classification",
                {"concept": concept, "rule": rules[concept]["required"],
                 "evidence_event_id": event["id"],
                 "method": "deterministic_feature_matching",
                 "note": "Вывод по заявленным признакам, а не независимая проверка изображения"},
                concepts=["геометрия", concept, rules[concept]["parent"]],
                source="geometry_audit_v1",
                parent_id=event["id"],
            )
            memory.link(derived, "classifies", event["id"])
            created.append({"observation_id": event["id"],
                            "classification_id": derived, "concept": concept})
    return created

def demo(db_path):
    memory = Memory(db_path)
    try:
        observation = memory.add(
            "observation",
            {"description": "Неизвестная фигура",
             "features": {"closed": True, "sides": 4,
                          "equal_sides": True, "right_angles": True}},
            concepts=["фигура", "наблюдение"],
            source="geometry_demo",
        )
        memory.archive(observation)
        original = memory.get(observation)["payload"].copy()
        print("До аудита, поиск 'квадрат':",
              len(memory.search("квадрат", include_archive=True)))
        created = audit_geometry(memory)
        print("Новые выводы:", json.dumps(created, ensure_ascii=False))
        print("Повторный аудит, новых выводов:", len(audit_geometry(memory)))
        print("После аудита, поиск 'квадрат':",
              len(memory.search("квадрат", include_archive=True)))
        print("Исходная запись не изменена:",
              memory.get(observation)["payload"] == original)
        print("Исходная запись осталась в архиве:",
              memory.get(observation)["tier"] == "archive")
        print("Результаты классификации:",
              json.dumps(classify({"closed": True, "sides": 4},
                                  RULES), ensure_ascii=False))
    finally:
        memory.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo", "audit"])
    parser.add_argument("--db", default="ottt_geometry_demo.sqlite3")
    args = parser.parse_args()
    if args.command == "demo":
        demo(args.db)
    else:
        memory = Memory(args.db)
        try:
            print(json.dumps(audit_geometry(memory), ensure_ascii=False, indent=2))
        finally:
            memory.close()
