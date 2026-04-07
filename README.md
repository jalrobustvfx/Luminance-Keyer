# 🎯 Channel & Luminance Keyer — ComfyUI Node

A Nuke-style **Channel & Luminance Keyer** that generates a clean black-and-white matte from any input image, with a **live in-node preview** that updates in real-time as you drag sliders — no queue required.

---

## Features

| Feature | Description |
|---|---|
| **5 key sources** | Luminance (Rec-709), Red, Green, Blue, Alpha |
| **Nuke-style clip points** | `low_clip` / `high_clip` define the key range |
| **Soft rolloff** | `low_softness` / `high_softness` add feathered transitions |
| **Gain + Gamma** | Post-process the matte curve |
| **Invert** | Flip the matte |
| **Second channel** | Optionally blend a second channel matte via Max / Min / Multiply / Add / Subtract |
| **Live preview** | In-node canvas showing the matte, clip guide lines, and a mini histogram |
| **Colour range bar** | Thin gradient bar on the node header showing your Lo/Hi key window |

---

<img width="2236" height="1045" alt="Capture" src="https://github.com/user-attachments/assets/685e2d03-fcb3-4fb6-8302-c79c4867ce1b" />


## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/your-handle/ComfyUI-ChannelKeyer.git
```

Or drop the folder directly into `custom_nodes/`.

---

## Node Inputs

| Input | Type | Description |
|---|---|---|
| `image` | IMAGE | Source image (RGB or RGBA) |
| `channel` | Enum | Which channel to key from |
| `low_clip` | Float 0–1 | Pixel values at or below this → black |
| `high_clip` | Float 0–1 | Pixel values at or above this → white |
| `low_softness` | Float 0–0.5 | Feather below the low clip |
| `high_softness` | Float 0–0.5 | Feather above the high clip |
| `gamma` | Float 0.1–4 | Gamma applied to the matte |
| `gain` | Float 0–4 | Gain (brightness multiplier) applied to the matte |
| `invert` | Bool | Invert the output matte |
| `second_channel` *(opt)* | Enum | A second channel to combine |
| `combine_op` *(opt)* | Enum | How to combine the two channel mattes |

## Node Outputs

| Output | Type | Description |
|---|---|---|
| `mask` | MASK | The computed B&W matte (use with other mask nodes) |
| `preview_image` | IMAGE | Greyscale matte as an IMAGE (for preview / saving) |

---

## How the Live Preview Works

The JavaScript extension (`web/js/channel_keyer.js`) does the following:

1. **After execution**, ComfyUI sends back the `preview_image` tensor. The JS receives it via `onExecuted` and loads the thumbnail into an offscreen `<canvas>`.
2. **On every widget change** (any slider, dropdown, checkbox), the JS re-runs the full key curve algorithm in the browser on the downsampled thumbnail pixels — no Python needed.
3. The result is painted into a `<canvas>` DOM widget embedded inside the node, with:
   - The greyscale matte
   - Blue / orange dashed guide lines for `low_clip` / `high_clip`
   - A mini histogram of the matte values (bottom-right corner)
4. A thin colour-range bar is drawn on the node header background via `onDrawBackground`.

This approach (browser-side pixel math on a thumbnail) gives **instant, zero-latency feedback** while you tweak parameters, matching the feel of Nuke's interactive keyer.

---

## Tips

- Start with **Luminance** for general mattes; switch to **Green** or **Blue** for greenscreen / bluescreen pulls.
- Use **low_softness** to feather semi-transparent edges (hair, smoke) into the key.
- Pair with a second channel (e.g., Luminance + Red combined with **Multiply**) to tighten difficult keys.
- Connect the `mask` output into a **Mask Blur** or **Mask Erode/Dilate** node for further refinement.
- The `preview_image` output can go to a **Preview Image** node to see the full-resolution result.

---

MIT License
