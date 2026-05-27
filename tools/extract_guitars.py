import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path('c:/Users/kbsama/Desktop/声音clone')
INPUT_DIR = ROOT / 'recordings/with_guitar'
RAW_DIR = ROOT / 'recordings/raw'
DEMUCS_OUT = ROOT / 'recordings/_demucs_guitar'

DEMUCS_OUT.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

audio_files = [f for f in INPUT_DIR.glob('*') if f.suffix.lower() in ['.m4a', '.wav', '.mp3']]

print(f"Found {len(audio_files)} files to process.")

for idx, f in enumerate(audio_files, 1):
    print(f"\n[{idx}/{len(audio_files)}] Processing {f.name}...")
    
    # Run Demucs
    cmd = [
        "python", "-m", "demucs",
        "--two-stems", "vocals",
        "-n", "htdemucs",
        "-o", str(DEMUCS_OUT),
        str(f)
    ]
    subprocess.run(cmd, check=True)
    
    # Find output vocals
    out_dir = DEMUCS_OUT / "htdemucs" / f.stem
    vocals = out_dir / "vocals.wav"
    
    if vocals.exists():
        target_name = f"extracted_{f.stem}.wav"
        target_path = RAW_DIR / target_name
        shutil.copy2(vocals, target_path)
        print(f"-> Successfully extracted vocals to {target_name}")
    else:
        print(f"-> ERROR: Failed to find vocals for {f.name}")

print("\nAll extractions complete! You can now run make-dataset.")
