import argparse
import csv
import json
from collections import defaultdict, deque
from pathlib import Path


OUTPUT_DIR = Path("output")
DEFAULT_ANALYSIS_INPUT = OUTPUT_DIR / "topic_analysis.json"
DEFAULT_JSON_OUTPUT = OUTPUT_DIR / "adaptive_curriculum.json"
DEFAULT_CSV_OUTPUT = OUTPUT_DIR / "adaptive_curriculum.csv"

DEFAULT_TOTAL_HOURS = 45
MIN_TOPIC_HOURS = 1.0
TIME_INCREMENT = 0.25

MODULE_SEQUENCE = [
    "Algorithm Foundations",
    "Linear Data Structures",
    "Searching And Sorting",
    "Trees",
    "Graphs",
    "Hashing",
]

TOPIC_MODULES = {
    "Algorithm Basics": "Algorithm Foundations",
    "Algorithm Correctness": "Algorithm Foundations",
    "Time Complexity": "Algorithm Foundations",
    "Asymptotic Notation": "Algorithm Foundations",
    "Recurrence Relations": "Algorithm Foundations",
    "Arrays": "Linear Data Structures",
    "Stack": "Linear Data Structures",
    "Queue": "Linear Data Structures",
    "Linked List": "Linear Data Structures",
    "Polynomial Manipulation": "Linear Data Structures",
    "Linear Search": "Searching And Sorting",
    "Binary Search": "Searching And Sorting",
    "Bubble Sort": "Searching And Sorting",
    "Insertion Sort": "Searching And Sorting",
    "Merge Sort": "Searching And Sorting",
    "Quick Sort": "Searching And Sorting",
    "Counting Sort": "Searching And Sorting",
    "Complexity Analysis (sorting-specific)": "Searching And Sorting",
    "Binary Trees": "Trees",
    "BST": "Trees",
    "Tree Traversals": "Trees",
    "2-3 Trees": "Trees",
    "Heap": "Trees",
    "Priority Queue": "Trees",
    "AVL Rotations": "Trees",
    "BFS": "Graphs",
    "DFS": "Graphs",
    "Dijkstra": "Graphs",
    "Minimum Spanning Tree": "Graphs",
    "Prim": "Graphs",
    "Kruskal": "Graphs",
    "Hash Functions": "Hashing",
    "Collision Resolution": "Hashing",
    "Separate Chaining": "Hashing",
    "Open Addressing": "Hashing",
}

PREREQUISITES = {
    "Algorithm Correctness": ["Algorithm Basics"],
    "Time Complexity": ["Algorithm Basics"],
    "Asymptotic Notation": ["Time Complexity"],
    "Recurrence Relations": ["Time Complexity", "Asymptotic Notation"],
    "Linear Search": ["Arrays"],
    "Binary Search": ["Arrays", "Time Complexity"],
    "Bubble Sort": ["Arrays", "Time Complexity"],
    "Insertion Sort": ["Arrays", "Time Complexity"],
    "Merge Sort": ["Arrays", "Recurrence Relations"],
    "Quick Sort": ["Arrays", "Recurrence Relations"],
    "Counting Sort": ["Arrays", "Time Complexity"],
    "Complexity Analysis (sorting-specific)": ["Time Complexity"],
    "Stack": ["Arrays"],
    "Queue": ["Arrays"],
    "Linked List": ["Arrays"],
    "Polynomial Manipulation": ["Linked List"],
    "Binary Trees": ["Linked List"],
    "BST": ["Binary Trees"],
    "Tree Traversals": ["Binary Trees"],
    "2-3 Trees": ["BST"],
    "Heap": ["Binary Trees", "Arrays"],
    "Priority Queue": ["Heap"],
    "AVL Rotations": ["BST"],
    "BFS": ["Queue"],
    "DFS": ["Stack"],
    "Dijkstra": ["Priority Queue"],
    "Minimum Spanning Tree": [],
    "Prim": ["Minimum Spanning Tree"],
    "Kruskal": ["Minimum Spanning Tree"],
    "Hash Functions": ["Arrays"],
    "Collision Resolution": ["Hash Functions"],
    "Separate Chaining": ["Collision Resolution", "Linked List"],
    "Open Addressing": ["Collision Resolution", "Arrays"],
}

FOUNDATION_TOPICS = {
    "Algorithm Basics",
    "Time Complexity",
    "Arrays",
    "Linked List",
    "Binary Trees",
}

