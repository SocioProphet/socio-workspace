
## TritRPC + Trit-to-Trust
- Added as submodules: third_party/tritrpc-v1-full and third_party/trit-to-trust
- Next: pin versions/tags + wire into manifest/workspace.toml + reference from protocol/ docs

## TritRPC + Trit-to-Trust (pinned)
- tritrpc-v1-full: tag v0.1.0
- trit-to-trust: tag v0.1.0

## TritRPC + Trit-to-Trust (pinned)
- tritrpc-v1-full: v0.1.1 @ 6091e55
- trit-to-trust:  v0.1.1 @ 68186ab
- Policy: do not move tags; bump patch tags for cleanup-only changes.

## TritRPC core (repin + de-commingle)
- TritRPC is a core project; pinned to v0.1.2
- Trit-to-Trust repo is no longer a workspace dependency (notes are folded into TritRPC/docs)

## TritRPC
- TritRPC is a core standalone project: SocioProphet/tritrpc-v1-full
- Workspace pins TritRPC by tag via submodule: third_party/tritrpc-v1-full (v0.1.2)
- Trit-to-Trust sources were folded into TritRPC docs; workspace no longer depends on trit-to-trust as a submodule.
