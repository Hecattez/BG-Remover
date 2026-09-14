# Project Context: BG-Remover

## 1. Overview & Repository
- **Project:** Local AI Background Remover (Zero-download clipboard-in, clipboard-out workflow).
- **Local Path:** `D:\BG-Remover`
- **GitHub Repo:** `https://github.com/Hecattez/BG-Remover` (`git@github.com:Hecattez/BG-Remover.git`)
- **Main Branch:** `main`
- **User:** `Hecattez` (`frgottenacc@gmail.com`)
- **SSH Key:** Configured in `C:\Users\Windows\.ssh\id_ed25519` and verified with GitHub.

---

## 2. Workstation & Runtime Specifications
- **Operating System:** Windows 10 Pro (x64, Build 19045)
- **CPU:** Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz (4 Cores, 8 Threads)
- **GPU:** Intel(R) UHD Graphics 620 (DirectX 12 feature level 12_1)
- **RAM:** 8 GB
- **Python Environment:** Python 3.11 (`C:\Users\Windows\AppData\Local\Programs\Python\Python311\python.exe` and `pythonw.exe`).
  *(Critical: Avoid default Python 3.14 on this machine due to ONNX/scipy C-extension binary wheel incompatibility).*
- **Key Installed Dependencies:**
  - `onnxruntime-directml==1.24.4` (Hardware-accelerates neural inference on Intel UHD 620 via Microsoft DirectX 12 DML; zero background/idle consumption).
  - `rembg==2.0.84`
  - `Pillow>=10.0.0`
  - `scipy>=1.12.0`
  - `numpy>=1.26.0`
  - `pymatting==1.1.16` (Provides multi-level Laplacian foreground decontamination and Levin closed-form alpha matting).