TOPIC_DIFFICULTY_BOOSTS = {
    "Algorithm Correctness": 0.55,
    "Asymptotic Notation": 0.35,
    "Recurrence Relations": 0.35,
    "Complexity Analysis (sorting-specific)": 0.35,
    "Heap": 0.25,
    "Dijkstra": 0.35,
    "Minimum Spanning Tree": 0.35,
    "Kruskal": 0.25,
}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def module_index(topic):
    module = TOPIC_MODULES.get(topic, "Other")
    try:
        return MODULE_SEQUENCE.index(module)
    except ValueError:
        return len(MODULE_SEQUENCE)


def cognitive_level(topic):
    bloom = topic.get("bloom_distribution", {})
    weighted = (
        bloom.get("Remember", 0) * 1
        + bloom.get("Understand", 0) * 2
        + bloom.get("Apply", 0) * 3
        + bloom.get("Analyze", 0) * 4
        + bloom.get("Create", 0) * 5
    )
    total = sum(bloom.values())
    if not total:
        return 2.0
    return round(weighted / total, 2)


def difficulty_score(topic):
    cognitive = cognitive_level(topic)
    importance = float(topic.get("percentage_weight", 0))
    frequency = float(topic.get("frequency", 0))

    normalized_importance = min(5.0, importance / 4)
    normalized_frequency = min(5.0, frequency / 3)
    score = (cognitive * 0.55) + (normalized_importance * 0.3) + (normalized_frequency * 0.15)
    score += TOPIC_DIFFICULTY_BOOSTS.get(topic["topic"], 0)
    return round(score, 2)


def difficulty_level_from_score(score):
    if score >= 3.75:
        return "Very Hard"
    if score >= 3.0:
        return "Hard"
    if score >= 2.2:
        return "Moderate"
    return "Easy"


def topic_difficulty(topic):
    score = difficulty_score(topic)
    return score, difficulty_level_from_score(score)


def topic_priority(topic):
    foundation_bonus = 10 if topic["topic"] in FOUNDATION_TOPICS else 0
    importance = float(topic.get("percentage_weight", 0))
    primary = float(topic.get("primary_frequency", 0))
    cognitive = cognitive_level(topic)
    return (
        -module_index(topic["topic"]),
        foundation_bonus,
        importance,
        primary,
        cognitive,
    )


def build_topic_lookup(analysis_report, min_percentage):
    topics = {}
    for topic in analysis_report.get("ranked_topics", []):
        if topic.get("percentage_weight", 0) < min_percentage and topic.get("importance_level") == "Low":
            continue
        topics[topic["topic"]] = topic
    return topics


def build_dependency_graph(topics):
    children = defaultdict(set)
    indegree = {topic: 0 for topic in topics}
    missing_prerequisites = defaultdict(list)

    for topic in topics:
        for prerequisite in PREREQUISITES.get(topic, []):
            if prerequisite in topics:
                children[prerequisite].add(topic)
                indegree[topic] += 1
            else:
                missing_prerequisites[topic].append(prerequisite)

    return children, indegree, missing_prerequisites


def order_topics(topics):
    children, indegree, missing_prerequisites = build_dependency_graph(topics)
    ready = sorted(
        [topic for topic, count in indegree.items() if count == 0],
        key=lambda name: topic_priority(topics[name]),
        reverse=True,
    )
    ordered = []

    while ready:
        topic = ready.pop(0)
        ordered.append(topic)
        for child in sorted(children[topic], key=lambda name: topic_priority(topics[name]), reverse=True):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
        ready.sort(key=lambda name: topic_priority(topics[name]), reverse=True)

    if len(ordered) != len(topics):
        remaining = [topic for topic in topics if topic not in ordered]
        ordered.extend(sorted(remaining, key=lambda name: topic_priority(topics[name]), reverse=True))

    return ordered, missing_prerequisites


def allocate_hours(ordered_topics, topic_lookup, total_hours):
    weighted_sum = sum(topic_lookup[topic].get("weighted_score", 0) for topic in ordered_topics)
    topic_count = len(ordered_topics)
    if not topic_count:
        return {}

    minimum_total = MIN_TOPIC_HOURS * topic_count
    if minimum_total >= total_hours:
        equal_hours = total_hours / topic_count
        return normalize_time_allocations(
            {topic: equal_hours for topic in ordered_topics},
            ordered_topics,
            topic_lookup,
            total_hours,
        )

    remaining_hours = float(total_hours) - minimum_total
    allocations = {topic: MIN_TOPIC_HOURS for topic in ordered_topics}

    for topic in ordered_topics:
        if weighted_sum:
            hours = remaining_hours * topic_lookup[topic].get("weighted_score", 0) / weighted_sum
        else:
            hours = remaining_hours / topic_count
        allocations[topic] += hours

    return normalize_time_allocations(allocations, ordered_topics, topic_lookup, total_hours)


