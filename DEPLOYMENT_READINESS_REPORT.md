# Deployment Readiness Report

Generated: 2026-06-18 16:33:06

| Target | Readiness | Present capabilities | Missing/weak capabilities | Gate before deployment |
| --- | --- | --- | --- | --- |
| Research Platform | Ready with validation | Research, Strategy Discovery, Market Data, Reporting, Learning | Canonical experiment/model registry policy; reproducible promotion gate | Run research smoke suite and freeze strategy metadata schema. |
| Paper Trading | Ready with validation | Execution, Broker Integration, Risk, Market Data, Operations | single paper/live adapter contract; paper broker parity evidence | Run paper execution replay and broker fault simulation before extending scope. |
| Shadow Portfolio | Partially ready | Execution, Portfolio Management, Risk, Reporting, Audit | shadow-to-live promotion evidence; position reconciliation proof | Complete shadow portfolio reconciliation and performance attribution checks. |
| Personal Capital | Not ready for live capital | Execution, Risk, Broker Integration, Governance, Operations | live broker certification; kill-switch drill evidence; secrets/permissions hardening | Require end-to-end live dry-run, human approval gate, and rollback path. |
| Multi-Account Trading | Architecture present; not production ready | OMS, Accounting, Broker Integration, Risk, Governance | account hierarchy; allocation/reconciliation per account; ledger reporting | Implement account-level ledger, permissions, and reconciliation tests. |
| Multi-Broker Trading | Partially ready | Broker Integration, OMS, Execution, Risk, Audit | broker parity matrix; failover operating rules; live broker certification | Prove failover, no-paper-fallback behavior, and broker response normalization. |
| Family Office Scale | Architecture/research only | Accounting, Governance, Audit, Reporting, Cloud | entity accounting; compliance workflows; ops ownership; disaster recovery | Add governance workflows, release management, and financial reporting controls. |
| Institutional Scale | Architecture/research only | OMS, Accounting, Governance, Audit, Cloud, API, Operations | RBAC; SLA observability; formal compliance; deployment certification | Treat as a roadmap target after live personal-capital proof and CI maturity. |

## Readiness Notes
- Research and paper workflows have the strongest on-disk evidence: strategy labs, research engines, synthetic markets, market data modules, and paper broker paths are present.
- Live personal-capital readiness is blocked by broker contract normalization, runtime kill-switch proof, secrets handling, and audited execution replay.
- Multi-account, family office, and institutional modes are architectural ambitions today; OMS, accounting ledger, compliance workflow, role controls, and production observability remain weak or missing.
