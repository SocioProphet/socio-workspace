# Cosign Signing & Verification

## Sign
cosign sign-blob --yes --key cosign.key artifact.bin > artifact.sig

## Verify
cosign verify-blob --key cosign.pub --signature artifact.sig artifact.bin

## Attest
cosign attest --predicate predicate.json --key cosign.key <image-or-blob>
