import json
import os

from utils import detect_bloom, detect_source_type, extract_text, map_topic, parse_entries

INPUT_DIR = "data"
OUTPUT_DIR = "output"


SUPPORTED_EXTENSIONS = (".pdf", ".docx")


def process_file(file_path):
    text = extract_text(file_path)
    source_type = detect_source_type(text)
    entries = parse_entries(text, source_type)
    results = []

    for index, entry in enumerate(entries, start=1):
        question_text = entry["question_text"]
        answer_text = entry["answer_text"]
        primary, secondary, scores, confidence = map_topic(question_text, answer_text)
        bloom = detect_bloom(question_text)

        results.append(
            {
                "question_id": f"Q{index}",
                "question_text": question_text,
                "answer_text": answer_text,
                "primary_topic": primary,
                "secondary_topics": secondary,
                "confidence": confidence,
                "bloom_level": bloom,
                "source_type": source_type,
                "scores": scores,
            }
        )

    return source_type, results


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for file_name in sorted(os.listdir(INPUT_DIR)):
        if not file_name.lower().endswith(SUPPORTED_EXTENSIONS):
            continue

        path = os.path.join(INPUT_DIR, file_name)
        print(f"Processing: {file_name}")

        source_type, results = process_file(path)
        print(f"Detected type: {source_type}")

        base_name = os.path.splitext(file_name)[0]
        output_file = os.path.join(OUTPUT_DIR, f"{base_name}.json")
        with open(output_file, "w", encoding="utf-8") as file_obj:
            json.dump(results, file_obj, indent=2, ensure_ascii=False)

        print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
