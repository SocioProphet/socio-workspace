from __future__ import annotations
from typing import Any, Dict, List
from transformers import AutoTokenizer, AutoModel
import torch

class EmbeddingsHFRunner:
    def __init__(self, hf_id: str, pooling: str = "mean"):
        self.hf_id = hf_id
        self.pooling = pooling
        self.tok = AutoTokenizer.from_pretrained(hf_id)
        self.model = AutoModel.from_pretrained(hf_id)
        self.model.eval()

    @torch.inference_mode()
    def infer(self, batch: List[Dict[str, Any]]):
        texts = [b.get("text","") for b in batch]
        toks = self.tok(texts, padding=True, truncation=True, return_tensors="pt")
        out = self.model(**toks)
        last = out.last_hidden_state  # [B,T,H]
        if self.pooling == "cls" and last.shape[1] > 0:
            emb = last[:, 0, :]
        else:
            mask = toks.get("attention_mask")
            if mask is not None:
                mask = mask.unsqueeze(-1)  # [B,T,1]
                summed = (last * mask).sum(dim=1)
                denom = mask.sum(dim=1).clamp(min=1)
                emb = summed / denom
            else:
                emb = last.mean(dim=1)
        return emb.detach().cpu().tolist()
