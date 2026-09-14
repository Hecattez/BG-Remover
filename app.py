import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from rembg import new_session, remove

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_DIR, "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "app_icon.ico")
if not os.path.exists(ICON_ICO):
    ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PNG = os.path.join(ASSETS_DIR, "icon.png")

# Track activity to shut down server when window closes
last_activity_time = time.time()
has_received_first_request = False

# Model configurations
AVAILABLE_MODELS = {
    "u2net": {
        "label": "U2-Net (Balanced & Fast - Recommended)",
        "default": True,
        "description": "Standard balanced model (~170MB). Fast on laptop CPU."
    },
    "silueta": {
        "label": "Silueta (Ultra Fast / Instant)",
        "default": False,
        "description": "Lightweight model (~40MB). Instant processing on CPU."
    },
    "bria-rmbg": {
        "label": "BRIA RMBG 2.0 (Max Quality / Hair & Details)",
        "default": False,
        "description": "State-of-the-art background removal model (~1GB). Downloads on first selection."
    },
    "isnet-general-use": {
        "label": "IS-Net (High Accuracy / DIS5K)",
        "default": False,
        "description": "High-accuracy dichotomous image segmentation model. Pre-downloaded and ready."
    }
}

# Cache sessions in memory
sessions = {}

def get_session(model_name: str):
    if model_name not in AVAILABLE_MODELS:
        model_name = "u2net"
    if model_name not in sessions:
        t0 = time.time()
        sessions[model_name] = new_session(model_name)
    return sessions[model_name]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BG Remover - Clipboard Assistant</title>
