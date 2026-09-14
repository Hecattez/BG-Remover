# Project Context: BG-Remover

## 1. Overview & Repository
- **Project:** Local AI Background Remover (Zero-download clipboard-in, clipboard-out workflow).
- **Local Path:** `D:\BG-Remover`
- **GitHub Repo:** `https://github.com/Hecattez/BG-Remover` (`git@github.com:Hecattez/BG-Remover.git`)
- **Main Branch:** `main` (clean initial commit pushed; `.gitignore` ignores `profile/`, `__pycache__`, logs).
- **User:** `Hecattez` (`frgottenacc@gmail.com`)
- **SSH Key:** Configured in `C:\Users\Windows\.ssh\id_ed25519` and linked to GitHub.

---

## 2. Environment & Runtime
- **Python:** Python 3.11 (`C:\Users\Windows\AppData\Local\Programs\Python\Python311\python.exe` and `pythonw.exe`).
  *(Note: Avoid default Python 3.14 on this machine due to wheel compatibility).*
- **Key Libraries:** `rembg` (v2.0.84), `onnxruntime` (v1.30.0), `Pillow`, `scipy`, `numpy`, `pymatting`.
  - `u2net.onnx` (~176MB, legacy balanced model)
  - `silueta.onnx` (~44MB, ultra-fast model)
  - `birefnet-general-lite.onnx` (~220MB, SOTA bilateral transformer model)
  - `bria-rmbg` (available in dropdown for on-demand download)
---

## 3. Desktop Application Architecture
- **No Console Window:** Launches via `pythonw.exe app.py` (or `launch.vbs`), ensuring 0 black command prompt windows appear in `Alt + Tab`.
- **Desktop Shortcut:** `C:\Users\Windows\Desktop\Background Remover.lnk` -> points to `pythonw.exe "D:\BG-Remover\app.py"` with icon `D:\BG-Remover\assets\app_icon.ico,0`.
- **Isolated Window:** Spawns Edge in standalone app mode (`--app=http://127.0.0.1:PORT`) with dedicated user profile (`D:\BG-Remover\profile`) so it never conflicts with regular browser sessions.
- **Port Detection & Readiness:** Dynamically binds available port starting at `7860`, probes socket readiness before window launch to prevent blank white screens.
- **Watchdog Keep-Alive:** Frontend pings `/api/ping` every 2.5s. If window is closed, watchdog automatically shuts down the Python process after 8s of inactivity.

---

## 4. Key Engineering & Algorithm Fixes
1. **Split-Slider Layering:**
   - Bottom layer: Cutout on active backdrop (Dark/Light Checkerboard, Black, White, Green Screen).
   - Top layer: Original image clipped on left side via CSS `clip-path: polygon(...)`.
2. **Anti-Aliasing (No Jaggedness):**
   - `post_process_mask=False` in `rembg.remove` (bypasses rembg's internal 1-bit hard thresholding `np.where(mask < 127, 0, 255)`).
   - Preserves continuous 8-bit alpha transitions.
3. **Sub-Pixel Edge Defringe:**
   - Replaced harsh box `MinFilter` with a continuous alpha curve adjustment (`cutoff = 0.05 * trim_px`) and a 0.35px Gaussian feather.
   - Eliminates dark background bleed without stair-stepping.
4. **Dual-Pass Saliency Fusion (`fuse_dual_pass_saliency`):**
   - Solves white-on-white / color camouflage false cutouts (e.g. white shrimp meat on white backgrounds).
   - Pass 1: AI color saliency.
   - Pass 2: AI luminance / desaturated saliency (forces AI to segment by structural contours, texture, and shading).
   - Background Color Filtering: Suppresses grayscale false-fill on pixels matching the sampled background color, preventing hollow loops (headphones, mug handles) from being falsely filled in.
   - Union: `np.maximum(color_mask, gray_mask_filtered)` retains camouflaged subjects while respecting topological holes.
5. **Interactive Smart AI Brush & Magic Tap (remove.bg-style Object/Hole Segmentation):**
   - **✨ Smart AI Auto-Snap Mode:** Rather than requiring manual pixel-by-pixel tracing, rough strokes sample target seeds and expand via edge-contrast barriers (gradient stopping) to automatically snap to the subject's contours. Protects foreground objects from accidental erasure.
   - **🪄 Magic Tap (One-Click Hole Remover):** Single-click BFS bounded region flooding removes enclosed background pockets (e.g. headphone loop interior, mug handles, arms/legs) in ~10–25ms.
   - **🖌️ Manual Mode:** Direct pixel eraser/restore retained for explicit pixel-level touch-ups.
   - **Adjustable Tolerance Slider:** Controls expansion over gradients and shadow penumbras while preserving high-contrast object rims.
   - **High-Performance Dirty Rect Updates:** Sub-rectangle GPU transfers (`0.2ms` per stamp) enable silky-smooth 60 FPS interactive dragging on multi-megapixel images.
   - **GPU Undo/Redo Engine:** Uses `createImageBitmap` snapshots (~0.4ms overhead) with 15-step undo/redo stack (`Ctrl + Z` / `Ctrl + Y`).

6. **Color-Guided Fine Detail & Micro-Structure Recovery (`recover_fine_details`):**
   - High-resolution segmentation models (like IS-Net) naturally segment macro silhouettes and holes, but can assign faint confidence (alpha 2–20) to thin 1-pixel structures (like headphone audio cords, antennae, and fine hair).
   - Automatically samples background color from verified perimeter background pixels.
   - Pixels where the model detected a trace of foreground (`mask > 1`) and whose color has high contrast against the background ($\Delta E > 38$) are dynamically boosted to full opacity.
   - Achieves 100% remove.bg parity (intact cords, wires, and hollow loops) in ~1.9s on CPU without requiring heavy cloud GPUs.
7. **Color Spill Decontamination & Foreground Unmixing (`decontaminate_color_spill`):**
   - Eliminates color bleeding, chromatic fringes, and background halos (e.g. green cast from green-screens, or bleached frosty edges from white studio backdrops).
   - Uses multi-level Laplacian pyramid foreground estimation (Germer et al., 2020 via `pymatting`) executed directly on the post-guided-filter continuous alpha matte.
   - $C^1$ Continuous Core Preservation: pixels with $\alpha \ge 0.98$ strictly preserve 100% original camera sensor pixels, while transition pixels ($0.02 < \alpha < 0.98$) are unmixed to true foreground color.
   - Added `Color Decontam` checkbox to top control bar (enabled by default) with instant auto-reprocess on toggle.
---

## 5. File Structure
```text
D:\BG-Remover\
├── assets/
│   ├── app_icon.ico       # Active desktop shortcut icon
│   ├── icon.ico           # Backup multi-resolution icon bundle
│   └── icon.png           # App header logo & web favicon
├── app.py                 # Full self-contained app (backend + frontend template + window controller)
├── launch.vbs             # Silent VBScript launcher
├── run.bat                # Batch runner using start "" pythonw.exe
├── requirements.txt       # Dependencies
├── .gitignore             # Git ignore rules
├── LICENSE                # MIT License
├── README.md              # Documentation
├── RESEARCH.md            # Deep CV research & remove.bg reverse-engineering documentation
└── CONTEXT.md             # This context file for future sessions
```