- **Local Model Weights (`C:\Users\Windows\.rembg\models\`):**
  - `isnet-general-use\isnet-general-use.onnx` (~179MB, native $1024\text{px}$ DIS5K dichotomous segmentation — **Default Auto-Pilot Engine**).
  - `u2net\u2net.onnx` (~176MB, legacy balanced model).
  - `silueta\silueta.onnx` (~44MB, ultra-fast model).
  - `birefnet-general-lite\birefnet-general-lite.onnx` (~220MB, bilateral reference transformer).
  - `u2net_human_seg\u2net_human_seg.onnx` (~176MB, human portrait segmentation model).

---

## 3. Desktop Application Architecture & UX Design
- **Zero-Friction "Auto-Pilot" Experience:**
  - The top header is completely decluttered of technical engineering knobs (model pickers, defringe dropdowns, matting thresholds).
  - A user simply presses `Ctrl + V` or drops an image; the app executes the optimal GPU-accelerated pipeline under the hood.
  - Header layout: Brand Logo + **BG Remover** + `⚡ GPU Accelerated` badge on the left, and a single **Auto-copy result** checkbox toggle on the right.
- **Preserved Interactive View Toolbar:**
  - Positioned directly above the canvas stage:
    `View: [Split Slider] [Side-by-Side] [Cutout Only] [🖌️ Refine Brush]`
    `Backdrop: [Dark Checker] [Light Checker] [Solid Black] [Solid White] [Green Screen]`
- **Headless Desktop Window Launch:**
  - Launches via `pythonw.exe app.py` (or `launch.vbs`), ensuring 0 black command prompt windows appear in `Alt + Tab`.
  - Spawns Edge in standalone app mode (`--app=http://127.0.0.1:PORT`) with an isolated profile in `D:\BG-Remover\profile` to avoid conflicts with personal browser tabs.
  - Dynamic port binding starting at `7860`, with socket readiness probing before window spawn.
  - Watchdog keep-alive terminates the Python process after 60s of complete idle silence to free all system RAM and GPU resources.

---

## 4. End-to-End Image Processing Pipeline (`app.py`)
Every pasted or uploaded image is processed through a cascaded 9-stage computer vision pipeline:

1. **Macro Saliency Inference (DirectML GPU):**
   - High-resolution $1024 \times 1024$ dichotomous segmentation via `isnet-general-use.onnx`.
   - Executed on Intel UHD 620 GPU via DirectX 12 (`DmlExecutionProvider`), taking $\sim 1.62\text{s}$ steady-state without CPU thermal throttling.
2. **Spatially-Varying Local Background Field (`compute_local_background_field`):**
   - Vectorized $O(N)$ Euclidean Distance Transform (EDT) nearest-neighbor propagation ($\sim 100\text{ms}$).
   - Maps every pixel to the RGB color of its closest confirmed background pixel, accurately modeling studio lighting gradients, vignettes, and shadows.
3. **Local Cavity & Webbing Suppression (`suppress_background_webbing`):**
   - Compares ambiguous non-solid pixels against the local background field.
   - Pockets showing through cords, spokes, or hair curls matching local backdrop ($\Delta E < 26$) are suppressed to transparent.
4. **Selective Fine Detail & Cord Recovery (`recover_fine_details`):**
   - Protects solid boundaries (`mask >= 180` dilated by 4px).
   - Dynamically boosts isolated thin structures (headphone cords, wires, hair strands) having high contrast against local background ($\Delta E > 38$).
5. **Distance-Aware Orphan Island Pruning (`clean_orphan_islands_distance`):**
   - Connected component analysis with Euclidean distance transform from primary subject.
   - Small noise components ($< 3\%$ of subject) located $> 30\text{px}$ away from the subject in empty background are purged.
6. **Sub-Pixel Optical Anti-Aliasing (`fast_guided_filter`):**
   - Fast $O(1)$ Guided Filter (He et al., IEEE TPAMI) using photographic luminance as guidance.
   - Converts quantized step-transitions into smooth sub-pixel continuous optical gradients in $\sim 15\text{ms}$.
7. **Continuous Edge Defringing:**
   - Smooth continuous power-curve defringe without harsh 1-bit box-filter staircase jaggedness.
8. **Color Spill Decontamination (`decontaminate_color_spill`):**
   - Multi-level Laplacian pyramid foreground estimation (Germer et al., IEEE TPAMI 2020 via `pymatting`).
   - Unmixes and cancels background color bleeding and reflections from semi-transparent boundaries ($0.02 < \alpha < 0.98$).
   - $C^1$ continuous core preservation: pixels with $\alpha \ge 0.98$ retain $100\%$ untouched camera sensor pixels.
9. **Alpha Premultiplication:**
   - Zeroes out RGB values where alpha is 0, outputting a clean transparent RGBA PNG.

---

## 5. Interactive Studio: Smart AI Brush & Magic Tap
For complex images with touching environmental clutter (e.g. sunscreen bottle on beach with miniature people):
- **🪄 Magic Tap (`M` key):** Single-click BFS flood fill bounded by local gradient barriers. Tapping touching scene clutter with high contrast ($\Delta E > 230$) erases it cleanly up to the product boundary in $\sim 15\text{ms}$.
- **✨ Smart AI Brush (`S` key):** Auto-snapping brush that expands inside the brush circle but halts sharply at high-contrast subject edges.
- **GPU Undo/Redo Engine:** `createImageBitmap` snapshots (~0.4ms overhead) with 15-step undo/redo stack (`Ctrl + Z` / `Ctrl + Y`).

---

## 6. Literature & Architectural Research Summary (`RESEARCH.md`)
The `RESEARCH.md` document is structured into 3 distinct sections:
- **Part 1 (Chronological Log):** Append-only engineering log tracking daily findings, failures, and mathematical solutions from 2026-09-11 to 2026-09-14.
- **Part 2 (Thematic Synthesis):**
  - Synthesizes academic references:
    - *Semantic Soft Segmentation (Aksoy, Paris et al., SIGGRAPH 2018 / Adobe)*: Fusing deep CNN semantic feature vectors with Matting Laplacian affinities.
    - *Closed-Form Natural Image Matting (Levin et al., IEEE TPAMI 2008)*: Solving the Matting Laplacian over adaptive trimaps.
    - *greenScreen.AI Lessons (Shperber, Towards Data Science 2017)*: Handheld objects, dataset coarse-polygon limitations, and why CRFs fail.
  - Documents the 7 Major Failure Modes Identified & Solved.
- **Part 3 (Conclusions So Far):** The Two-Stage Paradigm, Local over Global fields, and Consumer Appliance UX.

---

## 7. Next Milestones on the Roadmap
1. **Quantized E-Commerce Packshot Model (RMBG-1.4 INT8):**
   - Integrate an 85MB INT8 quantized packshot model trained specifically on commercial product catalogs to automatically reject touching beach sand and props.
2. **Clipboard Auto-Watch (Ghost Mode):**
   - Background worker thread monitoring Windows clipboard (`ImageGrab`) to remove backgrounds silently and overwrite the clipboard with transparent PNGs without opening the window.
3. **Auto-Crop to Subject:**
   - Automatic bounding-box trimming (`Image.getbbox()`) with configurable padding to eliminate excessive transparent margins.

---

## 8. Development Commands & Hygiene
- **Run App:** `"C:\Users\Windows\AppData\Local\Programs\Python\Python311\pythonw.exe" app.py` (or double-click `launch.vbs`).
- **Syntax Check:** `"C:\Users\Windows\AppData\Local\Programs\Python\Python311\python.exe" -m py_compile app.py`
- **Dependencies:** `requirements.txt` (`onnxruntime-directml`, `rembg`, `Pillow`, `scipy`, `numpy`, `pymatting`).
- **GitHub Commits:** Every milestone MUST be committed and pushed immediately to `git@github.com:Hecattez/BG-Remover.git` on branch `main`.
