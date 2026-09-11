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
  - **U2-Net** *(Default)*: Fast and balanced (~1–2s on laptop CPU).
  - **IS-Net (DIS5K)**: High-accuracy dichotomous image segmentation for complex and camouflaged subjects.
  - **Silueta**: Ultra-lightweight model (~40MB) for near-instant cutouts.
  - **BRIA RMBG 2.0**: State-of-the-art bilateral transformer segmentation.
- **🎯 Dual-Pass Saliency Fusion (Camouflage Master):**
  - Eliminates false interior cutouts (e.g. white meat on white background, white shirts, specular highlights) by calculating the mathematical union of color and structural luminance saliency passes.
- **🪄 Anti-Aliased Sub-Pixel Defringing:**
  - Removes dark color bleeding and shadow halos without destroying edge anti-aliasing or causing stair-stepped jaggedness.
- **🔍 Interactive Comparison & Live Backdrops:**
  - Split Before/After comparison slider.
  - Side-by-Side and Cutout Only view modes.
  - Live preview swatches: Dark Checkerboard, Light Checkerboard, Solid Black, Solid White, and Green Screen.
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
└── README.md              # Project documentation
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
