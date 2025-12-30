from __future__ import annotations
from typing import Any, Dict, List
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
import torch

class WhisperHFRunner:
    def __init__(self, hf_id: str, device: str | None = None, language: str | None = None, task: str | None = None):
        self.hf_id = hf_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoProcessor.from_pretrained(hf_id)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(hf_id).to(self.device)
        self.model.eval()
        self.generation_kwargs = {}
        if language: self.generation_kwargs["language"] = language
        if task: self.generation_kwargs["task"] = task

    @torch.inference_mode()
    def infer(self, batch: List[Dict[str, Any]]):
        waves = []
        for b in batch:
            x = b.get("audio")
            if isinstance(x, str):
                import soundfile as sf
                wav, sr = sf.read(x)
            else:
                wav = x; sr = self.processor.feature_extractor.sampling_rate
            if sr != self.processor.feature_extractor.sampling_rate:
                import librosa
                wav = librosa.resample(wav, orig_sr=sr, target_sr=self.processor.feature_extractor.sampling_rate)
            waves.append(wav)
        inputs = self.processor(waves, sampling_rate=self.processor.feature_extractor.sampling_rate, return_tensors="pt").to(self.device)
        gen = self.model.generate(**inputs, **self.generation_kwargs)
        texts = self.processor.batch_decode(gen, skip_special_tokens=True)
        return texts
