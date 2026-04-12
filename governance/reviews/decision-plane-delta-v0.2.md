# Decision Plane Delta from v0.1 to v0.2

## Material strategy changes

- SDP-1 now centers `policy-fabric` as the operational governance/control anchor.
- SDP-3 now explicitly includes `cloudshell-fog` as a cloud-edge execution anchor.
- SDP-4 now explicitly includes `ontogenesis` and `memory-mesh`.
- SDP-5 now treats Digital / Trust as an active surface boundary, not a future packaging note.
- SDP-6 now explicitly binds to `policy-fabric` as a policy-control support anchor.

## Process changes

- product-surface reconciliation should key off `config/surfaces.json`
- merge planning now considers current open PR path and semantic overlap risk
- old repo-drop assets should be regenerated from v0.2 inputs rather than reused unchanged
