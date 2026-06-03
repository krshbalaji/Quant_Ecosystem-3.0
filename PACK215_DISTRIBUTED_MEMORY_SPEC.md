PACK215 Distributed Memory Specification
========================================

Branch: `release/qe3-v1-institutional`
Baseline: `693 passing tests`

Purpose
-------
Define the architecture for distributed memory mesh shadow integration and replication compatibility with the existing audit replay foundation.
This specification is architecture-only: no code, no migrations, no implementation.

Scope
-----
This spec covers:
- `DistributedMemoryMesh`
- `SovereignMemoryReplicationEngine`
- `MemoryLineage`
- `ExecutionLineage`
- `MultiMapStore`
- `MemoryEventAdapter`
- `AuditReplayEngine`

It does not propose any runtime read-path changes, API surface changes, or persistence migrations.

Foundations
-----------
The current system already contains:
- `MultiMapStore` as an in-memory append-only audit store with `put`, `get`, `latest`, `keys`, and `size`.
- `ExecutionLineage` and `MemoryLineage` as legacy lineage containers with shadow writes into `audit.execution.lineage.<lineage_id>`.
- `DistributedMemoryMesh` as a mesh of snapshots accepted by `FederationMemoryContract`.
- `SovereignMemoryReplicationEngine` as a replication engine that synchronizes snapshots and writes lineage.
- `MemoryEventAdapter` that persists arbitrary events into `MultiMapStore` by event type name.
- `AuditReplayEngine` as a read-only replay layer over audit keys.

Current Audit Key Patterns
--------------------------
The current audit persistence foundation uses canonical audit keys:
- `audit.execution.lineage.<lineage_id>` for lineage snapshots and events
- `audit.execution.lineage_registry` for registered lineage IDs
- `audit.topology.namespace_registry` for namespace topology audit results

Shadow Integration Strategy
---------------------------
The distributed memory mesh integration must preserve legacy production behavior while adding non-authoritative shadow visibility.

Strategy:
- `DistributedMemoryMesh` remains the authoritative snapshot aggregator.
- `SovereignMemoryReplicationEngine.replicate()` continues to:
  1. validate and synchronize a snapshot with `DistributedMemoryMesh`
  2. append the snapshot to `MemoryLineage`
- `MemoryLineage.append()` continues to write lineage snapshots to the legacy in-memory `_lineages` store.
- `MemoryLineage.append()` may optionally emit the same snapshot into `MultiMapStore` under `audit.execution.lineage.<lineage_id>` as shadow parity.
- Shadow writes are strictly non-primary and must not affect authorization, synchronization, or legacy replication semantics.

Replication Strategy
--------------------
Replication concerns for the distributed memory mesh are:
- snapshot propagation
- lineage propagation
- replication safety

Snapshot propagation
~~~~~~~~~~~~~~~~~~~~
- `DistributedMemoryMesh.synchronize(snapshot, contract)` remains the gatekeeper.
- if the contract allows the snapshot, the mesh accepts it and appends it to `snapshots`.
- if the contract rejects the snapshot, replication returns `False` and no lineage write occurs.

Lineage propagation
~~~~~~~~~~~~~~~~~~~
- `SovereignMemoryReplicationEngine.replicate()` must continue legacy propagation by appending the accepted snapshot to `MemoryLineage`.
- this is the production path for lineage lookups through `latest_memory()` and `get_lineage()`.

Replication safety
~~~~~~~~~~~~~~~~~~
- Shadow persistence is disabled by default in governance mode.
- Any shadow write path must be optional and wrapped in a try/except that swallows errors.
- The replication engine must preserve boolean success semantics: `False` on sync failure, `True` on accepted replication.
- No shadow write may alter the return value of `replicate()` or the legacy mesh/lineage state.

Replay Compatibility
--------------------
The distributed memory mesh architecture must remain compatible with the existing audit replay foundation.

Compatibility requirements:
- shadow lineage snapshots written to `audit.execution.lineage.<lineage_id>` must be readable by `AuditReplayEngine`.
- `MemoryLineage` must continue to support legacy read methods (`get_lineage`, `latest`) without modification.
- `AuditReplayEngine` must continue to resolve lineage queries through `audit.execution.lineage.<lineage_id>`.
- namespace and topology filters must remain compatible with existing `audit.topology.namespace_registry` patterns.

If new audit key families are introduced for mesh snapshots, they must still respect the `audit.*` naming contract and not replace legacy lineage keys.

Safety
------
The distributed memory mesh package must obey strict governance safety rules.

Safety rules:
- Shadow writes only: extensions may persist audit data into `MultiMapStore` only as a non-authoritative, diagnostic path.
- No read-path changes: legacy `MemoryLineage` and `ExecutionLineage` state must continue to be the source of truth.
- No API changes: method signatures and external behavior of `DistributedMemoryMesh`, `SovereignMemoryReplicationEngine`, and lineage classes remain stable.
- No replication behavior changes: replication success/failure logic is unchanged.
- No EventBus publishing, no execution triggering, no routing triggering, no governance mutation.

Rollback
--------
Governance must preserve a clean rollback path.

Rollback rules:
- `MemoryLineage` shadow writes may be disabled via a configuration flag or governance switch.
- when disabled, `SovereignMemoryReplicationEngine` and `DistributedMemoryMesh` must behave exactly as before.
- disabling shadow writes must not change legacy memory snapshot storage, replication success semantics, or lineage retrieval.
- no automatic rollback of snapshots or mesh state is introduced by the shadow architecture.

Non-goals
--------
- No durable storage or migration strategies are proposed.
- No changes to `EventBus`, routing, or governance execution paths.
- No modifications to legacy method signatures or public APIs.
- No new authorization or contract semantics beyond existing `FederationMemoryContract`.
