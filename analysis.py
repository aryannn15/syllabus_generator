import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


OUTPUT_DIR = Path("output")
DEFAULT_JSON_OUTPUT = OUTPUT_DIR / "topic_analysis.json"
DEFAULT_CSV_OUTPUT = OUTPUT_DIR / "topic_analysis.csv"

BLOOM_WEIGHTS = {
    "Remember": 1,
    "Understand": 2,
    "Apply": 3,
    "Analyze": 4,
    "Create": 5,
}

BLOOM_LEVELS = list(BLOOM_WEIGHTS)

PRIMARY_TOPIC_WEIGHT = 1.0
SECONDARY_TOPIC_WEIGHT = 0.45
MIN_CONFIDENCE = 0.25

CORE_TOPIC_BOOSTS = {
    "Time Complexity": 1.12,
    "Asymptotic Notation": 1.1,
    "Recurrence Relations": 1.1,
    "Arrays": 1.05,
    "Stack": 1.05,
    "Queue": 1.05,
    "Linked List": 1.05,
    "Binary Trees": 1.05,
    "Tree Traversals": 1.05,
    "Heap": 1.05,
    "Hash Functions": 1.05,
}

TOPIC_GROUPS = {
    "Algorithm Analysis": {
        "Algorithm Basics",
        "Algorithm Correctness",
        "Time Complexity",
        "Asymptotic Notation",
        "Recurrence Relations",
    },
    "Linear Data Structures": {
        "Arrays",
        "Stack",
        "Queue",
        "Linked List",
        "Polynomial Manipulation",
    },
    "Searching And Sorting": {
        "Linear Search",
        "Binary Search",
        "Bubble Sort",
        "Insertion Sort",
        "Merge Sort",
        "Quick Sort",
        "Counting Sort",
        "Complexity Analysis (sorting-specific)",
    },
    "Trees": {
        "Binary Trees",
        "BST",
        "Tree Traversals",
        "2-3 Trees",
        "Heap",
        "Priority Queue",
        "AVL Rotations",
    },
    "Graphs": {
        "BFS",
        "DFS",
        "Dijkstra",
        "Minimum Spanning Tree",
        "Prim",
        "Kruskal",
    },
    "Hashing": {
        "Hash Functions",
        "Collision Resolution",
        "Separate Chaining",
        "Open Addressing",
    },
}


def empty_topic_record():
    return {
        "frequency": 0,
        "primary_frequency": 0,
        "secondary_frequency": 0,
        "raw_score": 0.0,
        "weighted_score": 0.0,
        "normalized_weight": 0.0,
        "percentage_weight": 0.0,
        "average_confidence": 0.0,
        "importance_level": "Low",
        "bloom_distribution": {level: 0 for level in BLOOM_LEVELS},
        "questions": [],
    }


def load_json_file(path):
    with path.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    if not isinstance(data, list):
        return []
    return data


def discover_input_files(input_dir):
    ignored_names = {
        DEFAULT_JSON_OUTPUT.name,
        DEFAULT_CSV_OUTPUT.name,
        "adaptive_curriculum.json",
    }
    return [
        path
        for path in sorted(input_dir.glob("*.json"))
        if path.name not in ignored_names
    ]


