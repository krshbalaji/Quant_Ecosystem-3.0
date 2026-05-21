**Forensic Validation Summary**

- **Scope:** PHASE 2A.4 strict read-only validation of prior forensic claims.
- **Outcome:** Evidence-backed cross-checks, contradiction audit, and canonical base recommendation.

**A) Cross-check — key forensic claims with exact file+line evidence**

- `execution_engine_v2.py` — undefined variable bug (NameError): evidence lines [execution_engine_v2.py](execution_engine_v2.py#L31) and [execution_engine_v2.py](execution_engine_v2.py#L68) show `entry = pos.get("entry_price")` and later `pnl = calculate_pnl(entry_price, current_price, side)` (mismatched names).
- `main.py` — canonical runtime entry and router build: [main.py](main.py#L30) (`factory = SystemFactory()`), [main.py](main.py#L34) (`router = factory.build()`), [main.py](main.py#L39) (`if hasattr(router, "execution_router"):`).
- `quant_ecosystem/core/system_factory.py` — core wiring:
  - Risk engine import: [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L353).
  - BrokerRouter import points: [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L806) and [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L902).
  - ExecutionRouter import & init: [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L850) and instantiation [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L852).
  - Strategy engine wiring: [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L929) and creation [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L937).
- Broker implementations (paper broker copies): root [broker/paper_broker.py](broker/paper_broker.py#L1) and package copy [quant_ecosystem/broker/paper_broker.py](quant_ecosystem/broker/paper_broker.py#L3).
- Signal manager (module-level signal lifecycle): [signal_manager.py](signal_manager.py#L24).
- Telegram notifier: `send_telegram(message)` at [telegram_notifier.py](telegram_notifier.py#L10).
- Regime memory presence and tests:
  - `RegimeMemory` class: [quant_ecosystem/intelligence/regime_memory.py](quant_ecosystem/intelligence/regime_memory.py#L36).
  - Tests: [quant_ecosystem/tests/test_regime_memory.py](quant_ecosystem/tests/test_regime_memory.py#L9) and [quant_ecosystem/tests/test_regime_memory.py](quant_ecosystem/tests/test_regime_memory.py#L50).

**B) Runtime truth classification (LIVE / PARTIAL / STUB / UNKNOWN)**

- `main.py` entrypoint: LIVE — calls `SystemFactory()` and `factory.build()` ([main.py](main.py#L30), [main.py](main.py#L34)).
- `SystemFactory` core wiring: LIVE — imports and instantiates `RiskEngine`, `ExecutionRouter`, `BrokerRouter`, and strategy engine ([quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L353), [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L850-L852), [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L929-L937), [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L806)).
- `ExecutionRouter`: LIVE (instantiated and started where factory wiring allows) — see instantiation [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L852).
- Broker subsystem: PARTIAL — working `PaperBroker` implementations exist, plus `quant_ecosystem` broker router/manager, but multiple copies/adapters exist and behavior varies ([broker/paper_broker.py](broker/paper_broker.py#L1), [quant_ecosystem/broker/paper_broker.py](quant_ecosystem/broker/paper_broker.py#L3), [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L806)).
- RiskEngine: LIVE — imported/used by SystemFactory ([quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L353)).
- StrategyRegistry / LiveStrategyEngine: LIVE (wired into ExecutionRouter) — [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L929-L937).
- RegimeMemory & RegimeService: LIVE/PRESENT — implementation and tests present ([quant_ecosystem/intelligence/regime_memory.py](quant_ecosystem/intelligence/regime_memory.py#L36), [quant_ecosystem/intelligence/regime_service.py](quant_ecosystem/intelligence/regime_service.py#L25)).

**C) Contradiction audit (claims vs actual references)**

- Claim: `execution_engine_v2.py` is the canonical live engine — Reality: it is a standalone executor script present at repo root and referenced by `cloudrun_app.py` ([execution_engine_v2.py](execution_engine_v2.py#L31), [execution_engine_v2.py](execution_engine_v2.py#L68); [cloudrun_app.py](cloudrun_app.py#L11)), but the canonical runtime path used by `main.py` is `SystemFactory` → `ExecutionRouter` (see [main.py](main.py#L30-L39) and [quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L850-L852)). Recommendation: treat `execution_engine_v2.py` as a separate utility/legacy script until reconciled.
- Claim: single broker implementation — Reality: multiple broker implementations and adapters (root `broker/` vs `quant_ecosystem/broker/`) exist; SystemFactory favors `quant_ecosystem` router/manager wiring ([quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L806)).

**D) Canonical base recommendation (choose one)**

- Recommendation: adopt `quant_ecosystem-3.0-git-FRESH` (this workspace) as the canonical base.
  - Rationale (concise): contains the complete `SystemFactory` wiring with `ExecutionRouter` instantiation ([quant_ecosystem/core/system_factory.py](quant_ecosystem/core/system_factory.py#L850-L852)), has `RegimeMemory` implementation and tests ([quant_ecosystem/intelligence/regime_memory.py](quant_ecosystem/intelligence/regime_memory.py#L36); [quant_ecosystem/tests/test_regime_memory.py](quant_ecosystem/tests/test_regime_memory.py#L9)), includes telemetry, execution, and integration scaffolding, and already contains the detailed forensic artifacts (FORENSIC_AUDIT_OUTPUT) — minimizing additional forensic work and merge risk.
  - Risks: repo contains duplicated modules and legacy standalone scripts (e.g., `execution_engine_v2.py`) that must be reconciled; some adapters exist in other local copies.

**E) Next steps (read-only deliverables available on request)**

- If approved, produce exact per-file, per-line read-only diffs between the shortlisted duplicates (up to 12 files) to support a non-destructive merge plan.
- Produce a prioritized repair checklist for critical runtime issues (start with `execution_engine_v2.py` safe-fix and ExecutionRouter integration testing).

-- End of FORENSIC VALIDATION SUMMARY
