# LTX-Video Mastery Guide

> A complete, practical guide to mastering [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) — from first install to training your own control LoRAs.
> Compiled from the official repo README, pipeline configs, ComfyUI-LTXVideo, LTX-Video-Trainer docs, and the Hugging Face Diffusers integration. (June 2026)

---

## Table of Contents

1. [What LTX-Video Is (and Why It's Fast)](#1-what-ltx-video-is)
2. [Ecosystem Map — Know Before You Start](#2-ecosystem-map)
3. [Model Catalog — Choosing Your Checkpoint](#3-model-catalog)
4. [Installation](#4-installation)
5. [First Generations (CLI)](#5-first-generations-cli)
6. [Understanding Pipeline Configs (the Real Power Lever)](#6-pipeline-configs)
7. [Prompt Engineering Masterclass](#7-prompt-engineering)
8. [Parameter Reference & Rules](#8-parameter-reference)
9. [The Diffusers Path (Python, Low VRAM, Long Video)](#9-diffusers-path)
10. [The ComfyUI Path (Node Workflows)](#10-comfyui-path)
11. [Control Models — IC-LoRA (Depth / Pose / Canny)](#11-control-models)
12. [Training Your Own LoRAs](#12-training)
13. [Performance Optimization Stack](#13-performance)
14. [Troubleshooting](#14-troubleshooting)
15. [30-Day Mastery Roadmap](#15-roadmap)
16. [Resources](#16-resources)

---

## 1. What LTX-Video Is

LTX-Video is the **first DiT-based (Diffusion Transformer) video generation model** designed for *real-time* generation — it can produce video faster than playback speed on an H100. Its core capabilities, all in **one model**:

- **Text-to-video** (T2V)
- **Image-to-video** (I2V) — animate a still image
- **Multi-keyframe animation** — condition on several images/clips at chosen frame positions
- **Video extension** — extend an existing clip forward *or* backward in time
- **Video-to-video** with structural control (depth / pose / canny via IC-LoRA)

### Why it's fast: the Video-VAE

The secret weapon is its **Video-VAE with a 1:192 pixel-to-latent compression ratio** (far higher than typical image VAEs). The model denoises in an extremely compact latent space, and the VAE decoder performs **the final denoising step *during* decoding** — recovering fine detail that the aggressive compression would otherwise lose.

### The multi-scale pipeline (v0.9.7+)

Modern LTX-Video configs are `pipeline_type: multi-scale`:

1. **First pass** — generate the whole video at ~⅔ resolution (`downscale_factor: 0.6666`)
2. **Latent upscale** — a dedicated *spatial latent upsampler* model 2×'s the latents
3. **Second pass** — a few denoise steps at full resolution to restore texture

This is why generations are both fast *and* sharp. Understand this and the configs stop being magic.

- Paper: <https://arxiv.org/abs/2501.00103>
- License: Apache-2.0, ~10.5k stars, Python 100%

---

## 2. Ecosystem Map

**⚠️ Important 2026 context:** Since October 2025, Lightricks' primary focus is **LTX-2** — a newer unified foundation model (up to 22B params) adding **synchronized audio+video**, up to 50 FPS, and native 4K. The LTX-Video repo (v0.9.8) remains fully functional and is the better entry point for consumer GPUs; LTX-2 needs ~32GB VRAM in ComfyUI. Master LTX-Video first — the concepts (multi-scale, IC-LoRA, distilled vs dev) carry directly into LTX-2.

| Repo / Tool | Role |
|---|---|
| [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) | Core model + standalone inference (`inference.py`, configs) |
| [Lightricks/ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) | Official ComfyUI nodes + example workflows (now LTX-2-first) |
| [Lightricks/LTX-Video-Trainer](https://github.com/Lightricks/LTX-Video-Trainer) | LoRA / full fine-tune / IC-LoRA training |
| [Lightricks/LTXVideo-Q8-Kernels](https://github.com/Lightricks/LTXVideo-Q8-Kernels) | FP8 kernels for Ada GPUs (RTX 40xx) |
| Diffusers (`LTXPipeline` etc.) | Hugging Face integration, best for Python + low VRAM |
| LTX-Studio / Fal.ai / Replicate | Zero-install online inference |
| Community: ComfyUI-LTXTricks | RF-Inversion, RF-Edit, FlowEdit, interpolation |
| Community: TeaCache | ~2× inference speedup via step caching |

---

## 3. Model Catalog

All checkpoints live under the [Lightricks Hugging Face org](https://huggingface.co/Lightricks). Current stable generation: **0.9.8**.

| Checkpoint | Size | Character | Pick it when… |
|---|---|---|---|
| `ltxv-13b-0.9.8-dev` | 13B | Max quality, full CFG+STG sampling, ~30+ steps | Final production renders, you have ≥24GB VRAM |
| `ltxv-13b-0.9.8-distilled` | 13B | Guidance+timestep distilled: **4–10 steps**, near-dev quality | **Default choice.** Iteration, real-time on H100 |
| `ltxv-2b-0.9.8-distilled` | 2B | Lightweight, lowest VRAM | Laptops / ≤8GB GPUs / batch experimentation |
| `ltxv-13b-0.9.8-dev-fp8` | 13B | Quantized dev | Quality on Ada GPUs with Q8 kernels |
| `ltxv-13b-0.9.8-distilled-fp8` | 13B | Quantized distilled | Max speed on RTX 40xx |
| `ltxv-spatial-upscaler-0.9.8` | — | Latent 2× upscaler | Required by all multi-scale configs |
| `LTX-Video-ICLoRA-{depth,pose,canny}-13b-0.9.7` | LoRA (~1GB) | Control adapters | V2V with structural control |

**Key distinction to internalize:**

- **dev** = classic diffusion: needs `guidance_scale ≈ 3–8`, STG, 30+ steps. Slower, max fidelity, more knobs.
- **distilled** = baked-in guidance: `guidance_scale = 1.0`, **fixed timestep list**, 4–10 steps. ~8× fewer steps. This is what makes "real-time" true.

VRAM ballpark: 2B-distilled runs on ~6–8GB; 13B comfortable at 24GB+ (less with FP8/offloading — see [§13](#13-performance)); diffusers with full offloading gets 13B down to **~10GB**.

---

## 4. Installation

**Requirements:** Python ≥ 3.10.5, CUDA ≥ 12.2, PyTorch ≥ 2.1.2 (macOS: MPS with PyTorch 2.3.0 or ≥ 2.6).

### Linux / macOS

```bash
git clone https://github.com/Lightricks/LTX-Video.git
cd LTX-Video
python -m venv env
source env/bin/activate
python -m pip install -e .[inference]
```

### Windows (PowerShell)

```powershell
git clone https://github.com/Lightricks/LTX-Video.git
cd LTX-Video
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install -e ".[inference]"   # quote the extras on PowerShell
```

### Optional: FP8 kernels (RTX 40xx "Ada" GPUs)

Install from [LTXVideo-Q8-Kernels](https://github.com/Lightricks/LTXVideo-Q8-Kernels) to use the `*-fp8` configs — roughly **3× speedup** with minimal quality loss.

Model weights auto-download from Hugging Face on first run (expect tens of GB; the ComfyUI stack recommends 100GB+ free disk).

---

## 5. First Generations (CLI)

`inference.py` is the single entry point. `--pipeline_config` selects the model + sampling recipe. Run `python inference.py --help` for every flag.

### Text-to-video

```bash
python inference.py \
  --prompt "A woman in a red coat walks across a rain-slicked city street at dusk; neon signs reflect in puddles; the camera tracks her from the side in a smooth dolly motion; cinematic, shallow depth of field" \
  --height 704 --width 1216 --num_frames 121 --seed 42 \
  --pipeline_config configs/ltxv-13b-0.9.8-distilled.yaml
```

### Image-to-video (animate a still)

```bash
python inference.py --prompt "PROMPT" \
  --conditioning_media_paths photo.jpg \
  --conditioning_start_frames 0 \
  --height 704 --width 1216 --num_frames 121 --seed 42 \
  --pipeline_config configs/ltxv-13b-0.9.8-distilled.yaml
```

`--conditioning_start_frames 0` pins the image to frame 0 — the video *starts from* your image.

### Video extension (forward or backward)

```bash
python inference.py --prompt "PROMPT" \
  --conditioning_media_paths input.mp4 \
  --conditioning_start_frames 0 \
  --height 704 --width 1216 --num_frames 257 --seed 42 \
  --pipeline_config configs/ltxv-13b-0.9.8-distilled.yaml
```

- Start frame `0` → the clip is the *beginning*, model continues it.
- Start frame `N` near the end → model generates *up to* the clip (backward extension).
- **Constraint:** conditioning video segments must be `8k+1` frames (9, 17, 25…); target start frames must be multiples of 8.

### Multi-keyframe (the killer feature)

Pin different images/clips at different timeline positions and let the model interpolate the story between them:

```bash
python inference.py --prompt "PROMPT" \
  --conditioning_media_paths start.jpg end.jpg \
  --conditioning_start_frames 0 112 \
  --height 704 --width 1216 --num_frames 121 --seed 42 \
  --pipeline_config configs/ltxv-13b-0.9.8-distilled.yaml
```

**Tip:** use visually *similar* keyframes — large divergence between conditions causes abrupt transitions.

### As a Python library

```python
from ltx_video.inference import infer, InferenceConfig

infer(InferenceConfig(
    pipeline_config="configs/ltxv-13b-0.9.8-distilled.yaml",
    prompt="...",
    height=704, width=1216, num_frames=121,
    output_path="output.mp4",
))
```

---

## 6. Pipeline Configs

The YAML files in `configs/` are **the** mastery lever — they encode the entire sampling recipe. Annotated comparison of the two 13B configs:

### `ltxv-13b-0.9.8-distilled.yaml` (your daily driver)

```yaml
pipeline_type: multi-scale                  # two-pass low-res → upscale → refine
checkpoint_path: "ltxv-13b-0.9.8-distilled.safetensors"
downscale_factor: 0.6666666                 # first pass at 2/3 target resolution
spatial_upscaler_model_path: "ltxv-spatial-upscaler-0.9.8.safetensors"
stg_mode: "attention_values"                # SpatioTemporal Guidance variant
decode_timestep: 0.05                       # VAE decodes mid-denoise (timestep-aware VAE)
decode_noise_scale: 0.025
text_encoder_model_name_or_path: "PixArt-alpha/PixArt-XL-2-1024-MS"  # T5-based encoder
precision: "bfloat16"
sampler: "from_checkpoint"
prompt_enhancement_words_threshold: 120     # prompts <120 words get auto-enhanced
prompt_enhancer_image_caption_model_name_or_path: "MiaoshouAI/Florence-2-large-PromptGen-v2.0"
prompt_enhancer_llm_model_name_or_path: "unsloth/Llama-3.2-3B-Instruct"
stochastic_sampling: false

first_pass:                                 # only 7 steps! (distillation)
  timesteps: [1.0000, 0.9937, 0.9875, 0.9812, 0.9750, 0.9094, 0.7250]
  guidance_scale: 1                         # distilled ⇒ CFG baked in
  stg_scale: 0
  rescaling_scale: 1
  skip_block_list: [42]

second_pass:                                # 3 refinement steps at full res
  timesteps: [0.9094, 0.7250, 0.4219]
  guidance_scale: 1
  stg_scale: 0
  rescaling_scale: 1
  skip_block_list: [42]
  tone_map_compression_ratio: 0.6           # 0.9.8 feature: tone mapping (0.6 recommended)
```

### `ltxv-13b-0.9.8-dev.yaml` (quality mode) — what differs

- First pass: **30 steps** with *scheduled* guidance — `guidance_scale` ramps `[1,1,6,8,6,1,1]` across timesteps, `stg_scale` `[0,0,4,4,4,2,1]`, per-stage `skip_block_list`, `cfg_star_rescale: true`.
- Second pass: 30 steps, skipping the first 17 (i.e., ~13 effective refinement steps).

**What this teaches you:** the dev model applies strong guidance only in the *middle* of denoising (where composition forms) and relaxes it at the start/end. If you ever hand-tune, tune there.

**Glossary:**
- **STG (SpatioTemporal Guidance)** — perturbs attention in selected transformer blocks (`skip_block_list`) to boost coherence/detail, like CFG but for motion quality.
- **`decode_timestep`** — the timestep-aware VAE's "last denoise during decode" (set 0.05 for 0.9.1+).
- **`tone_map_compression_ratio`** — 0.9.8 addition that compresses tonal range in refinement; default 0.6.

---

## 7. Prompt Engineering

LTX-Video's text encoder responds to **detailed, chronological, cinematographic prose** — not tag soup. Official guidance:

> Focus on detailed, chronological descriptions of actions and scenes. Include specific movements, appearances, camera angles, and environmental details.

### The structure (aim < 200 words, single paragraph)

1. **Main action** in one opening sentence
2. **Specific movements & gestures**, in chronological order
3. **Appearance** of characters/objects (clothing, colors, distinguishing marks)
4. **Background & environment**
5. **Camera**: angle + movement ("close-up", "camera tracks from behind", "slow dolly out, rotating")
6. **Lighting & color** ("warm sunset glow", "dim streetlights on wet pavement")
7. **Changes/transitions** during the shot
8. Optional style anchor: "captured in real-life footage" / "cinematic"

### A gold-standard example (from the official docs)

> *"A woman walks away from a white Jeep parked on a city street at night, then ascends a staircase and knocks on a door. The woman, wearing a dark jacket and jeans, walks away from the Jeep parked on the left side of the street, her back to the camera; she walks at a steady pace, her arms swinging slightly by her sides; the street is dimly lit, with streetlights casting pools of light on the wet pavement; a man in a dark jacket and jeans walks past the Jeep in the opposite direction; the camera follows the woman from behind as she walks up a set of stairs towards a building with a green door; she reaches the top of the stairs and turns left, continuing to walk towards the building; she reaches the door and knocks on it with her right hand; the camera remains stationary, focused on the doorway; the scene is captured in real-life footage."*

Notice: chronological clauses joined by semicolons, explicit camera notes, concrete visual details, zero abstractions.

### Negative prompt (use it always)

```
worst quality, inconsistent motion, blurry, jittery, distorted
```

Extend with content-specific exclusions, e.g. `bright colors, symbols, graffiti, watermarks` for muted scenes.

### The built-in prompt enhancer

Prompts **under 120 words** (`prompt_enhancement_words_threshold`) are automatically expanded by a local Llama-3.2-3B + Florence-2 captioner (for image conditions). Control it with `enhance_prompt=True/False`. **Master move:** start with the enhancer ON to learn what good prompts look like, then write your own >120-word prompts for full control.

### Practical rules

- Describe **motion explicitly** — a static description yields a near-static video.
- One scene per generation. Don't script multi-shot sequences in one prompt.
- For I2V, describe the image *and* what happens next — consistency between prompt and conditioning image matters.
- Keep a **seed journal**: same seed + same prompt = same video; same seed + edited prompt = controlled variation.

---

## 8. Parameter Reference

| Parameter | Rule / Recommended | Why |
|---|---|---|
| `height`, `width` | **Divisible by 32**; sweet spot ≤ 720×1280 | Trained distribution; VAE constraint |
| `num_frames` | **8n + 1** (9, 17, …, 121, 161, 257); ≤257 typical for quality | Temporal VAE compression |
| FPS (export) | 24–30 (model supports up to 50 in LTX-2) | |
| `seed` | Fix it to reproduce/iterate | Determinism |
| `guidance_scale` | **dev: 3–3.5** (config schedules up to 8 mid-trajectory); **distilled: 1.0 always** | Distilled has CFG baked in |
| Steps | dev: 30–40+ for quality, 20–30 for speed; **distilled: fixed timestep lists (≈7+3)** | Don't add steps to distilled — use its timesteps |
| `decode_timestep` / `decode_noise_scale` | 0.05 / 0.025 (0.9.1+) | Timestep-aware VAE |
| `image_cond_noise_scale` | 0.0–0.025 | Higher = more freedom from conditioning image |
| `guidance_rescale` | 0.7 (diffusers) | Prevents over-saturation |
| `tone_map_compression_ratio` | 0.6 (0.9.8) | Tonal quality |
| Conditioning clips | length 8k+1 frames; start frames multiple of 8 | Latent grid alignment |

**Resolution/length trade triangle:** VRAM and time scale with `height × width × num_frames`. When pushing one axis up, pull another down. 704×1216×121f is a strong default on 24GB.

---

## 9. Diffusers Path

Best when you want LTX-Video **inside a Python app** or on **small GPUs**. Pipelines: `LTXPipeline` (T2V), `LTXImageToVideoPipeline`, `LTXConditionPipeline` (anything-to-video), `LTXLatentUpsamplePipeline`.

### Minimal T2V

```python
import torch
from diffusers import LTXPipeline
from diffusers.utils import export_to_video

pipe = LTXPipeline.from_pretrained("Lightricks/LTX-Video", torch_dtype=torch.bfloat16).to("cuda")
video = pipe(
    prompt=prompt, negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted",
    width=768, height=512, num_frames=161,
    decode_timestep=0.03, decode_noise_scale=0.025, num_inference_steps=50,
).frames[0]
export_to_video(video, "output.mp4", fps=24)
```

### ~10GB VRAM recipe (fp8 layerwise casting + group offloading)

```python
import torch
from diffusers import LTXPipeline, AutoModel
from diffusers.hooks import apply_group_offloading

transformer = AutoModel.from_pretrained("Lightricks/LTX-Video", subfolder="transformer", torch_dtype=torch.bfloat16)
transformer.enable_layerwise_casting(storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.bfloat16)

pipe = LTXPipeline.from_pretrained("Lightricks/LTX-Video", transformer=transformer, torch_dtype=torch.bfloat16)
pipe.transformer.enable_group_offload(onload_device=torch.device("cuda"), offload_device=torch.device("cpu"),
                                      offload_type="leaf_level", use_stream=True)
apply_group_offloading(pipe.text_encoder, onload_device=torch.device("cuda"), offload_type="block_level", num_blocks_per_group=2)
apply_group_offloading(pipe.vae, onload_device=torch.device("cuda"), offload_type="leaf_level")
```

### Full multi-scale with the 0.9.8 distilled model (incl. long video, 361 frames)

The four-stage pattern — **low-res latents → latent 2× upsample → few-step refine → resize**:

```python
import torch
from diffusers import LTXConditionPipeline, LTXLatentUpsamplePipeline
from diffusers.pipelines.ltx.modeling_latent_upsampler import LTXLatentUpsamplerModel
from diffusers.utils import export_to_video

pipe = LTXConditionPipeline.from_pretrained("Lightricks/LTX-Video-0.9.8-13B-distilled", torch_dtype=torch.bfloat16).to("cuda")
upsampler = LTXLatentUpsamplerModel.from_pretrained("a-r-r-o-w/LTX-0.9.8-Latent-Upsampler", torch_dtype=torch.bfloat16)
pipe_up = LTXLatentUpsamplePipeline(vae=pipe.vae, latent_upsampler=upsampler).to(torch.bfloat16).to("cuda")
pipe.vae.enable_tiling()

h, w, frames, ds = 480, 832, 361, 2/3     # 361 frames ≈ 15s — 0.9.8 long-video support
dh, dw = int(h*ds) - int(h*ds) % pipe.vae_spatial_compression_ratio, int(w*ds) - int(w*ds) % pipe.vae_spatial_compression_ratio

latents = pipe(prompt=prompt, negative_prompt=neg, width=dw, height=dh, num_frames=frames,
               timesteps=[1000, 993, 987, 981, 975, 909, 725, 0.03],          # distilled first-pass schedule
               guidance_scale=1.0, guidance_rescale=0.7,
               decode_timestep=0.05, decode_noise_scale=0.025, image_cond_noise_scale=0.0,
               generator=torch.Generator().manual_seed(0), output_type="latent").frames

up = pipe_up(latents=latents, adain_factor=1.0, tone_map_compression_ratio=0.6, output_type="latent").frames

video = pipe(prompt=prompt, negative_prompt=neg, width=dw*2, height=dh*2, num_frames=frames,
             denoise_strength=0.999, timesteps=[1000, 909, 725, 421, 0],      # distilled refine schedule
             latents=up, guidance_scale=1.0, guidance_rescale=0.7,
             decode_timestep=0.05, decode_noise_scale=0.025, image_cond_noise_scale=0.0,
             generator=torch.Generator().manual_seed(0), output_type="pil").frames[0]

video = [f.resize((w, h)) for f in video]
export_to_video(video, "output.mp4", fps=24)
```

Memorize the two distilled timestep lists — they appear everywhere:
- First pass: `[1000, 993, 987, 981, 975, 909, 725, 0.03]`
- Refine: `[1000, 909, 725, 421, 0]`

Extra speed: `pipe.transformer = torch.compile(pipe.transformer, mode="max-autotune", fullgraph=True)` (slow first call, fast after).

---

## 10. ComfyUI Path

For visual, iterative workflow building — and the only first-class home of the newest features (LTX-2, lipdub, HDR).

**Install:** ComfyUI Manager → "Install Custom Nodes" → search **LTXVideo** → Install → restart. Nodes appear under the `LTXVideo` category; models auto-download on first use.

**Example workflows shipped in the repo** (`example_workflows/`):
- T2V / I2V — single-stage (distilled or full) and two-stage with upsampling
- **IC-LoRA**: depth, pose, edge control ([ic-lora.json](https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/ic_lora/ic-lora.json))
- Motion tracking I2V, video-to-video detailing
- LTX-2 extras: **Union IC-LoRA** (one LoRA, multiple controls), **HDR output** (ARRI LogC3 + EXR export), **Lipdub** (multilingual dubbing preserving speaker identity), camera-move LoRAs (dolly, jib)

**Hardware notes (LTX-2 workflows):** 32GB VRAM recommended, 100GB+ disk. On smaller cards: use the **low-VRAM loader nodes** (`low_vram_loaders.py`) and launch ComfyUI with `--reserve-vram`. For LTX-Video 0.9.8 workflows, 12–24GB is workable, especially FP8.

---

## 11. Control Models

Three official **IC-LoRA** (In-Context LoRA) adapters, ~1GB each, give structural control for video-to-video:

| Adapter | Conditioning signal | Use for |
|---|---|---|
| `LTX-Video-ICLoRA-depth-13b-0.9.7` | Depth maps | Re-render scene with same 3D layout |
| `LTX-Video-ICLoRA-pose-13b-0.9.7` | Human pose skeletons | Motion transfer to new characters |
| `LTX-Video-ICLoRA-canny-13b-0.9.7` | Canny edges | Preserve composition/linework |

Workflow: extract the control signal from a source video (depth estimator / pose detector / edge filter) → feed as conditioning alongside your prompt → model regenerates appearance while obeying structure. Easiest via the ComfyUI `ic-lora` workflow; programmatic via `LTXConditionPipeline` or the trainer's inference utilities.

---

## 12. Training

[LTX-Video-Trainer](https://github.com/Lightricks/LTX-Video-Trainer) supports, for both 2B and 13B:

1. **LoRA fine-tuning** — styles & effects (e.g., the "Cakeify" and "Squish" effect LoRAs)
2. **Full fine-tuning** — domain adaptation with big data/compute
3. **IC-LoRA training** — your own control adapters (depth/pose/canny or novel signals)

**Setup (uses `uv`):**

```bash
git clone https://github.com/Lightricks/LTX-Video-Trainer
cd LTX-Video-Trainer
uv sync
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
```

**Two interfaces:**
- **Gradio UI:** `cd scripts && python app_gradio.py` → <http://localhost:7860>. Friendliest start, less configurable.
- **CLI:** prepare dataset → write a YAML config (e.g., `configs/ltxv_13b_lora_cakeify.yaml`) → launch training.

Read these in-repo docs in order: `docs/quick-start.md` → `dataset-preparation.md` → `training-modes.md` → `configuration-reference.md` → `training-guide.md` → `troubleshooting.md` (+ `utility-scripts.md`).

**Effect-LoRA recipe (the classic first project):** collect 10–50 short clips demonstrating one consistent transformation, caption with a trigger phrase, train at modest rank, then load the LoRA at inference with your trigger phrase in the prompt.

---

## 13. Performance

Stack these in order of effort vs. payoff:

| Technique | Gain | How |
|---|---|---|
| Use **distilled** checkpoints | ~8× fewer steps | `ltxv-13b-0.9.8-distilled.yaml` |
| Multi-scale pipeline | Big — most compute at ⅔ res | Default in 0.9.7+ configs |
| **FP8 + Q8 kernels** (RTX 40xx) | ~3× | LTXVideo-Q8-Kernels + `*-fp8` configs |
| **TeaCache** | ~2× | Community caching, plugs into pipeline |
| `torch.compile` (diffusers) | Significant after warmup | `mode="max-autotune", fullgraph=True` |
| Layerwise fp8 casting + group offloading | 13B on ~10GB | Diffusers recipe in §9 |
| `vae.enable_tiling()` | Avoids decode OOM | Always on for high res / long videos |
| 2B model | Smallest footprint | `ltxv-2b-0.9.8-distilled` |
| Lower res/frames first | Linear | Draft at 512×768×97f, finalize bigger |

---

## 14. Troubleshooting

| Symptom | Cause → Fix |
|---|---|
| Washed-out / oversaturated output | Missing rescale → `guidance_rescale=0.7`; on 0.9.8 keep `tone_map_compression_ratio=0.6` |
| Distilled output is mush | You changed steps/CFG → use `guidance_scale=1.0` and the **exact** distilled timestep lists |
| Near-static video | Prompt has no motion verbs → describe movement chronologically, raise motion detail |
| Jittery/morphing motion | Use the standard negative prompt; try dev model; resolution within sweet spot |
| Crash on `num_frames` / size | Violated 8n+1 frames or ÷32 resolution rule |
| Abrupt jump between keyframes | Conditioning images too dissimilar → use closer keyframes or more of them |
| OOM at decode | `vae.enable_tiling()` |
| OOM at denoise | FP8 casting + group offloading (§9), or 2B model, or lower res |
| I2V ignores image details | Prompt contradicts the image → describe the image faithfully, then the action; lower `image_cond_noise_scale` |
| Conditioning video rejected | Clip length must be 8k+1 frames; start frame multiple of 8 |

---

## 15. Roadmap

**Week 1 — Operator.** Try LTX-Studio/Fal.ai online to calibrate expectations. Install locally, run T2V/I2V with `ltxv-13b-0.9.8-distilled.yaml` (or 2B if VRAM-bound). Learn the prompt structure (§7); 20+ generations; keep a seed/prompt journal.

**Week 2 — Power user.** Multi-keyframe conditioning and both directions of video extension. Read both config YAMLs until every key makes sense (§6). Compare dev vs distilled on identical seeds. Tune the §8 parameters deliberately.

**Week 3 — Integrator.** Pick a path: **diffusers** (build the 4-stage multi-scale script, then the 10GB recipe, then a 361-frame long video) or **ComfyUI** (run every example workflow; try IC-LoRA depth/pose/canny on real footage).

**Week 4 — Creator.** Train an Effect LoRA with LTX-Video-Trainer (Gradio first, then CLI configs). Apply the full performance stack (§13). Optional: step up to LTX-2 in ComfyUI for audio+video. Join the [Discord](https://discord.gg/ltxplatform) and study the paper.

**You've mastered it when you can:** predict output quality from a prompt before generating; explain why distilled needs exactly those timesteps; debug any artifact to a parameter; and ship a custom LoRA.

---

## 16. Resources

- **Repo:** <https://github.com/Lightricks/LTX-Video> · **Docs:** <https://docs.ltx.video> · **Paper:** <https://arxiv.org/abs/2501.00103>
- **Weights:** <https://huggingface.co/Lightricks> · **Diffusers API:** <https://huggingface.co/docs/diffusers/main/en/api/pipelines/ltx_video>
- **ComfyUI nodes:** <https://github.com/Lightricks/ComfyUI-LTXVideo> · **Trainer:** <https://github.com/Lightricks/LTX-Video-Trainer>
- **Q8 kernels:** <https://github.com/Lightricks/LTXVideo-Q8-Kernels> · **Community:** ComfyUI-LTXTricks, TeaCache, LTX-VideoQ8
- **Online:** LTX-Studio, Fal.ai, Replicate · **Discord:** <https://discord.gg/ltxplatform>
