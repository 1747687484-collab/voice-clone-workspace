#!/usr/bin/env python3
"""Local AI cover workspace helper.

This script does not replace Applio/RVC. It organizes the repeatable parts
around them: dependency checks, voice dataset preparation, vocal separation
handoff, stem importing, and final mixing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}

DIRECTORIES = [
    "recordings/raw",
    "recordings/clean",
    "datasets",
    "songs/originals",
    "songs/stems",
    "songs/converted_vocals",
    "models",
    "outputs",
    "reports",
    "logs",
    "tools",
]

DEFAULT_CONFIG = {
    "workspace_version": 1,
    "applio": {
        "install_path": "",
        "notes": "Install Applio separately, then train/infer from its GUI.",
    },
    "audio": {
        "sample_rate": 48000,
        "dataset_segment_seconds": 12,
        "dataset_loudness_i": -20,
        "mix_loudness_i": -16,
    },
    "rvc": {
        "recommended_f0_method": "rmvpe",
        "recommended_sample_rate": "48k",
        "recommended_first_batch_size": "6-8 for RTX 4060 Laptop 8GB",
    },
}


class AppError(RuntimeError):
    """Expected user-facing command failure."""


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def print_heading(title: str) -> None:
    print(f"\n== {title} ==")


def safe_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned.strip("._ ")
    return cleaned or "untitled"


def ensure_workspace() -> None:
    for item in DIRECTORIES:
        (ROOT / item).mkdir(parents=True, exist_ok=True)


def write_default_config(force: bool = False) -> Path:
    config_path = ROOT / "config.json"
    if config_path.exists() and not force:
        return config_path
    config_path.write_text(
        json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path


def load_config() -> dict:
    config_path = ROOT / "config.json"
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AppError(f"config.json is not valid JSON: {exc}") from exc
    merged = DEFAULT_CONFIG.copy()
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def tool_path(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct

    env_name = f"{name.upper()}_PATH"
    env_value = os.environ.get(env_name)
    if env_value and Path(env_value).exists():
        return str(Path(env_value).resolve())

    ffmpeg_bin = os.environ.get("FFMPEG_BIN")
    if ffmpeg_bin:
        candidate = Path(ffmpeg_bin) / exe_name(name)
        if candidate.exists():
            return str(candidate.resolve())

    if name.lower() in {"ffmpeg", "ffprobe", "ffplay"}:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            package_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
            if package_root.exists():
                matches = sorted(package_root.rglob(exe_name(name)), key=lambda item: item.stat().st_mtime, reverse=True)
                if matches:
                    return str(matches[0].resolve())
    return None


def exe_name(name: str) -> str:
    return name if name.lower().endswith(".exe") or os.name != "nt" else f"{name}.exe"


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    label: str | None = None,
) -> None:
    if label:
        print(f"\n# {label}")
    print(" ".join(quote_arg(part) for part in command))
    if dry_run:
        return
    try:
        subprocess.run(command, cwd=str(cwd or ROOT), check=True)
    except FileNotFoundError as exc:
        raise AppError(f"Command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise AppError(f"Command failed with exit code {exc.returncode}") from exc


def capture_command(command: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return False, ""
    return completed.returncode == 0, completed.stdout.strip()


def quote_arg(value: str) -> str:
    if not value:
        return '""'
    if re.search(r"\s", value):
        return f'"{value}"'
    return value


def require_ffmpeg() -> str:
    path = tool_path("ffmpeg")
    if not path:
        raise AppError(
            "ffmpeg is required for this command. Install it first, then reopen "
            "PowerShell. Example: winget install Gyan.FFmpeg"
        )
    return path


def find_audio_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = [
            item
            for item in sorted(input_path.rglob("*"))
            if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS
        ]
    else:
        raise AppError(f"Input path does not exist: {input_path}")

    if not files:
        raise AppError(f"No audio files found in: {input_path}")
    return files


def write_manifest(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def cmd_init(args: argparse.Namespace) -> None:
    ensure_workspace()
    config_path = write_default_config(force=args.force_config)
    for directory in DIRECTORIES:
        gitkeep = ROOT / directory / ".gitkeep"
        gitkeep.touch(exist_ok=True)
    print_heading("Workspace ready")
    print(f"Root: {ROOT}")
    print(f"Config: {rel(config_path)}")
    print("Next: put your raw voice recordings in recordings/raw/")


def cmd_doctor(_: argparse.Namespace) -> None:
    config = load_config()
    print_heading("System")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Workspace: {ROOT}")

    print_heading("Required audio tools")
    ffmpeg = tool_path("ffmpeg")
    ffprobe = tool_path("ffprobe")
    print_status("ffmpeg", ffmpeg, "Install with: winget install Gyan.FFmpeg")
    print_status("ffprobe", ffprobe, "Usually included with ffmpeg")

    print_heading("GPU")
    ok, output = capture_command(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    if ok and output:
        print(output)
    else:
        print("nvidia-smi not available. Training can still run on CPU, but it will be slow.")

    print_heading("Optional separation tools")
    ok, _ = capture_command([sys.executable, "-m", "demucs", "--help"])
    print_status(
        "demucs",
        "available via python -m demucs" if ok else None,
        "Optional. Use Applio UVR GUI instead if you prefer.",
    )

    print_heading("Applio/RVC")
    applio_path = str(config.get("applio", {}).get("install_path", "")).strip()
    if applio_path:
        path = resolve_path(applio_path)
        print_status("Applio path", str(path) if path.exists() else None, "Update config.json if this moved.")
    else:
        print("Applio install_path is empty in config.json. That is fine if you use Applio manually.")


def print_status(name: str, value: str | None, hint: str) -> None:
    if value:
        print(f"[OK] {name}: {value}")
    else:
        print(f"[MISSING] {name}: {hint}")


def cmd_make_dataset(args: argparse.Namespace) -> None:
    config = load_config()
    ffmpeg = require_ffmpeg()
    input_path = resolve_path(args.input)
    files = find_audio_files(input_path)
    voice_name = safe_name(args.name)
    dataset_dir = ROOT / "datasets" / voice_name
    raw_dir = dataset_dir / "raw"
    clean_dir = dataset_dir / "clean"
    segments_dir = dataset_dir / "segments"
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)

    sample_rate = args.sample_rate or int(config["audio"]["sample_rate"])
    segment_seconds = args.segment_seconds or int(config["audio"]["dataset_segment_seconds"])
    loudness_i = args.loudness_i if args.loudness_i is not None else int(config["audio"]["dataset_loudness_i"])
    manifest_rows: list[dict[str, str]] = []

    print_heading(f"Preparing dataset: {voice_name}")
    for index, source in enumerate(files, start=1):
        stem = safe_name(source.stem)
        raw_target = raw_dir / f"{index:03d}_{stem}{source.suffix.lower()}"
        clean_target = clean_dir / f"{index:03d}_{stem}.wav"
        if not args.dry_run:
            shutil.copy2(source, raw_target)

        filters = [f"highpass=f=60", f"loudnorm=I={loudness_i}:TP=-1.5:LRA=11"]
        if args.trim_silence:
            filters.insert(
                0,
                "silenceremove=start_periods=1:start_duration=0.15:start_threshold=-45dB:"
                "stop_periods=-1:stop_duration=0.25:stop_threshold=-45dB",
            )

        run_command(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-af",
                ",".join(filters),
                str(clean_target),
            ],
            dry_run=args.dry_run,
            label=f"Clean {source.name}",
        )

        segment_pattern = segments_dir / f"{index:03d}_{stem}_%03d.wav"
        run_command(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(clean_target),
                "-f",
                "segment",
                "-segment_time",
                str(segment_seconds),
                "-reset_timestamps",
                "1",
                "-c",
                "copy",
                str(segment_pattern),
            ],
            dry_run=args.dry_run,
            label=f"Split {clean_target.name}",
        )

        manifest_rows.append(
            {
                "source": str(source),
                "raw_copy": rel(raw_target),
                "clean_wav": rel(clean_target),
                "segments_glob": rel(segment_pattern),
            }
        )

    if not args.dry_run:
        write_manifest(dataset_dir / "manifest.csv", manifest_rows)
    print_heading("Dataset paths for Applio")
    print(f"Use this as the training dataset folder: {segments_dir.resolve()}")
    print("Recommended Applio settings: sample rate 48k, f0 method RMVPE, batch size 6-8 first.")


def cmd_trim_test(args: argparse.Namespace) -> None:
    ffmpeg = require_ffmpeg()
    source = resolve_path(args.input)
    if not source.exists():
        raise AppError(f"Input file does not exist: {source}")
    name = safe_name(args.name or source.stem)
    output = resolve_path(args.output) if args.output else ROOT / "songs" / "originals" / f"{name}_test.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            args.start,
            "-i",
            str(source),
            "-t",
            str(args.duration),
            "-acodec",
            "pcm_s16le",
            str(output),
        ],
        dry_run=args.dry_run,
        label="Create short test clip",
    )
    print(f"Test clip: {output.resolve()}")


def cmd_separate(args: argparse.Namespace) -> None:
    source = resolve_path(args.input)
    if not source.exists():
        raise AppError(f"Input file does not exist: {source}")
    song_name = safe_name(args.name or source.stem)
    target_dir = ROOT / "songs" / "stems" / song_name
    demucs_out = ROOT / "songs" / "stems" / "_demucs_work"
    target_dir.mkdir(parents=True, exist_ok=True)
    demucs_out.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-n",
        args.model,
        "-o",
        str(demucs_out),
    ]
    if args.device:
        command.extend(["--device", args.device])
    command.append(str(source))

    run_command(command, dry_run=args.dry_run, label="Separate vocals with Demucs")

    if args.dry_run:
        print("Dry run only. No stems were copied.")
        return

    produced_dir = demucs_out / args.model / source.stem
    vocals = produced_dir / "vocals.wav"
    instrumental = produced_dir / "no_vocals.wav"
    if not vocals.exists() or not instrumental.exists():
        raise AppError(
            "Demucs finished, but expected stems were not found. "
            f"Look under: {produced_dir}"
        )
    shutil.copy2(vocals, target_dir / "vocals.wav")
    shutil.copy2(instrumental, target_dir / "instrumental.wav")
    print_heading("Stems ready")
    print(f"Vocals for Applio inference: {(target_dir / 'vocals.wav').resolve()}")
    print(f"Instrumental for final mix: {(target_dir / 'instrumental.wav').resolve()}")


def cmd_import_stems(args: argparse.Namespace) -> None:
    ffmpeg = require_ffmpeg()
    song_name = safe_name(args.name)
    target_dir = ROOT / "songs" / "stems" / song_name
    target_dir.mkdir(parents=True, exist_ok=True)
    vocals = resolve_path(args.vocals)
    instrumental = resolve_path(args.instrumental)
    if not vocals.exists():
        raise AppError(f"Vocals file does not exist: {vocals}")
    if not instrumental.exists():
        raise AppError(f"Instrumental file does not exist: {instrumental}")
    convert_audio(ffmpeg, vocals, target_dir / "vocals.wav", args.dry_run, "Import vocals stem")
    convert_audio(ffmpeg, instrumental, target_dir / "instrumental.wav", args.dry_run, "Import instrumental stem")
    print_heading("Imported stems")
    print(f"Vocals for Applio inference: {(target_dir / 'vocals.wav').resolve()}")
    print(f"Instrumental for final mix: {(target_dir / 'instrumental.wav').resolve()}")


def convert_audio(ffmpeg: str, source: Path, target: Path, dry_run: bool, label: str) -> None:
    run_command(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-ar",
            "48000",
            "-acodec",
            "pcm_s16le",
            str(target),
        ],
        dry_run=dry_run,
        label=label,
    )


def cmd_mix(args: argparse.Namespace) -> None:
    config = load_config()
    ffmpeg = require_ffmpeg()
    song_name = safe_name(args.name)
    vocals = resolve_path(args.vocals)
    instrumental = resolve_path(args.instrumental) if args.instrumental else ROOT / "songs" / "stems" / song_name / "instrumental.wav"
    output = resolve_path(args.output) if args.output else ROOT / "outputs" / f"{song_name}_mix.wav"
    if not vocals.exists():
        raise AppError(f"Converted vocal file does not exist: {vocals}")
    if not instrumental.exists():
        raise AppError(f"Instrumental file does not exist: {instrumental}")
    output.parent.mkdir(parents=True, exist_ok=True)

    offset_ms = int(args.vocal_offset_ms)
    if offset_ms >= 0:
        vocal_chain = f"[0:a]adelay={offset_ms}:all=1,volume={args.vocal_gain_db}dB[v]"
        inst_chain = f"[1:a]volume={args.instrumental_gain_db}dB[i]"
    else:
        vocal_chain = f"[0:a]volume={args.vocal_gain_db}dB[v]"
        inst_chain = f"[1:a]adelay={abs(offset_ms)}:all=1,volume={args.instrumental_gain_db}dB[i]"

    loudness_i = args.loudness_i if args.loudness_i is not None else int(config["audio"]["mix_loudness_i"])
    filter_complex = (
        f"{vocal_chain};"
        f"{inst_chain};"
        f"[v][i]amix=inputs=2:duration=longest:dropout_transition=0,"
        f"alimiter=limit=0.98,loudnorm=I={loudness_i}:TP=-1.5:LRA=11[out]"
    )
    run_command(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(vocals),
            "-i",
            str(instrumental),
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            str(output),
        ],
        dry_run=args.dry_run,
        label="Mix converted vocal with instrumental",
    )
    print(f"Final mix: {output.resolve()}")


def cmd_checklist(args: argparse.Namespace) -> None:
    voice_name = safe_name(args.voice)
    song_name = safe_name(args.song)
    report_dir = ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{song_name}_applio_steps.md"
    dataset_segments = ROOT / "datasets" / voice_name / "segments"
    model_dir = ROOT / "models" / voice_name
    stems_dir = ROOT / "songs" / "stems" / song_name
    converted_target = ROOT / "songs" / "converted_vocals" / f"{song_name}_{voice_name}.wav"
    mix_target = ROOT / "outputs" / f"{song_name}_mix.wav"

    content = f"""# Applio/RVC Manual Steps

