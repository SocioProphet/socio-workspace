## SocioProphet — Unified CC + Eval + Forensics

This patch adds:
- **Runners**: Embeddings (HF), ASR (Whisper via HF), Vision Classification (ONNX).
- **Configs**: sample experiments for embedding/ASR/vision.
- Works with the Champion–Challenger Router (Ray Serve), Prophet CLI plugin, vendor-neutral secrets, forensics & crypto carriers.

### Quickstart
```bash
# Offline eval
python cc/run_eval.py --config configs/experiment.embedding.sentence.yaml --key-metric cosine

# Start router (see Kustomize/serve_app.py)
python serve_app.py
# Admin policy: 100% champion
curl -X POST :8000/admin/policy -H "X-Admin-Token:$ADMIN_TOKEN" -d '{"weights":{"all-MiniLM-L6-v2":1.0}}'
```

### Online scoring
Send payloads with inline targets for rewards:
```json
{ "task":"classification", "inputs":[{"text":"great","label":1}] }
{ "task":"text-generation", "inputs":[{"prompt":"Translate bonjour","target":"hello"}] }
{ "task":"embedding", "inputs":[{"text":"foo","target_embedding":[0.1,0.3,...]}] }
```

### Prophet CLI
- `prophet ai eval serve|policy|rollout|metrics|run`
- `prophet diag crypto --dual --publish --probe`

See project README for full admin endpoints and forensics pipeline (COSE carriers, schema, validate-then-replay, Kafka).
