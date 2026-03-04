"""Training pipeline for adaptive regime model."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List

from quant_ecosystem.regime_ai.regime_classifier import REGIMES


class _CentroidModel:
    """Lightweight fallback classifier when sklearn is unavailable."""

    def __init__(self, centroids: Dict[str, List[float]]):
        self.centroids = centroids

    def predict(self, X: List[List[float]]) -> List[str]:
        out = []
        for row in X:
            out.append(self._nearest(row))
        return out

    def predict_proba(self, X: List[List[float]]) -> List[List[float]]:
        out = []
        for row in X:
            dists = {}
            for label, centroid in self.centroids.items():
                d = self._distance(row, centroid)
                dists[label] = 1.0 / max(d, 1e-6)
            total = sum(dists.values())
            probs = [(dists.get(label, 0.0) / total) if total > 0 else 0.0 for label in REGIMES]
            out.append(probs)
        return out

    def _nearest(self, row: List[float]) -> str:
        best_label = REGIMES[0]
        best_dist = float("inf")
        for label, centroid in self.centroids.items():
            d = self._distance(row, centroid)
            if d < best_dist:
                best_dist = d
                best_label = label
        return best_label

    def _distance(self, a: List[float], b: List[float]) -> float:
        n = min(len(a), len(b))
        if n == 0:
            return 1e9
        return sum((a[i] - b[i]) ** 2 for i in range(n)) ** 0.5


class RegimeTrainer:
    """Trains and saves AI regime model (with robust fallback path)."""

    def __init__(self, model_path: str = "quant_ecosystem/regime_ai/models/regime_model.pkl"):
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

    def train(self, dataset_rows: List[Dict]) -> Dict:
        """Train model from dataset rows and persist to disk."""
        if not dataset_rows:
            return {"trained": False, "reason": "empty_dataset"}

        X = [list(row.get("features", [])) for row in dataset_rows]
        y = [str(row.get("regime_label", "RANGE_BOUND")).upper() for row in dataset_rows]

        model = None
        accuracy = 0.0
        model_type = "CENTROID"

        try:
            # Optional dependency path.
            from sklearn.ensemble import RandomForestClassifier  # type: ignore
            from sklearn.model_selection import train_test_split  # type: ignore
            from sklearn.metrics import accuracy_score  # type: ignore

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
            )
            clf = RandomForestClassifier(
                n_estimators=120,
                max_depth=8,
                random_state=42,
                class_weight="balanced",
            )
            clf.fit(X_train, y_train)
            pred = clf.predict(X_test)
            accuracy = float(accuracy_score(y_test, pred))
            model = clf
            model_type = "RANDOM_FOREST"
        except Exception:
            centroids = self._build_centroids(X, y)
            model = _CentroidModel(centroids)
            # Self-eval on train set
            pred = model.predict(X)
            correct = sum(1 for i in range(len(y)) if pred[i] == y[i])
            accuracy = (correct / len(y)) if y else 0.0
            model_type = "CENTROID"

        payload = {"model": model, "model_type": model_type, "accuracy": round(accuracy, 6)}
        with self.model_path.open("wb") as handle:
            pickle.dump(payload, handle)

        return {
            "trained": True,
            "model_type": model_type,
            "accuracy": round(accuracy, 6),
            "path": str(self.model_path),
            "samples": len(dataset_rows),
        }

    def _build_centroids(self, X: List[List[float]], y: List[str]) -> Dict[str, List[float]]:
        by_label: Dict[str, List[List[float]]] = {}
        for i, label in enumerate(y):
            by_label.setdefault(label, []).append(X[i])
        centroids: Dict[str, List[float]] = {}
        for label, rows in by_label.items():
            n = len(rows)
            width = min(len(r) for r in rows) if rows else 0
            if width == 0 or n == 0:
                continue
            centroid = []
            for j in range(width):
                centroid.append(sum(rows[i][j] for i in range(n)) / n)
            centroids[label] = centroid
        if not centroids:
            centroids["RANGE_BOUND"] = [0.0 for _ in range(len(X[0]) if X else 1)]
        return centroids