Voice model name: `{voice_name}`
Song name: `{song_name}`

## 1. Train your voice model in Applio

- Dataset folder: `{dataset_segments.resolve()}`
- Recommended sample rate: `48k`
- Recommended f0 method: `RMVPE`
- First batch size to try on RTX 4060 Laptop 8GB: `6-8`
- Save or copy final model files here: `{model_dir.resolve()}`

Expected model files:

- `{(model_dir / (voice_name + ".pth")).resolve()}`
- `{(model_dir / (voice_name + ".index")).resolve()}`

## 2. Convert the original vocal

- Input vocal stem: `{(stems_dir / "vocals.wav").resolve()}`
- Output converted vocal target: `{converted_target.resolve()}`

Start with these inference choices:

- f0 method: `RMVPE`
- Index/search ratio: `0.5`
- Protect consonants: `0.33`
- Clean audio: on if the separated vocal has artifacts

## 3. Mix the final cover

Run this after Applio exports the converted vocal:

```powershell
python .\\voice_cover.py mix --name "{song_name}" --vocals "{converted_target.resolve()}"
```

Expected final mix:

- `{mix_target.resolve()}`
"""
    output.write_text(content, encoding="utf-8")
    print(f"Checklist written: {output.resolve()}")


def cmd_show(_: argparse.Namespace) -> None:
    ensure_workspace()
    print_heading("Workspace map")
    for directory in DIRECTORIES:
        print(f"- {rel(ROOT / directory)}")
    print_heading("Fast path")
    print("1. Put your voice files in recordings/raw/")
    print("2. python .\\voice_cover.py make-dataset recordings/raw --name my_voice")
    print("3. Train in Applio using datasets/my_voice/segments/")
    print("4. Separate a song with Applio UVR or: python .\\voice_cover.py separate songs/originals/song.wav --name song")
    print("5. Convert songs/stems/song/vocals.wav in Applio with your model")
    print("6. python .\\voice_cover.py mix --name song --vocals songs/converted_vocals/song_my_voice.wav")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local workspace helper for RVC/Applio AI covers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create the project folders and config.json.")
    init.add_argument("--force-config", action="store_true", help="Overwrite config.json with defaults.")
    init.set_defaults(func=cmd_init)

    doctor = subparsers.add_parser("doctor", help="Check local tools needed by the workflow.")
    doctor.set_defaults(func=cmd_doctor)

    show = subparsers.add_parser("show", help="Print the workspace map and fast path.")
    show.set_defaults(func=cmd_show)

    dataset = subparsers.add_parser("make-dataset", help="Clean and split voice recordings for Applio training.")
    dataset.add_argument("input", help="Audio file or folder containing your raw voice recordings.")
    dataset.add_argument("--name", default="my_voice", help="Voice model/dataset name.")
    dataset.add_argument("--sample-rate", type=int, default=None, help="Output sample rate.")
    dataset.add_argument("--segment-seconds", type=int, default=None, help="Chunk length for training clips.")
    dataset.add_argument("--loudness-i", type=int, default=None, help="Integrated loudness target for voice clips.")
    dataset.add_argument("--trim-silence", action="store_true", help="Try to remove leading/trailing silence.")
    dataset.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    dataset.set_defaults(func=cmd_make_dataset)

    trim = subparsers.add_parser("trim-test", help="Cut a 30-60 second test clip from a song.")
    trim.add_argument("input", help="Source song file.")
    trim.add_argument("--name", default=None, help="Output base name.")
    trim.add_argument("--start", default="00:00:00", help="Start time, for example 00:01:20.")
    trim.add_argument("--duration", type=int, default=60, help="Clip duration in seconds.")
    trim.add_argument("--output", default=None, help="Optional output path.")
    trim.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    trim.set_defaults(func=cmd_trim_test)

    separate = subparsers.add_parser("separate", help="Separate vocals/instrumental with Demucs if installed.")
    separate.add_argument("input", help="Song file to separate.")
    separate.add_argument("--name", default=None, help="Song workspace name.")
    separate.add_argument("--model", default="htdemucs", help="Demucs model name.")
    separate.add_argument("--device", default=None, help="Demucs device, e.g. cuda or cpu.")
    separate.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    separate.set_defaults(func=cmd_separate)

    import_stems = subparsers.add_parser("import-stems", help="Import stems exported by UVR/Applio into this workspace.")
    import_stems.add_argument("--name", required=True, help="Song workspace name.")
    import_stems.add_argument("--vocals", required=True, help="Path to vocal stem.")
    import_stems.add_argument("--instrumental", required=True, help="Path to instrumental/accompaniment stem.")
    import_stems.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    import_stems.set_defaults(func=cmd_import_stems)

    mix = subparsers.add_parser("mix", help="Mix converted vocals with the instrumental stem.")
    mix.add_argument("--name", required=True, help="Song workspace name.")
    mix.add_argument("--vocals", required=True, help="Converted vocal exported by Applio/RVC.")
    mix.add_argument("--instrumental", default=None, help="Instrumental stem. Defaults to songs/stems/<name>/instrumental.wav.")
    mix.add_argument("--output", default=None, help="Output mix path.")
    mix.add_argument("--vocal-gain-db", type=float, default=0.0, help="Vocal gain in dB before mixing.")
    mix.add_argument("--instrumental-gain-db", type=float, default=0.0, help="Instrumental gain in dB before mixing.")
    mix.add_argument("--vocal-offset-ms", type=int, default=0, help="Delay vocals if positive, instrumental if negative.")
    mix.add_argument("--loudness-i", type=int, default=None, help="Final integrated loudness target.")
    mix.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    mix.set_defaults(func=cmd_mix)

    checklist = subparsers.add_parser("checklist", help="Write a per-song Applio manual checklist.")
    checklist.add_argument("--voice", default="my_voice", help="Voice model name.")
    checklist.add_argument("--song", required=True, help="Song workspace name.")
    checklist.set_defaults(func=cmd_checklist)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except AppError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
