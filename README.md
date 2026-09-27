# AveeVisualizer-CLI

Independent command-line audio-reactive visualizer renderer inspired by an Avee-style scene workflow.

This project is designed for batch production: put music, backgrounds, and logos in their folders, then select **Manual** or **Automatic / Sequential** and render synchronized MP4 visualizers with FFmpeg.

> Independent renderer; not an official Avee Player product. Avee-specific behavior is approximated with native FFT and beat-reactive rendering.

## Features

- Two modes only: Manual and Automatic / Sequential
- Music/, BackGround/, Logo/, and Output/ folder workflow
- One background or logo automatically becomes the default
- Natural filename sorting
- Persistent sequential rotation using .state.json
- FFT-based circular spectrum synchronized to audio
- Beat-reactive logo pulse and camera shake
- Multi-layer circular bars based on scene parameters
- H.264 + AAC output through FFmpeg
- Windows, Linux, and macOS support

## Requirements

Python 3.10+, FFmpeg in PATH, NumPy, and Pillow.

    ffmpeg -version

## Install on Windows

    git clone https://github.com/JaGir9/AveeVisualizer-CLI.git
    cd AveeVisualizer-CLI
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python main.py

## Install on Linux/macOS

    git clone https://github.com/JaGir9/AveeVisualizer-CLI.git
    cd AveeVisualizer-CLI
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    chmod +x run.sh
    ./run.sh

## Usage

Put audio in Music/, backgrounds in BackGround/, and logos in Logo/. Then run:

    python main.py

Menu:

    [1] Manual
    [2] Otomatis / Berurutan

Manual lets you select media yourself. If Background or Logo contains exactly one supported image, it is selected automatically.

Automatic / Sequential renders music in natural filename order and advances Background and Logo sequentially. State advances only after a successful render.

Reset rotation:

    python main.py --reset-state

## Render options

Default: 1920x1080, 30 FPS, H.264 CRF 18, AAC 320 kbps.

    python main.py --fps 60
    python main.py --width 3840 --height 2160 --fps 60
    python main.py --preset veryfast --crf 20

## Audio reaction

FFmpeg decodes audio to mono PCM. The renderer performs FFT analysis per video frame, maps frequency energy into logarithmic bands, and drives the circular spectrum from those bands. Transient energy controls beat reactions such as logo pulse and camera movement.

scene.json supplies the main spectrum and layout parameters. Avee-only internal effects are approximated renderer-side so the CLI does not depend on Android or the Avee engine.

The included scene.json is a compact CLI-compatible representation of the relevant parameters extracted from the working theme. A compatible full Avee scene can also be used.

## License

MIT. See LICENSE.
