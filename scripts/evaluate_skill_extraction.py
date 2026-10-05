"""Tính Precision/Recall/F1 cho tập dự đoán kỹ năng dạng JSON."""
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/evaluate_skill_extraction.py predictions.json")
        return 2
    truth = json.loads(Path("data/ground_truth/skill_extraction.json").read_text(encoding="utf-8"))
    predicted = {row["id"]: set(row.get("skills", [])) for row in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))}
    tp = fp = fn = 0
    for row in truth:
        actual = set(row["skills"])
        guess = predicted.get(row["id"], set())
        tp += len(actual & guess)
        fp += len(guess - actual)
        fn += len(actual - guess)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    print(json.dumps({"precision": precision, "recall": recall, "f1": f1}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
