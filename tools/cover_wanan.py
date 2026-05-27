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
    song_name = "晚安"
    
    vocals_path = WORKSPACE / "songs" / "stems" / song_name / "vocals.wav"
    instrumental_path = WORKSPACE / "songs" / "stems" / song_name / "instrumental.wav"
    
    if not vocals_path.exists():
        print(f"Error: {vocals_path} not found")
        return
        
    converted_vocals_path = WORKSPACE / "songs" / "converted_vocals" / f"{song_name}_{MODEL_NAME}_new.wav"
    
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
    
    subprocess.run(infer_cmd, cwd=str(APPLIO_DIR), check=True)
    
    # Run Mix
    print(f"=== Starting Mix for {song_name} ===", flush=True)
    final_output = WORKSPACE / "outputs" / f"{song_name}_V2_全新版.wav"
    
    # Since voice_cover.py hardcodes output to song_name + "_mix.wav", we will just rename it after
    mix_cmd = [
        sys.executable, "voice_cover.py", "mix",
        "--name", f"{song_name}_temp",
        "--vocals", str(converted_vocals_path),
        "--instrumental", str(instrumental_path),
        "--reverb", "medium",
        "--vocal-eq",
        "--vocal-gain-db", "2.0"
    ]
    
    subprocess.run(mix_cmd, cwd=str(WORKSPACE), check=True)
    
    # Rename output
    temp_output = WORKSPACE / "outputs" / f"{song_name}_temp_mix.wav"
    if temp_output.exists():
        if final_output.exists():
            final_output.unlink()
        temp_output.rename(final_output)
    
    print("\n=== SUCCESS ===")
    print(f"The final cover song has been generated at: {final_output}")

if __name__ == "__main__":
    main()
