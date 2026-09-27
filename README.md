# AveeVisualizer-CLI

Theme-driven CLI + local Web UI audio visualizer. Theme JSON is treated as a scene graph; Music, BackGround and Logo are user-replaceable media.

> Independent renderer, not an official Avee Player product. JSON structure and parameters are read directly. Avee internal engine/resources are reimplemented with compatible/equivalent behavior, so pixel-identical output with Avee itself is not guaranteed.

## Theme system

Themes are discovered recursively from `Themes/**/*.json`.

    Themes/
    ├── Default/
    │   └── scene.json
    ├── Theme-02/
    │   └── scene.json
    └── Theme-03/
        └── scene.json

If exactly one valid theme exists it is selected automatically. With two or more themes, the CLI automatically shows a numbered theme menu. To replace a single theme, replace `Themes/Default/scene.json`; no Python edit is required.

The included Default scene is the full original theme (9 compositions / 21 elements), not the previous compact scene.

## Supported scene features

The generic loader keeps the full JSON and inventories every element. The renderer currently implements all object types present in the bundled Default theme: `AudioProvider`, `Image`, `Bars`, `Particles`, `BlurEffect`, and `MotionBlurEffect`.

It resolves `composition:*` references recursively and implements beat/time measures used by the theme, including Beat, TotalTime, TotalTimeBackward, TotalTimeAndBeat, BeatRandomShake, BeatCamShakeMore/Less and ConstantShake. Theme values are evaluated at render time: Color/ColorTo and MeasureColorBlend, blend mode, opacity, position/scale/rotation and their measures, image blur, Bars height/delay/softness/segment colors, particle colors/speed/scale/count, BlurEffect and MotionBlurEffect parameters are read from the selected JSON rather than fixed to the bundled theme. It also provides procedural equivalents for required internal resources such as vignette and blurred-circle particles.

If a future theme contains a new `objType`, the CLI prints an explicit unsupported-type warning instead of silently pretending it was rendered. This makes theme changes data-driven while keeping unsupported Avee-specific behavior visible.

Background images tagged `BackGround` are overridden from `BackGround/`. Images tagged `Logo` are overridden from `Logo/`. Other scene elements/effects continue to come from the selected JSON.

## Media workflow

    Music/
    BackGround/
    Logo/
    Output/

Run:

    python main.py

Modes:

    [1] Manual
    [2] Otomatis / Berurutan

Orientation:

    [1] Horizontal / Landscape
    [2] Vertical / Portrait

Quality:

    [1] 480p
    [2] 720p HD
    [3] 1080p Full HD
    [4] 2K / 1440p QHD
    [5] 4K / 2160p UHD

## Local Web UI

Windows:

    run_web.bat

Linux/macOS:

    ./run_web.sh

The launcher starts a local-only server at `http://127.0.0.1:8080` and opens the default browser automatically. The Web UI uses the same Python theme/render engine as CLI mode.

Web controls include Theme, Music, Background, Logo, Landscape/Portrait, quality presets, fixed 30 FPS rendering, detected encoder information, live progress, current/total frame, render FPS, realtime multiplier, ETA, logs, cancel, and output download.

Quality presets:

    480p
    720p HD
    1080p Full HD
    2K / 1440p QHD
    4K / 2160p UHD

The renderer now caches completed compositions within each frame so repeated composition references do not redraw the same composition unnecessarily. BlurEffect also supports Avee-style `sourceCompositionIndex` references used by the bundled theme. These optimizations do not intentionally remove particles, bars, blur, motion blur, beat/shake reactions, transforms, colors, blending, or other supported theme behavior.

## Performance

At startup the CLI detects logical CPU resources and tests hardware H.264 encoders exposed by FFmpeg: NVIDIA NVENC, Intel Quick Sync, AMD AMF and Apple VideoToolbox, with libx264 fallback.

Progress is updated on one terminal line:

    Render  42% | 38.1 fps | 1.27x realtime

`x realtime` is measured performance, not a forced speed target.

## Install

Requires Python 3.10+ and FFmpeg in PATH.

    git clone https://github.com/JaGir9/AveeVisualizer-CLI.git
    cd AveeVisualizer-CLI
    python -m venv .venv

Windows:

    .venv\Scripts\activate
    pip install -r requirements.txt
    python main.py

Linux/macOS:

    source .venv/bin/activate
    pip install -r requirements.txt
    python main.py

Reset sequential rotation:

    python main.py --reset-state

## Compatibility note

A JSON file can describe the scene, but it does not contain Avee's proprietary rendering algorithms or original internal resource pixels. The project therefore uses independent equivalents. The theme remains the source for composition structure, parameters, media tags, audio settings, effect chain and reaction settings.

## License

MIT. See `LICENSE`.
