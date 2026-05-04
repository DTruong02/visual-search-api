from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import open_clip
import torch
from PIL import Image

from app.core.config import get_settings


@dataclass(frozen=True)
class ClipBundle:
    model: torch.nn.Module
    preprocess: object
    tokenizer: object
    device: torch.device


_bundle: ClipBundle | None = None


def get_clip() -> ClipBundle:
    global _bundle
    if _bundle is not None:
        return _bundle

    s = get_settings()
    device = torch.device(s.embedding_device)
    model, _, preprocess = open_clip.create_model_and_transforms(s.model_name, pretrained=s.model_pretrained)
    tokenizer = open_clip.get_tokenizer(s.model_name)

    model.to(device)
    model.eval()

    _bundle = ClipBundle(model=model, preprocess=preprocess, tokenizer=tokenizer, device=device)
    return _bundle


@torch.inference_mode()
def embed_image(pil_img: Image.Image) -> list[float]:
    b = get_clip()
    img = b.preprocess(pil_img).unsqueeze(0).to(b.device)
    feats = b.model.encode_image(img)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    v = feats[0].detach().cpu().float().numpy()
    return v.tolist()


@torch.inference_mode()
def embed_text(text: str) -> list[float]:
    b = get_clip()
    tokens = b.tokenizer([text])
    if isinstance(tokens, torch.Tensor):
        tokens = tokens.to(b.device)
    feats = b.model.encode_text(tokens)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    v = feats[0].detach().cpu().float().numpy()
    return v.tolist()


def embedding_dim() -> int:
    # Compute once from a dummy forward; cached model makes this cheap.
    b = get_clip()
    with torch.inference_mode():
        tokens = b.tokenizer(["dim_probe"])
        if isinstance(tokens, torch.Tensor):
            tokens = tokens.to(b.device)
        feats = b.model.encode_text(tokens)
        return int(feats.shape[-1])