def round_to_time_increment(hours):
    return round(round(hours / TIME_INCREMENT) * TIME_INCREMENT, 2)


def normalize_time_allocations(allocations, ordered_topics, topic_lookup, total_hours):
    rounded = {
        topic: max(TIME_INCREMENT, round_to_time_increment(hours))
        for topic, hours in allocations.items()
    }
    difference = round(total_hours - sum(rounded.values()), 2)

    while abs(difference) >= TIME_INCREMENT and rounded:
        if difference > 0:
            target = max(ordered_topics, key=lambda topic: topic_lookup[topic].get("weighted_score", 0))
            rounded[target] = round(rounded[target] + TIME_INCREMENT, 2)
        else:
            candidates = [
                topic
                for topic in ordered_topics
                if rounded[topic] - TIME_INCREMENT >= MIN_TOPIC_HOURS
            ]
            if not candidates:
                candidates = [
                    topic
                    for topic in ordered_topics
                    if rounded[topic] - TIME_INCREMENT >= TIME_INCREMENT
                ]
            if not candidates:
                break
            target = min(candidates, key=lambda topic: topic_lookup[topic].get("weighted_score", 0))
            rounded[target] = round(rounded[target] - TIME_INCREMENT, 2)

        difference = round(total_hours - sum(rounded.values()), 2)

    return rounded


def recommended_activity(topic):
    difficulty, level = topic_difficulty(topic)
    if level in {"Hard", "Very Hard"}:
        return "Proofs, traces, comparative problems, and exam-style analysis"
    if difficulty >= 2.4:
        return "Worked examples, implementation traces, and guided problem solving"
    return "Concept explanation, definitions, diagrams, and short recall checks"


def build_modules(sequence):
    modules = []
    grouped = defaultdict(list)
    for item in sequence:
        grouped[item["module"]].append(item)

    for module in MODULE_SEQUENCE:
        topics = grouped.get(module, [])
        if not topics:
            continue
        module_difficulty_score = round(
            sum(topic["difficulty_score"] * topic["allocated_hours"] for topic in topics)
            / max(0.01, sum(topic["allocated_hours"] for topic in topics)),
            2,
        )
        modules.append(
            {
                "module": module,
                "total_hours": round(sum(topic["allocated_hours"] for topic in topics), 2),
                "average_importance": round(sum(topic["percentage_weight"] for topic in topics) / len(topics), 2),
                "difficulty_score": module_difficulty_score,
                "difficulty_level": difficulty_level_from_score(module_difficulty_score),
                "topics": [topic["topic"] for topic in topics],
            }
        )

    other_topics = grouped.get("Other", [])
    if other_topics:
        module_difficulty_score = round(
            sum(topic["difficulty_score"] * topic["allocated_hours"] for topic in other_topics)
            / max(0.01, sum(topic["allocated_hours"] for topic in other_topics)),
            2,
        )
        modules.append(
            {
                "module": "Other",
                "total_hours": round(sum(topic["allocated_hours"] for topic in other_topics), 2),
                "average_importance": round(sum(topic["percentage_weight"] for topic in other_topics) / len(other_topics), 2),
                "difficulty_score": module_difficulty_score,
                "difficulty_level": difficulty_level_from_score(module_difficulty_score),
                "topics": [topic["topic"] for topic in other_topics],
            }
        )

    return modules


def build_curriculum(analysis_report, total_hours=DEFAULT_TOTAL_HOURS, min_percentage=0.5):
    topic_lookup = build_topic_lookup(analysis_report, min_percentage)
    ordered_topics, missing_prerequisites = order_topics(topic_lookup)
    hour_allocations = allocate_hours(ordered_topics, topic_lookup, total_hours)
    sequence = []

    for index, topic_name in enumerate(ordered_topics, start=1):
        topic = topic_lookup[topic_name]
        difficulty, difficulty_level = topic_difficulty(topic)
        prerequisites = [
            prerequisite
            for prerequisite in PREREQUISITES.get(topic_name, [])
            if prerequisite in topic_lookup
        ]
        missing = missing_prerequisites.get(topic_name, [])
        sequence.append(
            {
                "order": index,
                "topic": topic_name,
                "module": TOPIC_MODULES.get(topic_name, "Other"),
                "allocated_hours": hour_allocations[topic_name],
                "percentage_weight": topic["percentage_weight"],
                "importance_level": topic["importance_level"],
                "cognitive_level": cognitive_level(topic),
                "difficulty_score": difficulty,
                "difficulty_level": difficulty_level,
                "prerequisites": prerequisites,
                "missing_prerequisite_notes": missing,
                "recommended_activity": recommended_activity(topic),
            }
        )

    modules = build_modules(sequence)
    return {
        "metadata": {
            "source": str(DEFAULT_ANALYSIS_INPUT),
            "total_hours": total_hours,
            "included_topic_count": len(sequence),
            "min_percentage": min_percentage,
            "method": "Prerequisite-aware ordering plus PYQ/Bloom/confidence weighted hour allocation",
        },
        "modules": modules,
        "curriculum_sequence": sequence,
    }