def safe_confidence(entry):
    try:
        confidence = float(entry.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    return min(1.0, max(0.0, confidence))


def safe_bloom(entry):
    bloom = entry.get("bloom_level", "Understand")
    if bloom not in BLOOM_WEIGHTS:
        return "Understand"
    return bloom


def question_ref(source_file, question_id):
    return f"{source_file}:{question_id}"


def add_topic_evidence(topic_stats, topic, entry, source_file, credit):
    if not topic or topic == "UNKNOWN":
        return

    confidence = safe_confidence(entry)
    if confidence < MIN_CONFIDENCE:
        return

    bloom = safe_bloom(entry)
    bloom_weight = BLOOM_WEIGHTS[bloom]
    score = bloom_weight * confidence * credit
    stats = topic_stats[topic]

    stats["frequency"] += credit
    if credit == PRIMARY_TOPIC_WEIGHT:
        stats["primary_frequency"] += 1
    else:
        stats["secondary_frequency"] += 1
    stats["raw_score"] += score
    stats["bloom_distribution"][bloom] += credit
    stats["questions"].append(
        {
            "source_file": source_file,
            "question_id": entry.get("question_id", "UNKNOWN"),
            "role": "primary" if credit == PRIMARY_TOPIC_WEIGHT else "secondary",
            "bloom_level": bloom,
            "confidence": confidence,
            "score": round(score, 4),
        }
    )


def apply_noise_and_core_adjustments(topic, stats):
    score = stats["raw_score"]

    if stats["primary_frequency"] == 0:
        score *= 0.75
    if stats["frequency"] < 1.5 and stats["average_confidence"] < 0.6:
        score *= 0.65

    score *= CORE_TOPIC_BOOSTS.get(topic, 1.0)
    return score


def finalize_topic_stats(topic_stats):
    for topic, stats in topic_stats.items():
        confidence_values = [item["confidence"] for item in stats["questions"]]
        if confidence_values:
            stats["average_confidence"] = sum(confidence_values) / len(confidence_values)
        stats["weighted_score"] = apply_noise_and_core_adjustments(topic, stats)

    total_score = sum(stats["weighted_score"] for stats in topic_stats.values())
    ranked = sorted(
        topic_stats.items(),
        key=lambda item: (
            item[1]["weighted_score"],
            item[1]["primary_frequency"],
            item[1]["frequency"],
        ),
        reverse=True,
    )

    for rank, (topic, stats) in enumerate(ranked, start=1):
        if total_score:
            stats["normalized_weight"] = stats["weighted_score"] / total_score
            stats["percentage_weight"] = stats["normalized_weight"] * 100

        if stats["percentage_weight"] >= 10:
            stats["importance_level"] = "Very High"
        elif stats["percentage_weight"] >= 6:
            stats["importance_level"] = "High"
        elif stats["percentage_weight"] >= 3:
            stats["importance_level"] = "Medium"
        else:
            stats["importance_level"] = "Low"

        stats["rank"] = rank
        stats["frequency"] = round(stats["frequency"], 2)
        stats["raw_score"] = round(stats["raw_score"], 4)
        stats["weighted_score"] = round(stats["weighted_score"], 4)
        stats["normalized_weight"] = round(stats["normalized_weight"], 4)
        stats["percentage_weight"] = round(stats["percentage_weight"], 2)
        stats["average_confidence"] = round(stats["average_confidence"], 3)
        stats["bloom_distribution"] = {
            level: round(value, 2)
            for level, value in stats["bloom_distribution"].items()
        }

    return [
        {
            "topic": topic,
            **stats,
        }
        for topic, stats in ranked
    ]


def build_group_analysis(ranked_topics):
    topic_lookup = {item["topic"]: item for item in ranked_topics}
    groups = []

    for group_name, topics in TOPIC_GROUPS.items():
        group_topics = [topic_lookup[topic] for topic in topics if topic in topic_lookup]
        if not group_topics:
            continue

        groups.append(
            {
                "group": group_name,
                "topics": [item["topic"] for item in group_topics],
                "weighted_score": round(sum(item["weighted_score"] for item in group_topics), 4),
                "percentage_weight": round(sum(item["percentage_weight"] for item in group_topics), 2),
                "frequency": round(sum(item["frequency"] for item in group_topics), 2),
                "primary_frequency": sum(item["primary_frequency"] for item in group_topics),
            }
        )

    return sorted(
        groups,
        key=lambda item: (item["weighted_score"], item["primary_frequency"]),
        reverse=True,
    )


def analyze_entries(entries_by_file):
    topic_stats = defaultdict(empty_topic_record)
    skipped = []

    for source_file, entries in entries_by_file.items():
        for entry in entries:
            primary_topic = entry.get("primary_topic")
            if primary_topic in (None, "", "UNKNOWN"):
                skipped.append(question_ref(source_file, entry.get("question_id", "UNKNOWN")))
                continue

            add_topic_evidence(
                topic_stats,
                primary_topic,
                entry,
                source_file,
                PRIMARY_TOPIC_WEIGHT,
            )

            for secondary_topic in entry.get("secondary_topics", []) or []:
                add_topic_evidence(
                    topic_stats,
                    secondary_topic,
                    entry,
                    source_file,
                    SECONDARY_TOPIC_WEIGHT,
                )

    ranked_topics = finalize_topic_stats(topic_stats)
    group_analysis = build_group_analysis(ranked_topics)

    return {
        "metadata": {
            "source_file_count": len(entries_by_file),
            "question_count": sum(len(entries) for entries in entries_by_file.values()),
            "skipped_unknown_count": len(skipped),
            "primary_topic_weight": PRIMARY_TOPIC_WEIGHT,
            "secondary_topic_weight": SECONDARY_TOPIC_WEIGHT,
            "min_confidence": MIN_CONFIDENCE,
            "formula": "score = bloom_weight * confidence * topic_role_weight",
        },
        "ranked_topics": ranked_topics,
        "topic_groups": group_analysis,
        "skipped_unknown_questions": skipped,
    }


def analyze_directory(input_dir=OUTPUT_DIR):
    input_files = discover_input_files(Path(input_dir))
    entries_by_file = {
        path.name: load_json_file(path)
        for path in input_files
    }
    return analyze_entries(entries_by_file)


def write_json_report(report, output_path=DEFAULT_JSON_OUTPUT):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(report, file_obj, indent=2, ensure_ascii=False)


def write_csv_report(report, output_path=DEFAULT_CSV_OUTPUT):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "topic",
        "importance_level",
        "frequency",
        "primary_frequency",
        "secondary_frequency",
        "weighted_score",
        "percentage_weight",
        "average_confidence",
        "Remember",
        "Understand",
        "Apply",
        "Analyze",
        "Create",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        for topic in report["ranked_topics"]:
            row = {
                key: topic.get(key)
                for key in fieldnames
                if key not in BLOOM_LEVELS
            }
            row.update(topic["bloom_distribution"])
            writer.writerow(row)


def print_summary(report, limit=10):
    print("Top Topics")
    print("-" * 60)
    for topic in report["ranked_topics"][:limit]:
        print(
            f"{topic['rank']:>2}. {topic['topic']:<38} "
            f"{topic['percentage_weight']:>6.2f}%  "
            f"score={topic['weighted_score']:<6.2f}  "
            f"freq={topic['frequency']}"
        )

    print()
    print("Top Topic Groups")
    print("-" * 60)
    for group in report["topic_groups"][:5]:
        print(
            f"{group['group']:<30} "
            f"{group['percentage_weight']:>6.2f}%  "
            f"score={group['weighted_score']:<6.2f}"
        )


def main():
    parser = argparse.ArgumentParser(description="Build weighted topic intelligence from classified PYQ JSON files.")
    parser.add_argument("--input-dir", default=str(OUTPUT_DIR), help="Directory containing classified JSON files.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Path for the JSON analysis report.")
    parser.add_argument("--csv-output", default=str(DEFAULT_CSV_OUTPUT), help="Path for the CSV topic report.")
    parser.add_argument("--top", type=int, default=10, help="Number of ranked topics to print.")
    args = parser.parse_args()

    report = analyze_directory(args.input_dir)
    write_json_report(report, Path(args.json_output))
    write_csv_report(report, Path(args.csv_output))
    print_summary(report, args.top)
    print()
    print(f"Saved JSON: {args.json_output}")
    print(f"Saved CSV: {args.csv_output}")


if __name__ == "__main__":
    main()
