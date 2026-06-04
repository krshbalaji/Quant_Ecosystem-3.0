# PHASE114C Extraction Boundaries

## Extractable Support Services

- RetryGovernor
- LiquidityGuard
- DuplicateOrderGuard
- MarketHoursGuard
- RecoveryReconciler
- SnapshotBuilder

## Runtime Core

- MultiBrokerRouter
- ExecutionDispatcher
- IntentJournal
- MeshCoordinator
- KillHierarchy

## Architectural Conclusion

ExecutionRouter should not be decomposed by line count.

Future decomposition should follow subsystem ownership boundaries.

Support services may be extracted.

Runtime-core components should remain co-located until significantly larger regression coverage exists.