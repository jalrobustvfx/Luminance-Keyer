"""
Channel & Luminance Keyer Node for ComfyUI
Nuke-style keyer with R/G/B/A/Luminance channel selection.
Supports single images and video frame sequences (batches).
"""

import os
import torch
import numpy as np
from PIL import Image, ImageFilter
import folder_paths


class ChannelLuminanceKeyer:

    CATEGORY = "image/masking"
    FUNCTION = "key"
    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "channel": (["luminance", "red", "green", "blue", "alpha"],),
                "low_clip": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0,
                    "step": 0.001, "round": 0.001, "display": "slider",
                }),
                "high_clip": ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 1.0,
                    "step": 0.001, "round": 0.001, "display": "slider",
                }),
                "low_softness": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 0.5,
                    "step": 0.001, "round": 0.001, "display": "slider",
                }),
                "high_softness": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 0.5,
                    "step": 0.001, "round": 0.001, "display": "slider",
                }),
                "gamma": ("FLOAT", {
                    "default": 1.0, "min": 0.1, "max": 4.0,
                    "step": 0.01, "display": "slider",
                }),
                "gain": ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 4.0,
                    "step": 0.01, "display": "slider",
                }),
                "invert": ("BOOLEAN", {"default": False}),
                "blur_radius": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 100.0,
                    "step": 0.5, "display": "slider",
                }),
                "preview_frame": ("INT", {
                    "default": 0, "min": 0, "max": 9999, "step": 1,
                    "display": "slider",
                }),
            },
        }

    @staticmethod
    def _extract_channel(imgs: np.ndarray, channel: str) -> np.ndarray:
        ch = channel.lower()
        if ch == "luminance":
            return 0.2126*imgs[...,0] + 0.7152*imgs[...,1] + 0.0722*imgs[...,2]
        if ch == "red":   return imgs[..., 0].copy()
        if ch == "green": return imgs[..., 1].copy()
        if ch == "blue":  return imgs[..., 2].copy()
        if ch == "alpha":
            return imgs[..., 3].copy() if imgs.shape[-1] == 4 \
                   else np.ones(imgs.shape[:3], dtype=np.float32)
        return imgs[..., 0].copy()

    @staticmethod
    def _key_curve(v, lo, hi, lo_soft, hi_soft):
        lo, hi = min(lo, hi), max(lo, hi)
        if hi == lo:
            return np.where(v >= hi, 1.0, 0.0).astype(np.float32)
        r = hi - lo
        result = np.zeros_like(v)
        core = (v >= lo) & (v <= hi)
        result[core] = (v[core] - lo) / r
        result[v > hi] = 1.0
        lo_edge = max(0.0, lo - lo_soft)
        if lo_soft > 0 and lo > lo_edge:
            m = (v >= lo_edge) & (v < lo)
            t = (v[m] - lo_edge) / (lo - lo_edge)
            t = t * t * (3.0 - 2.0 * t)
            result[m] = t * ((v[m] - lo_edge) / r)
        return np.clip(result, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def _blur_matte(matte_hw: np.ndarray, radius: float) -> np.ndarray:
        """Gaussian blur on a single (H,W) float32 matte via PIL."""
        if radius <= 0:
            return matte_hw
        uint8 = (np.clip(matte_hw, 0, 1) * 255).astype(np.uint8)
        pil   = Image.fromarray(uint8, mode="L")
        pil   = pil.filter(ImageFilter.GaussianBlur(radius=radius))
        return np.array(pil, dtype=np.float32) / 255.0

    @staticmethod
    def _save_preview(matte_hw: np.ndarray) -> dict:
        grey = (np.clip(matte_hw, 0, 1) * 255).astype(np.uint8)
        rgb  = np.stack([grey, grey, grey], axis=-1)
        pil  = Image.fromarray(rgb, mode="RGB")
        tmp_dir  = folder_paths.get_temp_directory()
        filepath = os.path.join(tmp_dir, "keyer_preview.png")
        pil.save(filepath, compress_level=1)
        return {"filename": "keyer_preview.png", "subfolder": "", "type": "temp"}

    def key(self, image, channel, low_clip, high_clip,
            low_softness, high_softness, gamma, gain,
            invert, blur_radius=0.0, preview_frame=0):

        imgs  = image.cpu().numpy().astype(np.float32)
        B     = imgs.shape[0]

        matte = self._key_curve(
            self._extract_channel(imgs, channel),
            low_clip, high_clip, low_softness, high_softness,
        )

        matte = np.clip(matte * gain, 0.0, 1.0)
        if gamma != 1.0:
            matte = np.power(np.clip(matte, 1e-6, 1.0), 1.0 / gamma)
        if invert:
            matte = 1.0 - matte
        matte = np.clip(matte, 0.0, 1.0)

        # Per-frame blur (only if radius > 0)
        if blur_radius > 0:
            blurred = np.empty_like(matte)
            for b in range(B):
                blurred[b] = self._blur_matte(matte[b], blur_radius)
            matte = blurred

        pf       = int(np.clip(preview_frame, 0, B - 1))
        img_info = self._save_preview(matte[pf])

        return {
            "ui":     {"images": [img_info], "frame_count": [B]},
            "result": (torch.from_numpy(matte),),
        }


NODE_CLASS_MAPPINGS        = {"ChannelLuminanceKeyer": ChannelLuminanceKeyer}
NODE_DISPLAY_NAME_MAPPINGS = {"ChannelLuminanceKeyer": "🎯 Channel & Luminance Keyer"}
