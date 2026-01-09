# Training HA Modes (AA / AP / PA / PP)

## Definitions
- Active: executes training and can propose candidates; may have promotion authority.
- Passive: does not train/promote by default; replicates datasets/models and can fail over.

## Modes
### Active–Active (AA)
Both sites train and produce candidates. Promotion MUST be single-writer or quorum-gated to prevent split-brain.

### Active–Passive (AP)
Primary site trains/promotes. Secondary replicates and stands by. Failover flips roles.

### Passive–Active (PA)
Mirror of AP with the other site as primary for training/promote.

### Passive–Passive (PP)
Neither site trains by default. Training occurs on-demand/offline and releases are imported, verified, and promoted.