<link rel="icon" type="image/png" href="/assets/icon.png">
<style>
  :root {
    --bg: #0f1115;
    --surface: #181a20;
    --surface-hover: #22252e;
    --border: #2b2f3a;
    --border-accent: #3b82f6;
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --success: #10b981;
    --text: #f3f4f6;
    --text-muted: #9ca3af;
    --text-subtle: #6b7280;
    --accent-glow: rgba(37, 99, 235, 0.25);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

  body {
    background-color: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
  }

  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 10px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .brand img.app-logo {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
  }

  .brand-title {
    font-size: 1.05rem;
    font-weight: 600;
  }

  .brand-tag {
    font-size: 0.72rem;
    background: #272c38;
    color: #93c5fd;
    padding: 2px 8px;
    border-radius: 12px;
    margin-left: 6px;
  }

  .top-controls {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .model-select-group {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  select {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.85rem;
    outline: none;
    cursor: pointer;
  }
  select:focus { border-color: var(--border-accent); }

  .auto-copy-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    color: var(--text-muted);
    cursor: pointer;
  }

  .auto-copy-toggle input {
    accent-color: var(--primary);
    cursor: pointer;
  }

  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 16px 20px;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    gap: 12px;
  }

  .drop-box {
    background: var(--surface);
    border: 2px dashed var(--border);
    border-radius: 14px;
    padding: 24px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
  }
  .drop-box:hover, .drop-box.dragover {
    border-color: var(--border-accent);
    background: var(--surface-hover);
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.08);
  }

  .drop-box h2 {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .drop-box p {
    color: var(--text-muted);
    font-size: 0.88rem;
  }

  kbd {
    background: #282c37;
    border: 1px solid #3d4353;
    color: #e5e7eb;
    padding: 3px 7px;
    border-radius: 5px;
    font-size: 0.82rem;
    font-family: inherit;
    box-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }

  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.85rem;
    color: var(--text-muted);
    min-height: 22px;
    padding: 0 4px;
  }

  .status-msg {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.2);
    border-top-color: #60a5fa;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: none;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .toast {
    color: #34d399;
    font-weight: 500;
    animation: fadeIn 0.3s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: translateY(0); } }

  /* Workspace */
  .workspace {
    display: none;
    flex-direction: column;
    gap: 12px;
    flex: 1;
  }

  .view-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--surface);
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
  }

  .toolbar-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn-group {
    display: inline-flex;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2px;
  }

  .btn-group button {
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 5px 12px;
    font-size: 0.8rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .btn-group button.active {
    background: #2b303d;
    color: var(--text);
    font-weight: 500;
  }

  /* Brush Toolbar & Tool Styles */
  .brush-toolbar {
    display: none;
    align-items: center;
    justify-content: space-between;
    background: #181a22;
    padding: 8px 14px;
    border-radius: 8px;
    border: 1px solid #3b82f6;
    box-shadow: 0 2px 12px rgba(59, 130, 246, 0.15);
    flex-wrap: wrap;
    gap: 10px;
    animation: fadeIn 0.2s ease;
  }

  .brush-controls-left {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }

  .brush-controls-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .brush-btn-group {
    display: inline-flex;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2px;
  }

  .brush-tool-btn {
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 5px 12px;
    font-size: 0.82rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-weight: 500;
  }
  .brush-tool-btn:hover { color: var(--text); }

  .brush-tool-btn.active-erase {
    background: #dc2626 !important;
    color: #ffffff !important;
    box-shadow: 0 1px 6px rgba(220, 38, 38, 0.4);
  }

  .brush-tool-btn.active-restore {
    background: #059669 !important;
    color: #ffffff !important;
    box-shadow: 0 1px 6px rgba(5, 150, 105, 0.4);
  }

  .brush-tool-btn.active-smart {
    background: #2563eb !important;
    color: #ffffff !important;
    box-shadow: 0 1px 6px rgba(37, 99, 235, 0.4);
  }

  .brush-tool-btn.active-magic-tap {
    background: #8b5cf6 !important;
    color: #ffffff !important;
    box-shadow: 0 1px 6px rgba(139, 92, 246, 0.4);
  }

  .brush-param-group {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .brush-param-group input[type="range"] {
    width: 80px;
    accent-color: var(--primary);
    cursor: pointer;
  }

  .brush-badge {
    background: #252834;
    color: #e5e7eb;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.76rem;
    font-family: inherit;
    font-weight: 600;
    min-width: 42px;
    text-align: center;
    border: 1px solid #374151;
  }

  .brush-stage {
    display: none;
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
    align-items: center;
    justify-content: center;
    touch-action: none;
    user-select: none;
  }

  .brush-canvas-wrapper {
    position: relative;
    display: inline-block;
    transform-origin: center center;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.6);
    line-height: 0;
    cursor: crosshair;
    border-radius: 4px;
    overflow: hidden;
  }

  #brushCanvas {
    display: block;
    pointer-events: auto;
  }

  .brush-cursor {
    position: absolute;
    pointer-events: none;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    display: none;
    z-index: 100;
    box-sizing: border-box;
  }

  .brush-cursor.mode-erase {
    border: 2px solid #ef4444;
    background: rgba(239, 68, 68, 0.18);
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.5);
  }

  .brush-cursor.mode-restore {
    border: 2px solid #10b981;
    background: rgba(16, 185, 129, 0.18);
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.5);
  }

  .brush-cursor.mode-magic-tap {
    border: 2px solid #a855f7;
    background: rgba(168, 85, 247, 0.25);
    box-shadow: 0 0 8px rgba(168, 85, 247, 0.6);
  }

  .bg-swatches {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .swatch {
    width: 22px;
    height: 22px;
    border-radius: 4px;
    border: 1px solid #4b5563;
    cursor: pointer;
    position: relative;
    transition: transform 0.15s;
  }
  .swatch:hover { transform: scale(1.1); }
  .swatch.active {
    border-color: #60a5fa;
    box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.4);
  }

  .swatch-check-dark {
    background-color: #14151a;
    background-image: linear-gradient(45deg, #252833 25%, transparent 25%), linear-gradient(-45deg, #252833 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #252833 75%), linear-gradient(-45deg, transparent 75%, #252833 75%);
    background-size: 8px 8px;
  }
  .swatch-check-light {
    background-color: #ffffff;
    background-image: linear-gradient(45deg, #cbd5e1 25%, transparent 25%), linear-gradient(-45deg, #cbd5e1 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #cbd5e1 75%), linear-gradient(-45deg, transparent 75%, #cbd5e1 75%);
    background-size: 8px 8px;
  }
  .swatch-black { background: #000000; }
  .swatch-white { background: #ffffff; }
  .swatch-green { background: #00e676; }

  /* High-specificity Backdrop definitions for canvas & cutout */
  .backdrop-check-dark {
    background-color: #121318 !important;
    background-image:
      linear-gradient(45deg, #222634 25%, transparent 25%),
      linear-gradient(-45deg, #222634 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #222634 75%),
      linear-gradient(-45deg, transparent 75%, #222634 75%) !important;
    background-size: 16px 16px !important;
    background-position: 0 0, 0 8px, 8px -8px, -8px 0px !important;
  }
  .backdrop-check-light {
    background-color: #ffffff !important;
    background-image:
      linear-gradient(45deg, #e2e8f0 25%, transparent 25%),
      linear-gradient(-45deg, #e2e8f0 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, #e2e8f0 75%),
      linear-gradient(-45deg, transparent 75%, #e2e8f0 75%) !important;
    background-size: 16px 16px !important;
    background-position: 0 0, 0 8px, 8px -8px, -8px 0px !important;
  }
  .backdrop-black { background: #000000 !important; background-image: none !important; }
  .backdrop-white { background: #ffffff !important; background-image: none !important; }
  .backdrop-green { background: #00e676 !important; background-image: none !important; }

  /* Image Display Container */
  .preview-stage {
    background: #111317;
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    height: min(520px, calc(100vh - 280px));
    min-height: 380px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Compare Slider Mode */
  .slider-container {
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
    user-select: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Layer 1: Cutout layer sitting on backdrop */
  .slider-cutout-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Layer 2: Original image layer clipped by slider */
  .slider-original-clip {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    pointer-events: none;
    z-index: 2;
  }

  .slider-img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    pointer-events: none;
  }

  .badge-label {
    position: absolute;
    bottom: 12px;
    padding: 4px 10px;
    border-radius: 5px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: rgba(0, 0, 0, 0.7);
    color: #ffffff;
    pointer-events: none;
    z-index: 5;
    backdrop-filter: blur(4px);
    border: 1px solid rgba(255, 255, 255, 0.18);
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
  }
  .badge-before { left: 12px; }
  .badge-after { right: 12px; }

  .slider-handle {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 3px;
    background: #ffffff;
    cursor: ew-resize;
    box-shadow: 0 0 10px rgba(0,0,0,0.6);
    z-index: 10;
  }

  .slider-button {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #1f2937;
    font-size: 13px;
    font-weight: bold;
    pointer-events: none;
  }

  /* Side by side Mode */
  .side-by-side-container {
    display: none;
    width: 100%;
    height: 100%;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    padding: 12px;
  }
  .side-box {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    position: relative;
    display: flex;
    flex-direction: column;
  }
  .side-title {
    padding: 6px 12px;
    font-size: 0.75rem;
    color: var(--text-muted);
    background: rgba(0,0,0,0.3);
  }
  .side-img-wrapper {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .side-img-wrapper img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  /* Footer Action Buttons */
  .action-bar {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 4px;
  }

  button.btn {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: all 0.15s ease;
  }
  button.btn:hover { background: var(--surface-hover); border-color: #4b5563; }

  button.btn-primary {
    background: var(--primary);
    border-color: var(--primary);
    color: #ffffff;
    box-shadow: 0 2px 10px var(--accent-glow);
  }
  button.btn-primary:hover {
    background: var(--primary-hover);
    border-color: var(--primary-hover);
  }

  .badge-kbd {
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 0.75rem;
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <img src="/assets/icon.png" class="app-logo" alt="Logo">
    <div class="brand-title">BG Remover</div>
    <div class="brand-tag">Offline App</div>
  </div>

  <div class="top-controls">
    <div class="model-select-group">
      <label for="modelSelect">AI Model:</label>
      <select id="modelSelect">
        <!-- populated dynamically -->
      </select>
    </div>

    <div class="model-select-group">
      <label for="trimSelect">Edge Defringe:</label>
      <select id="trimSelect" title="Remove dark edge halos while keeping smooth anti-aliased curves">
        <option value="1" selected>Smooth & Clean (Recommended)</option>
        <option value="2">Deep Defringe (Strong Shadows)</option>
        <option value="0">Natural (Raw)</option>
      </select>
    <label class="auto-copy-toggle" title="Repairs false interior holes on solid subjects (uncheck for hollow objects like headphones or mug handles)">
      <input type="checkbox" id="recoverHolesCheck" checked>
      <span>Solid Subject</span>
    </label>

    <label class="auto-copy-toggle" title="Automatically copy transparent PNG to clipboard once removal completes">
      <input type="checkbox" id="autoCopyCheck" checked>
      <span>Auto-copy result</span>
    </label>
  </div>
</header>

<main>
  <div class="drop-box" id="dropZone">
    <h2>Paste Image <kbd>Ctrl</kbd> + <kbd>V</kbd></h2>
    <p>Copy any image from the web, screenshot, or drag and drop an image file here</p>
    <input type="file" id="fileInput" accept="image/*" style="display:none;">
  </div>

  <div class="status-bar">
    <div class="status-msg">
      <div class="spinner" id="spinner"></div>
      <span id="statusText">Ready for clipboard input</span>
    </div>
    <div id="metaInfo" style="font-size:0.8rem; color:var(--text-subtle);"></div>
  </div>

  <div class="workspace" id="workspace">
    <div class="view-toolbar">
      <div class="toolbar-group">
        <span style="font-size:0.85rem; color:var(--text-muted);">View:</span>
        <div class="btn-group">
          <button id="viewSplit" class="active" onclick="setViewMode('split')">Split Slider</button>
          <button id="viewSide" onclick="setViewMode('side')">Side-by-Side</button>
          <button id="viewCutout" onclick="setViewMode('cutout')">Cutout Only</button>
          <button id="viewBrush" onclick="setViewMode('brush')" title="Refine edges, erase stray background, or restore clipped parts">🖌️ Refine Brush</button>
        </div>
      </div>

      <div class="toolbar-group">
        <span style="font-size:0.85rem; color:var(--text-muted);">Backdrop:</span>
        <div class="bg-swatches">
          <div class="swatch swatch-check-dark active" title="Dark Checkerboard" onclick="setBackdrop('check-dark', this)"></div>
          <div class="swatch swatch-check-light" title="Light Checkerboard" onclick="setBackdrop('check-light', this)"></div>
          <div class="swatch swatch-black" title="Solid Black" onclick="setBackdrop('black', this)"></div>
          <div class="swatch swatch-white" title="Solid White" onclick="setBackdrop('white', this)"></div>
          <div class="swatch swatch-green" title="Green Screen" onclick="setBackdrop('green', this)"></div>
        </div>
      </div>
    </div>

    <!-- Dedicated Brush Controls Toolbar -->
    <div class="brush-toolbar" id="brushToolbar">
      <div class="brush-controls-left">
        <div class="brush-param-group">
          <span>Mode:</span>
          <div class="brush-btn-group">
            <button id="modeSmartBtn" class="brush-tool-btn active-smart" onclick="setBrushSnapMode('smart')" title="Smart AI Edge-Snapping (Auto-snaps to subject boundaries like remove.bg)">✨ Smart AI</button>
            <button id="modeManualBtn" class="brush-tool-btn" onclick="setBrushSnapMode('manual')" title="Manual pixel painting (exact pixel-by-pixel control)">🖌️ Manual</button>
          </div>
        </div>

        <div class="brush-param-group">
          <span>Tool:</span>
          <div class="brush-btn-group">
            <button id="toolEraseBtn" class="brush-tool-btn active-erase" onclick="setBrushTool('erase')" title="Erase background with edge snapping (E or 1)">⌫ Erase</button>
            <button id="toolRestoreBtn" class="brush-tool-btn" onclick="setBrushTool('restore')" title="Restore subject with edge snapping (R or 2)">⎗ Restore</button>
            <button id="toolMagicTapBtn" class="brush-tool-btn" onclick="setBrushTool('magic-tap')" title="Magic Tap: Click any enclosed hole or background pocket to auto-erase it in 1 click (M or 3)">🪄 Magic Tap</button>
          </div>
        </div>

        <div class="brush-param-group" id="brushSizeGroup">
          <label for="brushSizeInput">Size:</label>
          <input type="range" id="brushSizeInput" min="4" max="150" value="30" oninput="setBrushSize(this.value)">
          <span id="brushSizeVal" class="brush-badge">30px</span>
        </div>

        <div class="brush-param-group" id="brushTolGroup">
          <label for="brushTolInput" title="Controls how far smart erase expands over gradients and shadows (higher = covers more shadow)">Tolerance:</label>
          <input type="range" id="brushTolInput" min="10" max="85" value="35" oninput="setBrushTolerance(this.value)">
          <span id="brushTolVal" class="brush-badge">35%</span>
        </div>

        <div class="brush-param-group" id="brushSoftGroup">
          <label for="brushSoftInput">Softness:</label>
          <input type="range" id="brushSoftInput" min="0" max="100" value="25" oninput="setBrushSoftness(this.value)">
          <span id="brushSoftVal" class="brush-badge">25%</span>
        </div>

        <div class="brush-param-group">
          <span>Zoom:</span>
          <div class="brush-btn-group">
            <button class="brush-tool-btn" onclick="zoomBrush(-0.25)" title="Zoom Out">-</button>
            <span id="brushZoomVal" class="brush-badge" onclick="resetBrushZoom()" title="Click to Fit to Screen" style="cursor:pointer;">Fit</span>
            <button class="brush-tool-btn" onclick="zoomBrush(0.25)" title="Zoom In">+</button>
          </div>
        </div>
      </div>

      <div class="brush-controls-right">
        <button class="btn" id="brushUndoBtn" onclick="undoBrush()" title="Undo stroke (Ctrl+Z)" style="padding:5px 10px; font-size:0.8rem;" disabled>↶ Undo</button>
        <button class="btn" id="brushRedoBtn" onclick="redoBrush()" title="Redo stroke (Ctrl+Y)" style="padding:5px 10px; font-size:0.8rem;" disabled>↷ Redo</button>
        <button class="btn" id="brushResetBtn" onclick="resetBrushToAI()" title="Reset all touch-ups back to AI cutout" style="padding:5px 10px; font-size:0.8rem;">↺ Reset</button>
        <button class="btn btn-primary" onclick="setViewMode('split')" style="padding:5px 14px; font-size:0.8rem;" title="Finish touch-ups and view comparison">✓ Done</button>
      </div>
    </div>

    <!-- Preview Stage -->
    <div class="preview-stage backdrop-check-dark" id="previewStage">
      <!-- Split Slider View -->
      <div class="slider-container" id="sliderContainer">
        <!-- Layer 1: Cutout on backdrop -->
        <div class="slider-cutout-layer backdrop-check-dark" id="cutoutLayer">
          <img id="imgCutout" class="slider-img" alt="Cutout">
          <span class="badge-label badge-after">Cutout</span>
        </div>

        <!-- Layer 2: Original image clipped by slider -->
        <div class="slider-original-clip" id="sliderClipOriginal">
          <img id="imgOriginal" class="slider-img" alt="Original">
          <span class="badge-label badge-before">Original</span>
        </div>

        <div class="slider-handle" id="sliderHandle">
          <div class="slider-button">⬌</div>
        </div>
      </div>

      <!-- Side by Side View -->
      <div class="side-by-side-container" id="sideContainer">
        <div class="side-box">
          <div class="side-title">Original</div>
          <div class="side-img-wrapper"><img id="sideOrig" alt="Original"></div>
        </div>
        <div class="side-box backdrop-check-dark" id="sideCutoutWrapper">
          <div class="side-title">Cutout (Transparent)</div>
          <div class="side-img-wrapper"><img id="sideCutout" alt="Cutout"></div>
        </div>
      </div>

      <!-- Interactive Brush Refine Stage -->
      <div class="brush-stage" id="brushStage">
        <div class="brush-canvas-wrapper backdrop-check-dark" id="brushCanvasWrapper">
          <canvas id="brushCanvas"></canvas>
        </div>
        <div id="brushCursor" class="brush-cursor mode-erase"></div>
      </div>
    </div>
    <!-- Action Bar -->
    <div class="action-bar">
      <button class="btn" onclick="document.getElementById('fileInput').click()">Upload Different Image</button>
      <button class="btn" id="downloadBtn" onclick="downloadImage()">Save PNG <span class="badge-kbd">Ctrl+S</span></button>
      <button class="btn btn-primary" id="copyBtn" onclick="copyResultToClipboard()">
        <span>Copy PNG to Clipboard</span> <span class="badge-kbd">Ctrl+C</span>
      </button>
    </div>
  </div>
</main>

<script>
  let currentFile = null;
  let currentCutoutBlob = null;
  let currentViewMode = 'split';
  let isDragging = false;
  let sliderPos = 50;

  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const modelSelect = document.getElementById('modelSelect');
  const autoCopyCheck = document.getElementById('autoCopyCheck');
  const spinner = document.getElementById('spinner');
  const statusText = document.getElementById('statusText');
  const metaInfo = document.getElementById('metaInfo');
  const workspace = document.getElementById('workspace');
  const previewStage = document.getElementById('previewStage');

  const imgOriginal = document.getElementById('imgOriginal');
  const imgCutout = document.getElementById('imgCutout');
  const cutoutLayer = document.getElementById('cutoutLayer');
  const sliderClipOriginal = document.getElementById('sliderClipOriginal');
  const sliderHandle = document.getElementById('sliderHandle');
  const sliderContainer = document.getElementById('sliderContainer');
  const sideContainer = document.getElementById('sideContainer');
  const sideOrig = document.getElementById('sideOrig');
  const sideCutout = document.getElementById('sideCutout');
  const sideCutoutWrapper = document.getElementById('sideCutoutWrapper');
  const brushToolbar = document.getElementById('brushToolbar');
  const brushStage = document.getElementById('brushStage');
  const brushCanvasWrapper = document.getElementById('brushCanvasWrapper');
  const brushCanvas = document.getElementById('brushCanvas');
  const brushCtx = brushCanvas.getContext('2d', { willReadFrequently: true });
  const brushCursor = document.getElementById('brushCursor');

  // Brush tool state
  let brushSnapMode = 'smart'; // 'smart' | 'manual'
  let brushTool = 'erase'; // 'erase' | 'restore' | 'magic-tap'
  let brushRadius = 15;
  let brushTolerance = 35;
  let brushSoftness = 25;
  let brushZoom = 1.0;
  let brushPanX = 0;
  let brushPanY = 0;
  let isPainting = false;
  let isPanning = false;
  let isSpacePressed = false;
  let panStartX = 0;
  let panStartY = 0;
  let lastX = 0;
  let lastY = 0;
  let undoStack = [];
  let redoStack = [];
  let initialAIBitmap = null;
  let brushInitialized = false;
  let activeCutoutImgData = null;
  let activeOrigImgData = null;
  const origCanvas = document.createElement('canvas');
  const origCtx = origCanvas.getContext('2d');
  const scratchCanvas = document.createElement('canvas');
  const scratchCtx = scratchCanvas.getContext('2d');

  // Keep server alive while window is open
  setInterval(() => {
    fetch('/api/ping').catch(() => {});
  }, 2500);

  // Load models on startup
  async function loadModels() {
    try {
      const res = await fetch('/api/models');
      const data = await res.json();
      modelSelect.innerHTML = '';
      for (const [key, val] of Object.entries(data)) {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = val.label;
        if (val.default) opt.selected = true;
        modelSelect.appendChild(opt);
      }
    } catch (e) {
      console.error('Failed to load models list', e);
    }
  }
  loadModels();

  // Model & Defringe switch re-processes if image is active
  modelSelect.addEventListener('change', () => {
    if (currentFile) processImage(currentFile);
  });
  const trimSelect = document.getElementById('trimSelect');
  if (trimSelect) {
    trimSelect.addEventListener('change', () => {
      if (currentFile) processImage(currentFile);
    });
  }
  const recoverHolesCheck = document.getElementById('recoverHolesCheck');
  if (recoverHolesCheck) {
    recoverHolesCheck.addEventListener('change', () => {
      if (currentFile) processImage(currentFile);
    });
  }

  // Paste Event
  window.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (const item of items) {
      if (item.type.indexOf('image') !== -1) {
        const file = item.getAsFile();
        processImage(file);
        break;
      }
    }
  });

  // Drag & drop
  ['dragenter', 'dragover'].forEach(ev => dropZone.addEventListener(ev, (e) => {
    e.preventDefault(); dropZone.classList.add('dragover');
  }));
  ['dragleave', 'drop'].forEach(ev => dropZone.addEventListener(ev, (e) => {
    e.preventDefault(); dropZone.classList.remove('dragover');
  }));
  dropZone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length > 0 && e.dataTransfer.files[0].type.startsWith('image/')) {
      processImage(e.dataTransfer.files[0]);
    }
  });
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) processImage(e.target.files[0]);
  });

  // Shortcuts: Ctrl+C to copy, Ctrl+S to save
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c' && currentCutoutBlob) {
      copyResultToClipboard();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && currentCutoutBlob) {
      e.preventDefault();
      downloadImage();
    }
  });

  // Core Processing Routine
  async function processImage(file) {
    currentFile = file;
    currentCutoutBlob = null;

    const origUrl = URL.createObjectURL(file);
    imgOriginal.src = origUrl;
    sideOrig.src = origUrl;

    workspace.style.display = 'flex';
    spinner.style.display = 'inline-block';
    statusText.innerHTML = `Removing background using <b>${modelSelect.value}</b>...`;
    metaInfo.textContent = '';

    const startTime = performance.now();

    try {
      const model = modelSelect.value;
      const trim = document.getElementById('trimSelect')?.value ?? '1';
      const recoverHoles = document.getElementById('recoverHolesCheck')?.checked ?? true;
      const resp = await fetch(`/api/remove?model=${encodeURIComponent(model)}&trim=${encodeURIComponent(trim)}&decontaminate=true&recover_holes=${recoverHoles}`, {
        method: 'POST',
        body: file
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || 'Processing failed');
      }

      const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
      currentCutoutBlob = await resp.blob();
      const cutoutUrl = URL.createObjectURL(currentCutoutBlob);

      imgCutout.src = cutoutUrl;
      sideCutout.src = cutoutUrl;

      // Invalidate brush state so it re-initializes on next brush view
      brushInitialized = false;
      if (currentViewMode === 'brush') {
        await initBrushCanvases();
      }

      spinner.style.display = 'none';
      metaInfo.textContent = `Completed in ${elapsed}s (${(file.size / 1024).toFixed(0)} KB input)`;

      if (autoCopyCheck.checked) {
        await copyResultToClipboard(true);
      } else {
        statusText.innerHTML = `<span class="toast">✓ Background removed in ${elapsed}s!</span>`;
      }
    } catch (err) {
      spinner.style.display = 'none';
      statusText.innerHTML = `<span style="color:#ef4444;">Error: ${err.message}</span>`;
      console.error(err);
    }
  }

  // Clipboard Output
  async function copyResultToClipboard(isAuto = false) {
    if (!currentCutoutBlob) return;
    try {
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': currentCutoutBlob })
      ]);
      const prefix = isAuto ? 'Auto-copied' : 'Copied';
      statusText.innerHTML = `<span class="toast">✓ ${prefix} transparent PNG to clipboard! Ready to paste.</span>`;
    } catch (err) {
      statusText.innerHTML = `<span style="color:#f59e0b;">Clipboard write error: ${err.message}. Click Copy button.</span>`;
    }
  }

  function downloadImage() {
    if (!currentCutoutBlob) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(currentCutoutBlob);
    a.download = `cutout-${Date.now()}.png`;
    a.click();
  }

  // View Mode Controls
  async function setViewMode(mode) {
    currentViewMode = mode;
    document.querySelectorAll('.btn-group button').forEach(b => b.classList.remove('active'));

    if (mode === 'brush') {
      document.getElementById('viewBrush').classList.add('active');
      sliderContainer.style.display = 'none';
      sideContainer.style.display = 'none';
      brushStage.style.display = 'flex';
      brushToolbar.style.display = 'flex';
      if (!brushInitialized && currentCutoutBlob) {
        await initBrushCanvases();
      } else if (brushInitialized) {
        fitBrushToStage();
      }
    } else {
      brushStage.style.display = 'none';
      brushToolbar.style.display = 'none';

      if (mode === 'split') {
        document.getElementById('viewSplit').classList.add('active');
        sliderContainer.style.display = 'flex';
        sideContainer.style.display = 'none';
        sliderClipOriginal.style.display = 'block';
        sliderHandle.style.display = 'block';
        updateSlider(sliderPos);
      } else if (mode === 'side') {
        document.getElementById('viewSide').classList.add('active');
        sliderContainer.style.display = 'none';
        sideContainer.style.display = 'grid';
      } else if (mode === 'cutout') {
        document.getElementById('viewCutout').classList.add('active');
        sliderContainer.style.display = 'flex';
        sideContainer.style.display = 'none';
        sliderClipOriginal.style.display = 'none';
        sliderHandle.style.display = 'none';
      }
    }
  }
  // Backdrop Swatches
  function setBackdrop(type, el) {
    document.querySelectorAll('.swatch').forEach(s => s.classList.remove('active'));
    if (el) {
      el.classList.add('active');
    } else {
      const match = document.querySelector(`.swatch-${type}`);
      if (match) match.classList.add('active');
    }

    const classMap = {
      'check-dark': 'backdrop-check-dark',
      'check-light': 'backdrop-check-light',
      'black': 'backdrop-black',
      'white': 'backdrop-white',
      'green': 'backdrop-green'
    };

    const targetClass = classMap[type] || 'backdrop-check-dark';
    const allBackdropClasses = Object.values(classMap);

    const targets = [cutoutLayer, sideCutoutWrapper, previewStage, brushCanvasWrapper];
    targets.forEach(t => {
      if (!t) return;
      allBackdropClasses.forEach(c => t.classList.remove(c));
      t.classList.add(targetClass);
    });
  }

  // Split-view slider mouse/touch tracking
  function updateSlider(pct) {
    sliderPos = Math.max(0, Math.min(100, pct));
    if (sliderClipOriginal) {
      sliderClipOriginal.style.clipPath = `polygon(0 0, ${sliderPos}% 0, ${sliderPos}% 100%, 0 100%)`;
    }
    if (sliderHandle) {
      sliderHandle.style.left = `${sliderPos}%`;
    }
  }
  updateSlider(50);

  function handleSlide(e) {
    if (!isDragging || currentViewMode !== 'split') return;
    const rect = sliderContainer.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const pct = ((clientX - rect.left) / rect.width) * 100;
    updateSlider(pct);
  }

  sliderContainer.addEventListener('mousedown', () => { isDragging = true; });
  window.addEventListener('mouseup', () => { isDragging = false; });
  window.addEventListener('mousemove', handleSlide);

  sliderContainer.addEventListener('touchstart', () => { isDragging = true; });
  window.addEventListener('touchend', () => { isDragging = false; });
  window.addEventListener('touchmove', handleSlide);

  // Brush Tools & Operations
  function setBrushTool(tool) {
    brushTool = tool;
    const eraseBtn = document.getElementById('toolEraseBtn');
    const restoreBtn = document.getElementById('toolRestoreBtn');
    const magicTapBtn = document.getElementById('toolMagicTapBtn');
    const sizeGroup = document.getElementById('brushSizeGroup');

    if (eraseBtn) eraseBtn.classList.remove('active-erase');
    if (restoreBtn) restoreBtn.classList.remove('active-restore');
    if (magicTapBtn) magicTapBtn.classList.remove('active-magic-tap');

    brushCursor.classList.remove('mode-erase', 'mode-restore', 'mode-magic-tap');

    if (tool === 'erase') {
      if (eraseBtn) eraseBtn.classList.add('active-erase');
      brushCursor.classList.add('mode-erase');
      if (sizeGroup) sizeGroup.style.display = 'flex';
      statusText.innerHTML = `<span class="toast">⌫ Erase tool active (edge-snapping in Smart mode)</span>`;
    } else if (tool === 'restore') {
      if (restoreBtn) restoreBtn.classList.add('active-restore');
      brushCursor.classList.add('mode-restore');
      if (sizeGroup) sizeGroup.style.display = 'flex';
      statusText.innerHTML = `<span class="toast">⎗ Restore tool active (edge-snapping in Smart mode)</span>`;
    } else if (tool === 'magic-tap') {
      if (magicTapBtn) magicTapBtn.classList.add('active-magic-tap');
      brushCursor.classList.add('mode-magic-tap');
      if (sizeGroup) sizeGroup.style.display = 'none';
      statusText.innerHTML = `<span class="toast">🪄 Magic Tap: Click anywhere inside an enclosed hole or background pocket to auto-erase it instantly!</span>`;
    }
  }

  function setBrushSnapMode(mode) {
    brushSnapMode = mode;
    const smartBtn = document.getElementById('modeSmartBtn');
    const manualBtn = document.getElementById('modeManualBtn');
    const tolGroup = document.getElementById('brushTolGroup');
    if (mode === 'smart') {
      if (smartBtn) smartBtn.classList.add('active-smart');
      if (manualBtn) manualBtn.classList.remove('active-smart');
      if (tolGroup) tolGroup.style.display = 'flex';
      statusText.innerHTML = `<span class="toast">✨ Smart AI mode active: strokes automatically snap to object boundaries</span>`;
    } else {
      if (manualBtn) manualBtn.classList.add('active-smart');
      if (smartBtn) smartBtn.classList.remove('active-smart');
      if (tolGroup) tolGroup.style.display = 'none';
      statusText.innerHTML = `<span class="toast">🖌️ Manual mode active: exact pixel painting</span>`;
    }
  }

  function setBrushTolerance(val) {
    brushTolerance = Math.max(10, Math.min(85, parseInt(val, 10)));
    const badge = document.getElementById('brushTolVal');
    const slider = document.getElementById('brushTolInput');
    if (badge) badge.textContent = `${brushTolerance}%`;
    if (slider && parseInt(slider.value, 10) !== brushTolerance) slider.value = brushTolerance;
  }

  function setBrushSize(val) {
    const num = parseInt(val, 10);
    brushRadius = Math.max(2, Math.round(num / 2));
    const badge = document.getElementById('brushSizeVal');
    const slider = document.getElementById('brushSizeInput');
    if (badge) badge.textContent = `${num}px`;
    if (slider && parseInt(slider.value, 10) !== num) slider.value = num;
  }

  function setBrushSoftness(val) {
    brushSoftness = Math.max(0, Math.min(100, parseInt(val, 10)));
    const badge = document.getElementById('brushSoftVal');
    const slider = document.getElementById('brushSoftInput');
    if (badge) badge.textContent = `${brushSoftness}%`;
    if (slider && parseInt(slider.value, 10) !== brushSoftness) slider.value = brushSoftness;
  }

  async function initBrushCanvases() {
    let w = 0, h = 0;
    let origBmp = null;
    let cutoutBmp = null;

    try {
      if (currentCutoutBlob) {
        cutoutBmp = await createImageBitmap(currentCutoutBlob);
        w = cutoutBmp.width;
        h = cutoutBmp.height;
      }
      if (currentFile) {
        origBmp = await createImageBitmap(currentFile);
      }
    } catch (e) {
      console.warn('createImageBitmap failed, falling back to image elements', e);
    }

    if (!w || !h) {
      if (!imgOriginal.complete) {
        await new Promise(r => { imgOriginal.onload = r; });
      }
      if (!imgCutout.complete) {
        await new Promise(r => { imgCutout.onload = r; });
      }
      w = imgOriginal.naturalWidth || imgOriginal.width;
      h = imgOriginal.naturalHeight || imgOriginal.height;
    }

    if (!w || !h) return;

    brushCanvas.width = w;
    brushCanvas.height = h;

    origCanvas.width = w;
    origCanvas.height = h;
    origCtx.clearRect(0, 0, w, h);
    if (origBmp) {
      origCtx.drawImage(origBmp, 0, 0);
      if (origBmp.close) origBmp.close();
    } else {
      origCtx.drawImage(imgOriginal, 0, 0);
    }

    scratchCanvas.width = w;
    scratchCanvas.height = h;

    brushCtx.clearRect(0, 0, w, h);
    if (cutoutBmp) {
      brushCtx.drawImage(cutoutBmp, 0, 0);
      if (cutoutBmp.close) cutoutBmp.close();
    } else {
      brushCtx.drawImage(imgCutout, 0, 0);
    }

    try {
      if (initialAIBitmap && initialAIBitmap.close) initialAIBitmap.close();
      initialAIBitmap = await createImageBitmap(brushCanvas);
      undoStack.forEach(b => b.close && b.close());
      redoStack.forEach(b => b.close && b.close());
      undoStack = [];
      redoStack = [];
      updateHistoryButtons();
    } catch (e) {
      console.warn('createImageBitmap error', e);
    }

    brushInitialized = true;
    fitBrushToStage();
  }

  function fitBrushToStage() {
    const stageRect = previewStage.getBoundingClientRect();
    const pad = 24;
    const availW = Math.max(100, (stageRect.width || 800) - pad * 2);
    const availH = Math.max(100, (stageRect.height || 480) - pad * 2);

    const w = brushCanvas.width;
    const h = brushCanvas.height;
    if (!w || !h) return;

    const scale = Math.min(availW / w, availH / h);
    const dispW = Math.round(w * scale);
    const dispH = Math.round(h * scale);

    brushCanvas.style.width = dispW + 'px';
    brushCanvas.style.height = dispH + 'px';

    brushZoom = 1.0;
    brushPanX = 0;
    brushPanY = 0;
    applyBrushTransform();
    updateZoomBadge();
  }

  function applyBrushTransform() {
    brushCanvasWrapper.style.transform = `translate(${brushPanX}px, ${brushPanY}px) scale(${brushZoom})`;
  }

  function updateZoomBadge() {
    const badge = document.getElementById('brushZoomVal');
    if (!badge) return;
    if (Math.abs(brushZoom - 1.0) < 0.05 && brushPanX === 0 && brushPanY === 0) {
      badge.textContent = 'Fit';
    } else {
      badge.textContent = `${Math.round(brushZoom * 100)}%`;
    }
  }

  function zoomBrush(delta) {
    brushZoom = Math.min(5.0, Math.max(0.5, Math.round((brushZoom + delta) * 100) / 100));
    applyBrushTransform();
    updateZoomBadge();
  }

  function resetBrushZoom() {
    fitBrushToStage();
  }

  async function pushBrushHistory() {
    try {
      const bmp = await createImageBitmap(brushCanvas);
      undoStack.push(bmp);
      if (undoStack.length > 15) {
        const dropped = undoStack.shift();
        if (dropped && dropped.close) dropped.close();
      }
      redoStack.forEach(b => b.close && b.close());
      redoStack = [];
      updateHistoryButtons();
    } catch (err) {
      console.warn('History capture error', err);
    }
  }

  async function undoBrush() {
    if (undoStack.length === 0) return;
    try {
      const currentBmp = await createImageBitmap(brushCanvas);
      redoStack.push(currentBmp);

      const prevBmp = undoStack.pop();
      brushCtx.clearRect(0, 0, brushCanvas.width, brushCanvas.height);
      brushCtx.drawImage(prevBmp, 0, 0);
      if (prevBmp.close) prevBmp.close();

      commitBrushToBlobs();
      updateHistoryButtons();
    } catch (err) {
      console.error('Undo error', err);
    }
  }

  async function redoBrush() {
    if (redoStack.length === 0) return;
    try {
      const currentBmp = await createImageBitmap(brushCanvas);
      undoStack.push(currentBmp);

      const nextBmp = redoStack.pop();
      brushCtx.clearRect(0, 0, brushCanvas.width, brushCanvas.height);
      brushCtx.drawImage(nextBmp, 0, 0);
      if (nextBmp.close) nextBmp.close();

      commitBrushToBlobs();
      updateHistoryButtons();
    } catch (err) {
      console.error('Redo error', err);
    }
  }

  async function resetBrushToAI() {
    if (!initialAIBitmap) return;
    await pushBrushHistory();
    brushCtx.clearRect(0, 0, brushCanvas.width, brushCanvas.height);
    brushCtx.drawImage(initialAIBitmap, 0, 0);
    commitBrushToBlobs();
    statusText.innerHTML = `<span class="toast">↺ Reverted all manual edits to original AI cutout</span>`;
  }

  function updateHistoryButtons() {
    const undoBtn = document.getElementById('brushUndoBtn');
    const redoBtn = document.getElementById('brushRedoBtn');
    if (undoBtn) undoBtn.disabled = undoStack.length === 0;
    if (redoBtn) redoBtn.disabled = redoStack.length === 0;
  }

  function commitBrushToBlobs() {
    brushCanvas.toBlob(blob => {
      if (!blob) return;
      currentCutoutBlob = blob;
      const url = URL.createObjectURL(blob);
      imgCutout.src = url;
      sideCutout.src = url;
    }, 'image/png');
  }

  function getCanvasCoords(clientX, clientY) {
    const rect = brushCanvas.getBoundingClientRect();
    const normX = (clientX - rect.left) / rect.width;
    const normY = (clientY - rect.top) / rect.height;
    return {
      x: normX * brushCanvas.width,
      y: normY * brushCanvas.height,
      inside: normX >= 0 && normX <= 1 && normY >= 0 && normY <= 1
    };
  }

  function drawBrushSegment(x0, y0, x1, y1) {
    if (brushTool === 'erase') {
      brushCtx.save();
      brushCtx.globalCompositeOperation = 'destination-out';
      brushCtx.lineCap = 'round';
      brushCtx.lineJoin = 'round';
      brushCtx.lineWidth = brushRadius * 2;
      if (brushSoftness > 0) {
        brushCtx.shadowBlur = brushRadius * (brushSoftness / 100);
        brushCtx.shadowColor = 'black';
      }
      brushCtx.strokeStyle = 'black';
      brushCtx.beginPath();
      brushCtx.moveTo(x0, y0);
      brushCtx.lineTo(x1, y1);
      brushCtx.stroke();
      brushCtx.restore();
    } else if (brushTool === 'restore') {
      scratchCtx.clearRect(0, 0, scratchCanvas.width, scratchCanvas.height);
      scratchCtx.save();
      scratchCtx.lineCap = 'round';
      scratchCtx.lineJoin = 'round';
      scratchCtx.lineWidth = brushRadius * 2;
      if (brushSoftness > 0) {
        scratchCtx.shadowBlur = brushRadius * (brushSoftness / 100);
        scratchCtx.shadowColor = 'black';
      }
      scratchCtx.strokeStyle = 'black';
      scratchCtx.beginPath();
      scratchCtx.moveTo(x0, y0);
      scratchCtx.lineTo(x1, y1);
      scratchCtx.stroke();
      scratchCtx.restore();

      // Mask scratch with original image
      scratchCtx.save();
      scratchCtx.globalCompositeOperation = 'source-in';
      scratchCtx.drawImage(origCanvas, 0, 0);
      scratchCtx.restore();

      // Composite onto main cutout canvas
      brushCtx.save();
      brushCtx.globalCompositeOperation = 'source-over';
      brushCtx.drawImage(scratchCanvas, 0, 0);
      brushCtx.restore();
    }
  }

  // Magic Tap: One-Click Bounded Region Removal
  function magicTapErase(startX, startY, tolPct) {
    const w = brushCanvas.width;
    const h = brushCanvas.height;
    startX = Math.max(0, Math.min(w - 1, Math.round(startX)));
    startY = Math.max(0, Math.min(h - 1, Math.round(startY)));

    const cutoutImgData = brushCtx.getImageData(0, 0, w, h);
    const origImgData = origCtx.getImageData(0, 0, w, h);
    const orig = origImgData.data;
    const cutout = cutoutImgData.data;

    const colorTol = (tolPct / 100) * 125;
    const colorTolSq = colorTol * colorTol;
    const edgeBarrier = Math.max(10, (100 - tolPct) * 0.35);

    const sIdx = (startY * w + startX) * 4;
    const sR = orig[sIdx], sG = orig[sIdx + 1], sB = orig[sIdx + 2];

    const visited = new Uint8Array(w * h);
    const queue = new Int32Array(w * h);
    let head = 0, tail = 0;

    const startPos = startY * w + startX;
    queue[tail++] = startPos;
    visited[startPos] = 1;

    let erased = 0;
    let minX = startX, maxX = startX, minY = startY, maxY = startY;

    while (head < tail) {
      const curr = queue[head++];
      const cx = curr % w;
      const cy = (curr / w) | 0;
      const cIdx = curr * 4;

      cutout[cIdx + 3] = 0;
      erased++;

      if (cx < minX) minX = cx;
      if (cx > maxX) maxX = cx;
      if (cy < minY) minY = cy;
      if (cy > maxY) maxY = cy;

      const cR = orig[cIdx], cG = orig[cIdx + 1], cB = orig[cIdx + 2];

      const neighbors = [
        cx > 0 ? curr - 1 : -1,
        cx < w - 1 ? curr + 1 : -1,
        cy > 0 ? curr - w : -1,
        cy < h - 1 ? curr + w : -1
      ];

      for (let i = 0; i < 4; i++) {
        const n = neighbors[i];
        if (n >= 0 && !visited[n]) {
          const nIdx = n * 4;
          const nR = orig[nIdx], nG = orig[nIdx + 1], nB = orig[nIdx + 2];

          // Edge contrast step
          const sdr = nR - cR, sdg = nG - cG, sdb = nB - cB;
          if (Math.hypot(sdr, sdg, sdb) > edgeBarrier) continue;

          // Color difference from clicked seed
          const gdr = nR - sR, gdg = nG - sG, gdb = nB - sB;
          if (gdr * gdr + gdg * gdg + gdb * gdb > colorTolSq) continue;

          visited[n] = 1;
          queue[tail++] = n;
        }
      }
    }

    if (erased > 0) {
      brushCtx.putImageData(cutoutImgData, 0, 0, minX, minY, maxX - minX + 1, maxY - minY + 1);
    }
    return erased;
  }

  // Smart AI Edge-Snapping Stamp (Drag)
  function smartBrushStamp(centerX, centerY, radius, tolPct, mode) {
    if (!activeCutoutImgData || !activeOrigImgData) {
      activeCutoutImgData = brushCtx.getImageData(0, 0, brushCanvas.width, brushCanvas.height);
      activeOrigImgData = origCtx.getImageData(0, 0, brushCanvas.width, brushCanvas.height);
    }
    const w = brushCanvas.width;
    const h = brushCanvas.height;
    const orig = activeOrigImgData.data;
    const cutout = activeCutoutImgData.data;

    centerX = Math.max(0, Math.min(w - 1, Math.round(centerX)));
    centerY = Math.max(0, Math.min(h - 1, Math.round(centerY)));

    const colorTol = (tolPct / 100) * 115;
    const colorTolSq = colorTol * colorTol;
    const edgeBarrier = Math.max(10, (100 - tolPct) * 0.35);

    const sIdx = (centerY * w + centerX) * 4;
    const sR = orig[sIdx], sG = orig[sIdx + 1], sB = orig[sIdx + 2];

    const rSq = radius * radius;
    const minX = Math.max(0, centerX - radius);
    const maxX = Math.min(w - 1, centerX + radius);
    const minY = Math.max(0, centerY - radius);
    const maxY = Math.min(h - 1, centerY + radius);

    const localW = maxX - minX + 1;
    const localH = maxY - minY + 1;
    const visited = new Uint8Array(localW * localH);
    const queue = new Int32Array(localW * localH);
    let head = 0, tail = 0;

    const startLocal = (centerY - minY) * localW + (centerX - minX);
    queue[tail++] = startLocal;
    visited[startLocal] = 1;

    let changed = 0;

    while (head < tail) {
      const curr = queue[head++];
      const lx = curr % localW;
      const ly = (curr / localW) | 0;
      const gx = minX + lx;
      const gy = minY + ly;

      const gIdx = (gy * w + gx) * 4;

      if (mode === 'erase') {
        cutout[gIdx + 3] = 0;
      } else {
        cutout[gIdx] = orig[gIdx];
        cutout[gIdx + 1] = orig[gIdx + 1];
        cutout[gIdx + 2] = orig[gIdx + 2];
        cutout[gIdx + 3] = 255;
      }
      changed++;

      const cR = orig[gIdx], cG = orig[gIdx + 1], cB = orig[gIdx + 2];

      const neighbors = [
        lx > 0 ? curr - 1 : -1,
        lx < localW - 1 ? curr + 1 : -1,
        ly > 0 ? curr - localW : -1,
        ly < (maxY - minY) ? curr + localW : -1
      ];

      for (let i = 0; i < 4; i++) {
        const n = neighbors[i];
        if (n >= 0 && !visited[n]) {
          const nlx = n % localW;
          const nly = (n / localW) | 0;
          const ngx = minX + nlx;
          const ngy = minY + nly;

          const dx = ngx - centerX, dy = ngy - centerY;
          if (dx * dx + dy * dy > rSq) continue;

          const nIdx = (ngy * w + ngx) * 4;
          const nR = orig[nIdx], nG = orig[nIdx + 1], nB = orig[nIdx + 2];

          // Edge barrier: difference across step
          const sdr = nR - cR, sdg = nG - cG, sdb = nB - cB;
          if (Math.hypot(sdr, sdg, sdb) > edgeBarrier) continue;

          // Global seed tolerance
          const gdr = nR - sR, gdg = nG - sG, gdb = nB - sB;
          if (gdr * gdr + gdg * gdg + gdb * gdb > colorTolSq) continue;

          visited[n] = 1;
          queue[tail++] = n;
        }
      }
    }

    if (changed > 0) {
      brushCtx.putImageData(activeCutoutImgData, 0, 0, minX, minY, localW, localH);
    }
  }

  // Brush pointer & mouse interactions
  brushStage.addEventListener('pointermove', (e) => {
    if (currentViewMode !== 'brush') return;
    const stageRect = brushStage.getBoundingClientRect();
    const mx = e.clientX - stageRect.left;
    const my = e.clientY - stageRect.top;

    brushCursor.style.left = mx + 'px';
    brushCursor.style.top = my + 'px';

    const rect = brushCanvas.getBoundingClientRect();
    const scale = brushCanvas.width > 0 ? (rect.width / brushCanvas.width) : 1;
    const diam = brushTool === 'magic-tap' ? 24 : Math.max(6, Math.round(brushRadius * 2 * scale));
    brushCursor.style.width = diam + 'px';
    brushCursor.style.height = diam + 'px';
    brushCursor.style.display = 'block';

    if (isPanning) {
      brushPanX = e.clientX - panStartX;
      brushPanY = e.clientY - panStartY;
      applyBrushTransform();
      updateZoomBadge();
    } else if (isPainting) {
      const coords = getCanvasCoords(e.clientX, e.clientY);
      if (brushSnapMode === 'smart') {
        const dist = Math.hypot(coords.x - lastX, coords.y - lastY);
        const step = Math.max(2, brushRadius * 0.35);
        const steps = Math.ceil(dist / step);
        for (let i = 1; i <= steps; i++) {
          const t = i / steps;
          const ix = Math.round(lastX + (coords.x - lastX) * t);
          const iy = Math.round(lastY + (coords.y - lastY) * t);
          smartBrushStamp(ix, iy, brushRadius, brushTolerance, brushTool);
        }
      } else {
        drawBrushSegment(lastX, lastY, coords.x, coords.y);
      }
      lastX = coords.x;
      lastY = coords.y;
    }
  });

  brushStage.addEventListener('pointerleave', () => {
    brushCursor.style.display = 'none';
  });

  brushCanvas.addEventListener('pointerdown', async (e) => {
    if (currentViewMode !== 'brush') return;
    if (isSpacePressed || e.button === 1 || e.button === 2) {
      isPanning = true;
      panStartX = e.clientX - brushPanX;
      panStartY = e.clientY - brushPanY;
      brushStage.style.cursor = 'grabbing';
      return;
    }

    if (e.button === 0) {
      const coords = getCanvasCoords(e.clientX, e.clientY);
      if (!coords.inside) return;

      if (brushTool === 'magic-tap') {
        await pushBrushHistory();
        const erased = magicTapErase(coords.x, coords.y, brushTolerance);
        commitBrushToBlobs();
        statusText.innerHTML = `<span class="toast">🪄 Magic Tap removed background pocket (${erased.toLocaleString()} px)!</span>`;
        return;
      }

      await pushBrushHistory();
      isPainting = true;

      if (brushSnapMode === 'smart') {
        activeCutoutImgData = brushCtx.getImageData(0, 0, brushCanvas.width, brushCanvas.height);
        activeOrigImgData = origCtx.getImageData(0, 0, brushCanvas.width, brushCanvas.height);
        smartBrushStamp(coords.x, coords.y, brushRadius, brushTolerance, brushTool);
      } else {
        drawBrushSegment(coords.x, coords.y, coords.x, coords.y);
      }
      lastX = coords.x;
      lastY = coords.y;
    }
  });

  window.addEventListener('pointerup', () => {
    if (isPainting) {
      isPainting = false;
      activeCutoutImgData = null;
      activeOrigImgData = null;
      commitBrushToBlobs();
    }
    if (isPanning) {
      isPanning = false;
      brushStage.style.cursor = isSpacePressed ? 'grab' : 'default';
    }
  });

  window.addEventListener('pointercancel', () => {
    if (isPainting) {
      isPainting = false;
      activeCutoutImgData = null;
      activeOrigImgData = null;
      commitBrushToBlobs();
    }
    isPanning = false;
  });

  // Mouse wheel zoom in brush stage
  brushStage.addEventListener('wheel', (e) => {
    if (currentViewMode !== 'brush') return;
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.15 : -0.15;
    zoomBrush(delta);
  }, { passive: false });

  // Pan via spacebar
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && currentViewMode === 'brush' && !isSpacePressed) {
      isSpacePressed = true;
      brushStage.style.cursor = 'grab';
    }
  });
  window.addEventListener('keyup', (e) => {
    if (e.code === 'Space') {
      isSpacePressed = false;
      brushStage.style.cursor = 'default';
    }
  });

  // Hotkeys inside brush mode
  window.addEventListener('keydown', (e) => {
    if (currentViewMode === 'brush') {
      if (e.key === '[') {
        e.preventDefault();
        setBrushSize(Math.max(4, brushRadius * 2 - 6));
      } else if (e.key === ']') {
        e.preventDefault();
        setBrushSize(Math.min(150, brushRadius * 2 + 6));
      } else if (e.key.toLowerCase() === 'e' || e.key === '1') {
        setBrushTool('erase');
      } else if (e.key.toLowerCase() === 'r' || e.key === '2') {
        setBrushTool('restore');
      } else if (e.key.toLowerCase() === 'm' || e.key === '3') {
        setBrushTool('magic-tap');
      } else if (e.key.toLowerCase() === 's') {
        setBrushSnapMode(brushSnapMode === 'smart' ? 'manual' : 'smart');
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) redoBrush(); else undoBrush();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redoBrush();
      } else if (e.key === 'Escape') {
        setViewMode('split');
      }
    }
  });

  window.addEventListener('resize', () => {
    if (currentViewMode === 'brush') fitBrushToStage();
  });
</script>
</body>
</html>
"""
def fuse_dual_pass_saliency(input_bytes, orig_img, session):
    """
    Dual-pass AI Saliency Fusion:
    Pass 1 evaluates color saliency.
    Pass 2 evaluates structural luminance/grayscale saliency (user's breakthrough idea).
    Fusing both passes via maximum union ensures camouflaged surfaces (e.g. white shrimp meat,
    white clothing, reflections) are recognized naturally by the AI with 100% full opacity,
    eliminating low-opacity haze and avoiding artificial hole-patching.
    """
    import io, numpy as np
    from PIL import Image

    # Pass 1: Color Mask
    m_col_bytes = remove(input_bytes, session=session, only_mask=True, post_process_mask=False)
    m_col = np.array(Image.open(io.BytesIO(m_col_bytes)).convert("L"))

    # Pass 2: Desaturated / Luminance Mask
    gray_img = orig_img.convert("L").convert("RGB")
    buf_gray = io.BytesIO()
    gray_img.save(buf_gray, format="PNG")
    m_gray_bytes = remove(buf_gray.getvalue(), session=session, only_mask=True, post_process_mask=False)
    m_gray = np.array(Image.open(io.BytesIO(m_gray_bytes)).convert("L"))

    # Native Saliency Union: combines best of color and structural contours
    m_fused = np.maximum(m_col, m_gray)

    out = orig_img.convert("RGBA")
    out.putalpha(Image.fromarray(m_fused))
    return out


class BGRemoverServer(SimpleHTTPRequestHandler):
    def do_GET(self):
        global last_activity_time, has_received_first_request
        last_activity_time = time.time()
        has_received_first_request = True

        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/assets/icon.png":
            if os.path.exists(ICON_PNG):
                with open(ICON_PNG, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
        elif parsed.path == "/api/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(AVAILABLE_MODELS).encode("utf-8"))
        elif parsed.path == "/api/ping":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"pong")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global last_activity_time, has_received_first_request
        last_activity_time = time.time()
        has_received_first_request = True

        parsed = urlparse(self.path)
        if parsed.path == "/api/remove":
            qs = parse_qs(parsed.query)
            model_name = qs.get("model", ["u2net"])[0]
            trim_px = int(qs.get("trim", ["1"])[0])
            decontam = qs.get("decontaminate", ["true"])[0].lower() == "true"
            recover_holes = qs.get("recover_holes", ["true"])[0].lower() == "true"

            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Empty image payload")
                return

            input_bytes = self.rfile.read(length)

            try:
                from PIL import Image, ImageFilter
                import numpy as np

                session = get_session(model_name)
                # post_process_mask=False preserves sub-pixel anti-aliasing (never binarize)
                output_bytes = remove(
                    input_bytes,
                    session=session,
                    post_process_mask=False,
                    decontaminate=decontam
                )

                orig_img = Image.open(io.BytesIO(input_bytes)).convert("RGB")

                # Dual-pass luminance saliency: AI natively recognizes camouflaged parts
                if recover_holes:
                    cutout_img = fuse_dual_pass_saliency(input_bytes, orig_img, session)
                else:
                    cutout_img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")

                if trim_px > 0:
                    r, g, b, a = cutout_img.split()
                    a_arr = np.array(a).astype(np.float32) / 255.0

                    # Smoothly contract faint edge bleed without binarizing
                    cutoff = 0.05 * trim_px
                    a_clean = np.clip((a_arr - cutoff) / (1.0 - cutoff), 0.0, 1.0)
                    a_clean = np.power(a_clean, 1.0 + 0.12 * trim_px)
                    a_img = Image.fromarray((a_clean * 255.0).astype(np.uint8))

                    # Sub-pixel anti-alias feathering to ensure silky-smooth curvature
                    a_img = a_img.filter(ImageFilter.GaussianBlur(0.35))

                    cutout_img = Image.merge("RGBA", (r, g, b, a_img))

                out_buf = io.BytesIO()
                cutout_img.save(out_buf, format="PNG")
                output_bytes = out_buf.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(output_bytes)))
                self.end_headers()
                self.wfile.write(output_bytes)
            except Exception as e:
                err_msg = str(e).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(err_msg)))
                self.end_headers()
                self.wfile.write(err_msg)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def find_open_port(start_port=7860):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

def wait_for_server(port, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.05)
    return False

def launch_app_window(url):
    profile_dir = os.path.join(APP_DIR, "profile")
    os.makedirs(profile_dir, exist_ok=True)

    # Edge in standalone app window mode with isolated profile
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in edge_paths:
        if os.path.exists(p):
            cmd = [
                p,
                f"--app={url}",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            proc = subprocess.Popen(cmd)
            proc.wait()
            return

    # Chrome fallback
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in chrome_paths:
        if os.path.exists(p):
            cmd = [
                p,
                f"--app={url}",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            proc = subprocess.Popen(cmd)
            proc.wait()
            return

    webbrowser.open(url)

def watchdog_monitor(server):
    # Auto-shutdown server 8s after browser window closes (when pings stop)
    while True:
        time.sleep(2)
        if has_received_first_request:
            idle_seconds = time.time() - last_activity_time
            if idle_seconds > 8:
                try:
                    server.shutdown()
                except Exception:
                    pass
                sys.exit(0)

if __name__ == "__main__":
    PORT = find_open_port(7860)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), BGRemoverServer)
    url = f"http://127.0.0.1:{PORT}"

    # Start server thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Wait until server socket is accepting connections
    wait_for_server(PORT, timeout=5.0)

    # Start watchdog to terminate server when window closes
    watchdog_thread = threading.Thread(target=watchdog_monitor, args=(server,), daemon=True)
    watchdog_thread.start()

    # Launch standalone application window
    launch_app_window(url)

    # Clean shutdown
    try:
        server.shutdown()
    except Exception:
        pass
    sys.exit(0)
