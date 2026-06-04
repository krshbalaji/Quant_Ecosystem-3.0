# PHASE114C Execution Router Dependency Audit

## Certified Baseline

Branch: pack225-runtime-defect-tests
Commit: dc84f38
Tag: PHASE114_PACK225_RUNTIME_DEFECTS_FIXED

Tests: 719 passed

---

## Low Coupling Components

### RetryGovernor

Init:
- 871

Usage:
- 3476

Difficulty:
- Easy

Recommendation:
- Future extraction candidate

---

### LiquidityGuard

Init:
- 788

Usage:
- 1661
- 4523

Difficulty:
- Easy

Recommendation:
- Future extraction candidate

---

### RecoveryReconciler

Init:
- 807

Usage:
- 817
- 843

Difficulty:
- Medium

Recommendation:
- Candidate for future service extraction

---

## High Coupling Components

### MultiBrokerRouter

Init:
- 2474

Usage:
- 2485
- 2931
- 2941
- 2951
- 2961
- 3309
- 3313
- 3614
- 3791
- 4511

Difficulty:
- Hard

Recommendation:
- Retain in runtime core

---

### ExecutionDispatcher

Init:
- 854

Usage:
- 1120
- 1807

Difficulty:
- Hard

Recommendation:
- Retain in runtime core

---

### IntentJournal

Init:
- 805

Usage:
- 1716
- 1723
- 1730
- 1762
- 1802
- 1859
- 1918
- 2004

Difficulty:
- Very Hard

Recommendation:
- Retain in runtime core

---

### MeshCoordinator

Init:
- 869

Usage:
- 870
- 1746
- 1903
- 2100

Difficulty:
- Hard

Recommendation:
- Retain in runtime core

---

### KillHierarchy

Init:
- 866

Usage:
- 1651
- 2612-2677

Difficulty:
- Very Hard

Recommendation:
- Retain in runtime core