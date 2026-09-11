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
    height: 520px;
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
    <label class="auto-copy-toggle" title="Automatically repair interior holes carved mistakenly (e.g. white shrimp meat, specular reflections)">
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

    <!-- Preview Stage -->
    <div class="preview-stage" id="previewStage">
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
  function setViewMode(mode) {
    currentViewMode = mode;
    document.querySelectorAll('.btn-group button').forEach(b => b.classList.remove('active'));

    if (mode === 'split') {
      document.getElementById('viewSplit').classList.add('active');
      sliderContainer.style.display = 'flex';
      sideContainer.style.display = 'none';
      sliderClipOriginal.style.display = 'block';
      sliderHandle.style.display = 'block';
      updateSlider(50);
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

    const targets = [cutoutLayer, sideCutoutWrapper, previewStage];
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
