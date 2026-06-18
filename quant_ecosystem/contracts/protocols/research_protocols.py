from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class SupportsResearchNode(Protocol):
    def execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ...

class SupportsExperimentTracker(Protocol):
    def start_run(
        self,
        experiment_name: str,
        run_type: str = ...,
        params: Optional[Dict[str, Any]] = ...,
    ) -> str:
        ...

    def end_run(
        self,
        run_id: str,
        metrics: Optional[Dict[str, float]] = ...,
        status: str = ...,
    ) -> Any:
        ...


class SupportsResearchScheduler(Protocol):
    def add_job(
        self,
        name: str,
        fn: Any,
        interval_seconds: Optional[float] = ...,
        priority: int = ...,
    ) -> str:
        ...

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


class SupportsGenomeEvaluator(Protocol):
    def evaluate_genomes(
        self,
        genomes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        ...


class SupportsResearchPipeline(Protocol):
    def run_cycle(
        self,
        n_candidates: int = ...,
        periods: int = ...,
    ) -> Dict[str, Any]:
        ...        