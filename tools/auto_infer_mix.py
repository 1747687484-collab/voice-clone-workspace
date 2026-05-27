import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(r"C:\Users\kbsama\Desktop\声音clone")
APPLIO_DIR = Path(r"C:\Applio")
PYTHON_EXE = APPLIO_DIR / "env" / "python.exe"
CORE_PY = APPLIO_DIR / "core.py"
MODEL_NAME = "kbsama_v2"
MODEL_PATH = WORKSPACE / "models" / f"{MODEL_NAME}.pth"
INDEX_PATH = WORKSPACE / "models" / f"{MODEL_NAME}.index"

def main():
    # Find the target song
    stems_dir = WORKSPACE / "songs" / "stems"
    valid_dirs = [d for d in stems_dir.iterdir() if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('_')]
    if not valid_dirs:
        print("No valid song stems found in songs/stems/")
        return
    
    valid_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True); target_dir = valid_dirs[0]
    song_name = target_dir.name
    vocals_path = target_dir / "vocals.wav"
    instrumental_path = target_dir / "instrumental.wav"
    
    if not vocals_path.exists():
        print(f"Error: {vocals_path} not found")
        return
        
    converted_vocals_path = WORKSPACE / "songs" / "converted_vocals" / f"{song_name}_{MODEL_NAME}.wav"
    
    # Run Applio Inference
    print(f"=== Starting Inference for {song_name} ===", flush=True)
    infer_cmd = [
        str(PYTHON_EXE), str(CORE_PY), "infer",
        "--f0_method", "rmvpe",
        "--pth_path", str(MODEL_PATH),
        "--index_path", str(INDEX_PATH),
        "--input_path", str(vocals_path),
        "--output_path", str(converted_vocals_path),
        "--export_format", "WAV",
        "--index_rate", "0.7",
        "--pitch", "0"
    ]
    
    print(f"Running: {' '.join(infer_cmd)}", flush=True)
    subprocess.run(infer_cmd, cwd=str(APPLIO_DIR), check=True)
    
    # Run Mix
    print(f"=== Starting Mix for {song_name} ===", flush=True)
    mix_cmd = [
        sys.executable, "voice_cover.py", "mix",
        "--name", song_name,
        "--vocals", str(converted_vocals_path),
        "--instrumental", str(instrumental_path),
        "--reverb", "medium",
        "--vocal-eq",
        "--vocal-gain-db", "2.0"
    ]
    
    print(f"Running: {' '.join(mix_cmd)}", flush=True)
    subprocess.run(mix_cmd, cwd=str(WORKSPACE), check=True)
    
    print("\n=== SUCCESS ===")
    print(f"The final cover song has been generated in: {WORKSPACE}/outputs/")

if __name__ == "__main__":
    main()
