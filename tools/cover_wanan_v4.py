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
        
    converted_vocals_path = WORKSPACE / "songs" / "converted_vocals" / f"{song_name}_{MODEL_NAME}_crepe.wav"
    
    # 1. Run Applio Inference with CREPE and LOW index rate
    print(f"=== Starting Inference for {song_name} (CREPE + Low Index) ===", flush=True)
    infer_cmd = [
        str(PYTHON_EXE), str(CORE_PY), "infer",
        "--f0_method", "crepe",  # CREPE is the most robust F0 algorithm for difficult pitches
        "--pth_path", str(MODEL_PATH),
        "--index_path", str(INDEX_PATH),
        "--input_path", str(vocals_path),
        "--output_path", str(converted_vocals_path),
        "--export_format", "WAV",
        "--index_rate", "0.1",  # CRITICAL: Low index allows the model to sing high notes not present in training data
        "--protect", "0.2",     # Lower protection so it doesn't accidentally treat high falsetto as unvoiced breath
        "--pitch", "0"
    ]
    
    subprocess.run(infer_cmd, cwd=str(APPLIO_DIR), check=True)
    
    # 2. Run Custom Mix (same as V3 for high volume)
    print(f"=== Starting Mix for {song_name} ===", flush=True)
    final_output = WORKSPACE / "outputs" / f"{song_name}_V4_高音终极突破版.wav"
    
    ffmpeg_exe = r"C:\Users\kbsama\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
    
    v_fx = "equalizer=f=300:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1.5:g=3,equalizer=f=8000:t=q:w=1:g=3,aecho=0.8:0.75:60|80:0.4|0.25,adelay=0:all=1,volume=5.0dB"
    i_fx = "volume=-1.5dB,equalizer=f=2000:t=q:w=2:g=-2"
    
    filter_complex = f"[0:a]{v_fx}[v];[1:a]{i_fx}[i];[v][i]amix=inputs=2:duration=longest:dropout_transition=0,alimiter=limit=0.98,loudnorm=I=-14:TP=-1.5:LRA=11[out]"
    
    mix_cmd = [
        ffmpeg_exe, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(converted_vocals_path),
        "-i", str(instrumental_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        str(final_output)
    ]
    
    subprocess.run(mix_cmd, check=True)
    
    print("\n=== SUCCESS ===")
    print(f"The final cover song has been generated at: {final_output}")

if __name__ == "__main__":
    main()