def write_json_report(report, output_path=DEFAULT_JSON_OUTPUT):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(report, file_obj, indent=2, ensure_ascii=False)


def write_csv_report(report, output_path=DEFAULT_CSV_OUTPUT):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "order",
        "module",
        "topic",
        "allocated_hours",
        "percentage_weight",
        "importance_level",
        "cognitive_level",
        "difficulty_score",
        "difficulty_level",
        "prerequisites",
        "recommended_activity",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        for item in report["curriculum_sequence"]:
            row = {key: item.get(key) for key in fieldnames}
            row["prerequisites"] = "; ".join(item.get("prerequisites", []))
            writer.writerow(row)


def print_summary(report, limit=12):
    metadata = report.get("metadata", {})
    displayed = report["curriculum_sequence"][:limit]
    total_displayed_hours = sum(item["allocated_hours"] for item in displayed)

    print("Adaptive Curriculum Plan")
    print(
        f"Hours: {metadata.get('total_hours', 'N/A')}    "
        f"Topics: {metadata.get('included_topic_count', len(report['curriculum_sequence']))}    "
        "Time unit: 0.25h    "
        "Basis: PYQ + Bloom + prerequisites"
    )
    print()
    print("Topic Allocation")
    print("-" * 118)
    print(
        f"{'No.':<4}  {'Topic':<42}  {'Hours':>7}  "
        f"{'Importance':<12}  {'Difficulty':<12}  {'Module':<28}"
    )
    print("-" * 118)
    for item in report["curriculum_sequence"][:limit]:
        print(
            f"{item['order']:<4}  {item['topic']:<42}  "
            f"{item['allocated_hours']:>6.2f}h  "
            f"{item['importance_level']:<12}  "
            f"{item['difficulty_level']:<12}  "
            f"{item['module']:<28}"
        )
    if limit < len(report["curriculum_sequence"]):
        print(f"... showing {limit} of {len(report['curriculum_sequence'])} topics")
    print(f"Displayed hours: {total_displayed_hours:.2f}h")

    print()
    print("Module Summary")
    print("-" * 88)
    print(
        f"{'Module':<34}  {'Hours':>8}  {'Difficulty':<12}  "
        f"{'Avg Importance':>14}  {'Topics':>6}"
    )
    print("-" * 88)
    for module in report["modules"]:
        print(
            f"{module['module']:<34}  "
            f"{module['total_hours']:>7.2f}h  "
            f"{module['difficulty_level']:<12}  "
            f"{module['average_importance']:>13.2f}%  "
            f"{len(module['topics']):>6}"
        )
    print(f"Total allocated hours: {sum(module['total_hours'] for module in report['modules']):.2f}h")


def main():
    parser = argparse.ArgumentParser(description="Build an adaptive curriculum from topic analysis output.")
    parser.add_argument("--analysis-input", default=str(DEFAULT_ANALYSIS_INPUT), help="Path to topic_analysis.json.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Path for curriculum JSON output.")
    parser.add_argument("--csv-output", default=str(DEFAULT_CSV_OUTPUT), help="Path for curriculum CSV output.")
    parser.add_argument("--total-hours", type=float, default=DEFAULT_TOTAL_HOURS, help="Total syllabus hours to allocate.")
    parser.add_argument("--min-percentage", type=float, default=0.5, help="Drop low-importance topics below this percentage.")
    parser.add_argument("--top", type=int, default=12, help="Number of curriculum entries to print.")
    args = parser.parse_args()

    analysis_report = load_json(args.analysis_input)
    curriculum = build_curriculum(
        analysis_report,
        total_hours=args.total_hours,
        min_percentage=args.min_percentage,
    )
    write_json_report(curriculum, Path(args.json_output))
    write_csv_report(curriculum, Path(args.csv_output))
    print_summary(curriculum, args.top)
    print()
    print(f"Saved JSON: {args.json_output}")
    print(f"Saved CSV: {args.csv_output}")


if __name__ == "__main__":
    main()
