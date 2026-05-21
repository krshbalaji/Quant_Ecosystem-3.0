# ARCHITECTURE_DECISION

Decision: Adopt `quant_ecosystem-3.0-git-FRESH` as the canonical base (hybrid with selective recoveries from QE3 and other local copies).

Justification (concise):

- Runtime integrity: `quant_ecosystem-3.0-git-FRESH` contains the complete `SystemFactory` wiring that expresses the canonical boot sequence (`main.py` → `SystemFactory.build()` → core/execution/strategy layers). See forensic mapping: [FORENSIC_AUDIT_OUTPUT/RUNTIME_WIRING_MAP.md](FORENSIC_AUDIT_OUTPUT/RUNTIME_WIRING_MAP.md#L1).
- Module completeness: FRESH includes production-grade `quant_ecosystem/risk/risk_engine.py`, strategy registry, synthetic backtester, and most integration layers required to run a PAPER-mode system. Where richer implementations exist (notably `execution_router` in `QE3`), we will selectively recover those implementations into FRESH.
- Dead code ratio: FRESH has some legacy standalone scripts (e.g., `execution_engine_v2.py`) and duplicated modules across local repos, but overall contains the majority of up-to-date modules and the DI factory. This lowers merge surface and reduces forensic rework.
- Repair effort: fewer cross-repo edits required when upgrading FRESH (SystemFactory already present and used by `main.py`), while QE3 contains deeper ExecutionRouter code that can be selectively imported. Using FRESH as base minimizes invasive refactors.
- Extensibility: FRESH's `SystemFactory` shows explicit DI, clearly exposing injection points for recovered modules (broker adapters, execution router, research grid). This favors safe, incremental module replacement.
- Research loop compatibility: FRESH contains `synthetic_backtester.py`, `research` modules, and `alpha` engines required for research flows.
- Backtesting & paper readiness: FRESH boots PAPER mode by default and includes `broker/paper_broker.py` and a `Paper`-capable ExecutionRouter wiring.

Recommendation summary:
- Canonical base: `quant_ecosystem-3.0-git-FRESH` (this workspace).
- Recovery approach: selective hybrid recovery — import the strongest modules from `QE3` (notably `execution_router` implementation) and `quant_ecosystem-3.0-git` (broker wrappers/adapters) into the FRESH codebase.
- Safety constraints: All changes performed under a recovery snapshot (RECOVERY_SNAPSHOT_YYYYMMDD_HHMM). No live-broker activation; enforce PAPER-only operation during recovery and self-tests.

Evidence sources: FORENSIC_AUDIT_OUTPUT/* (TOP_PRIORITY_CODE_FORENSICS.md, RUNTIME_WIRING_MAP.md, BROKEN_VS_GOOD_VERSION_MATRIX.md, FORENSIC_VALIDATION_SUMMARY.md, shortlist_forensics.json)
