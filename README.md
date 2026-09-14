# Local AI Background Remover ✂️

A fast, private, 100% offline background removal desktop application tailored for an instant clipboard-to-clipboard workflow. No uploads, no subscriptions, and zero file downloading required.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-brightgreen.svg)

---

## ✨ Features

- **⚡ Zero-Download Clipboard Workflow:**
  - Copy an image anywhere (`Ctrl + C` or screenshot with `Win + Shift + S`).
  - Press `Ctrl + V` in the app to process.
  - The transparent cutout is automatically written back to your clipboard—ready to paste directly into Photoshop, Figma, Discord, or PowerPoint.
- **🧠 Multiple AI Backends (Offline & Local):**
  - **IS-Net (DIS5K)** *(Default & Recommended)*: High-accuracy 1024px dichotomous segmentation with automatic hole and silhouette detection (~1.9s on CPU).
  - **BiRefNet Lite**: State-of-the-art bilateral reference transformer for maximum precision and micro-details.
  - **U2-Net**: Legacy balanced model (~170MB).
  - **Silueta**: Ultra-lightweight model (~40MB) for near-instant cutouts.
  - **BRIA RMBG 2.0**: High-capacity deep learning model (~1GB).
- **🎯 Dual-Pass Saliency Fusion (Camouflage Master):**
  - Eliminates false interior cutouts (e.g. white meat on white background, white shirts, specular highlights) by calculating the mathematical union of color and structural luminance saliency passes.
- **🔬 Color-Guided Fine Detail & Cord Recovery:**
  - Automatically restores thin audio cords, fine wires, and hair strands without wiping them out during defringing, achieving remove.bg parity in ~1.9s on CPU.
- **🪄 Anti-Aliased Sub-Pixel Defringing:**
  - Removes dark color bleeding and shadow halos without destroying edge anti-aliasing or causing stair-stepped jaggedness.
- **🔍 Interactive Comparison & Live Backdrops:**
  - Split Before/After comparison slider.
  - Side-by-Side and Cutout Only view modes.
  - Live preview swatches: Dark Checkerboard, Light Checkerboard, Solid Black, Solid White, and Green Screen.
- **🖌️ Interactive Refine Brush & Magic Tap (remove.bg-style Smart AI):**
  - **✨ Smart AI Mode (Auto-Snap):** Roughly mark or swipe over an area; the algorithm automatically detects subject boundaries and removes/restores the target region while protecting the subject's edges.
  - **🪄 Magic Tap (One-Click Hole Remover):** Click once inside any enclosed hole or background pocket (e.g. inside headphone loops, mug handles, arms/legs) to erase the entire pocket instantly.
  - **🖌️ Manual Mode:** Direct pixel eraser/restore for exact pixel-by-pixel touch-ups.
  - **Adjustable Controls:** Tolerance slider for gradient/shadow expansion, brush radius slider, softness feathering, zoom & pan controls, and instant GPU undo/redo (`Ctrl + Z` / `Ctrl + Y`).
- **🖥️ Standalone Desktop Window:**
  - Runs in a clean, isolated application window with zero terminal windows cluttering `Alt + Tab`.
  - Automatic watchdog keep-alive: cleanly exits when the window closes to free system resources.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or 3.11 installed on Windows.
- Microsoft Edge or Google Chrome (for the standalone UI window).

### Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:Hecattez/BG-Remover.git
   cd BG-Remover
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   - Run `python app.py` (or double-click `run.bat` / `launch.vbs`).

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **`Ctrl + V`** | Paste image from clipboard and start removal |
| **`Ctrl + C`** | Copy transparent PNG result to clipboard |
| **`Ctrl + S`** | Save cutout as PNG file |
| **`Ctrl + R`** | Reload application |
| **`E` or `1`** | Switch to Erase Brush *(when in Refine Brush mode)* |
| **`R` or `2`** | Switch to Restore Brush *(when in Refine Brush mode)* |
| **`M` or `3`** | Switch to Magic Tap *(1-click hole/pocket eraser)* |
| **`S`** | Toggle Smart AI mode vs Manual pixel mode |
| **`[` / `]`** | Decrease / Increase brush size |
| **`Ctrl + Z` / `Ctrl + Y`** | Undo / Redo brush strokes |
| **`Space + Drag`** | Pan image canvas when zoomed in |
| **`Escape`** | Exit Refine Brush mode |

---

## 📁 Project Structure

```text
D:\BG-Remover\
├── assets/
│   ├── app_icon.ico       # Multi-resolution Windows application icon
│   ├── icon.ico           # Application icon bundle
│   └── icon.png           # High-resolution PNG logo & favicon
├── app.py                 # Core application backend & desktop window launcher
├── launch.vbs             # Completely silent launcher (no console window)
├── run.bat                # Batch file launcher
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore rules
├── LICENSE                # MIT License
├── README.md              # Project documentation
├── RESEARCH.md            # Deep CV research & remove.bg reverse-engineering documentation
└── CONTEXT.md             # Project architecture & engineering context
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
