import os
import sys
import subprocess
import math
from pathlib import Path
from download_song import download_song

WORKSPACE = Path(r"C:\Users\kbsama\Desktop\声音clone")
APPLIO_DIR = Path(r"C:\Applio")
PYTHON_EXE = APPLIO_DIR / "env" / "python.exe"
CORE_PY = APPLIO_DIR / "core.py"
MODEL_NAME = "kbsama_v2"
MODEL_PATH = WORKSPACE / "models" / f"{MODEL_NAME}.pth"
INDEX_PATH = WORKSPACE / "models" / f"{MODEL_NAME}.index"
FFMPEG_EXE = r"C:\Users\kbsama\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"

def clean_filename(name):
    # Keep alphanumeric characters and Chinese characters
    clean = "".join([c for c in name if c.isalnum() or c in (' ', '_', '-')]).strip()
    return clean.replace(' ', '_')

def run_auto_cover(query, pitch_shift=0):
    clean_name = clean_filename(query)
    
    # 1. Download
    original_wav_path = download_song(query, f"{clean_name}.wav")
    if not original_wav_path or not original_wav_path.exists():
        print(f"Error: Failed to download song for query '{query}'")
        return
        
    # 2. Extract stems
    print(f"\n=== Step 2: Extracting Vocals and Instrumental Stems ===", flush=True)
    extract_script = WORKSPACE / "tools" / "extract_song.py"
    subprocess.run([sys.executable, str(extract_script), str(original_wav_path)], check=True)
    
    stems_dir = WORKSPACE / "songs" / "stems" / clean_name
    vocals_path = stems_dir / "vocals.wav"
    instrumental_path = stems_dir / "instrumental.wav"
    
    if not vocals_path.exists() or not instrumental_path.exists():
        print("Error: Stems separation failed.")
        return
        
    # 3. Handle Pitch Shift for Instrumental
    shifted_instrumental_path = instrumental_path
    if pitch_shift != 0:
        print(f"\n=== Step 3: Pitch shifting Instrumental by {pitch_shift} semitones ===", flush=True)
        shifted_instrumental_path = stems_dir / f"instrumental_shifted_{pitch_shift}.wav"
        if not shifted_instrumental_path.exists():
            ratio = math.pow(2, pitch_shift / 12.0)
            shift_inst_cmd = [
                FFMPEG_EXE, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(instrumental_path),
                "-af", f"rubberband=pitch={ratio:.7f}",
                str(shifted_instrumental_path)
            ]
            subprocess.run(shift_inst_cmd, check=True)
        else:
            print("Shifted instrumental already exists.")
            
    # 4. RVC Voice Conversion
    print(f"\n=== Step 4: Converting Vocals to AI Voice (Pitch Shift: {pitch_shift}) ===", flush=True)
    converted_vocals_path = WORKSPACE / "songs" / "converted_vocals" / f"{clean_name}_{MODEL_NAME}_shifted_{pitch_shift}.wav"
    converted_vocals_path.parent.mkdir(parents=True, exist_ok=True)
    
    infer_cmd = [
        str(PYTHON_EXE), str(CORE_PY), "infer",
        "--f0_method", "rmvpe",
        "--pth_path", str(MODEL_PATH),
        "--index_path", str(INDEX_PATH),
        "--input_path", str(vocals_path),
        "--output_path", str(converted_vocals_path),
        "--export_format", "WAV",
        "--index_rate", "0.2",   
        "--protect", "0.5",      
        "--pitch", str(pitch_shift)
    ]
    subprocess.run(infer_cmd, cwd=str(APPLIO_DIR), check=True)
    
    # 5. Studio-grade Mix and Master
    print(f"\n=== Step 5: Mixing and Mastering Final Cover ===", flush=True)
    final_output = WORKSPACE / "outputs" / f"{clean_name}_完美AI翻唱版.wav"
    final_output.parent.mkdir(parents=True, exist_ok=True)
    
    v_fx = "equalizer=f=300:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1.5:g=3,equalizer=f=8000:t=q:w=1:g=3,aecho=0.8:0.75:60|80:0.4|0.25,adelay=0:all=1,volume=5.0dB"
    i_fx = "volume=-1.5dB,equalizer=f=2000:t=q:w=2:g=-2"
    
    filter_complex = f"[0:a]{v_fx}[v];[1:a]{i_fx}[i];[v][i]amix=inputs=2:duration=longest:dropout_transition=0,alimiter=limit=0.98,loudnorm=I=-14:TP=-1.5:LRA=11[out]"
    
    mix_cmd = [
        FFMPEG_EXE, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(converted_vocals_path),
        "-i", str(shifted_instrumental_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        str(final_output)
    ]
    
    subprocess.run(mix_cmd, check=True)
    print(f"\n======================================")
    print(f"=== SUCCESS: AI COVER GENERATED! ===")
    print(f"File saved at: {final_output}")
    print(f"======================================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_cover.py <search_query> [pitch_shift]")
        sys.exit(1)
        
    search_q = sys.argv[1]
    p_shift = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    run_auto_cover(search_q, p_shift)
