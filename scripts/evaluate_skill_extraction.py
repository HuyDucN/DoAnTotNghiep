"""Danh gia trich xuat ky nang: Precision/Recall/F1 micro + macro, chuan hoa ten."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.skill_names import normalize_skill_name


def load_sets(path: Path) -> dict[str, set[str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r["id"]: {normalize_skill_name(s) for s in r.get("skills", [])} for r in rows}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/evaluate_skill_extraction.py predictions.json")
        return 2
    root = Path(__file__).resolve().parents[1]
    truth = load_sets(root / "data/ground_truth/skill_extraction.json")
    predicted = load_sets(Path(sys.argv[1]))
    tp = fp = fn = 0
    per_sample = []
    precisions, recalls, f1s = [], [], []
    for sid, actual in sorted(truth.items()):
        guess = predicted.get(sid, set())
        s_tp = len(actual & guess)
        s_fp = len(guess - actual)
        s_fn = len(actual - guess)
        tp += s_tp
        fp += s_fp
        fn += s_fn
        p = s_tp / (s_tp + s_fp) if s_tp + s_fp else (1.0 if not actual and not guess else 0.0)
        r = s_tp / (s_tp + s_fn) if s_tp + s_fn else 1.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        precisions.append(p)
        recalls.append(r)
        f1s.append(f)
        per_sample.append({
            "id": sid,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
            "missing": sorted(actual - guess),
            "extra": sorted(guess - actual),
        })
    micro_p = tp / (tp + fp) if tp + fp else 0.0
    micro_r = tp / (tp + fn) if tp + fn else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    n = len(truth)
    report = {
        "samples": n,
        "micro": {"precision": round(micro_p, 4), "recall": round(micro_r, 4), "f1": round(micro_f1, 4)},
        "macro": {
            "precision": round(sum(precisions) / n, 4) if n else 0.0,
            "recall": round(sum(recalls) / n, 4) if n else 0.0,
            "f1": round(sum(f1s) / n, 4) if n else 0.0,
        },
        "per_sample": per_sample,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    out = root / "docs" / "skill_extraction_eval.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Da luu bao cao: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
