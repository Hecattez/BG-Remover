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
- **Key Libraries:** `rembg` (v2.0.84), `onnxruntime` (v1.30.0), `Pillow`, `scipy`, `numpy`.
- **Downloaded Local Models (`C:\Users\Windows\.rembg\models\`):**
  - `u2net.onnx` (~176MB, default balanced model)
  - `isnet-general-use.onnx` (~179MB, DIS5K high-accuracy model)
  - `silueta.onnx` (~44MB, ultra-fast model)
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
   - Union: `np.maximum(color_mask, gray_mask)` naturally retains the entire subject at full opacity without crude hole-patching.

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
└── CONTEXT.md             # This context file for future sessions
```
