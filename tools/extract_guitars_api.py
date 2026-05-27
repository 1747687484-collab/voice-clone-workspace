import os
import shutil
import subprocess
from pathlib import Path
import torch
import soundfile as sf
import torchaudio
import warnings

# Suppress torchaudio warnings about missing ffmpeg
warnings.filterwarnings("ignore")

from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import convert_audio

ROOT = Path('c:/Users/kbsama/Desktop/声音clone')
INPUT_DIR = ROOT / 'recordings/with_guitar'
RAW_DIR = ROOT / 'recordings/raw'

RAW_DIR.mkdir(parents=True, exist_ok=True)
audio_files = [f for f in INPUT_DIR.glob('*') if f.suffix.lower() in ['.m4a', '.wav', '.mp3']]

print("Loading Demucs model...")
model = get_model('htdemucs')
model.eval()

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

print(f"Using device: {device}")
print(f"Found {len(audio_files)} files to process.")

for idx, f in enumerate(audio_files, 1):
    print(f"\n[{idx}/{len(audio_files)}] Processing {f.name}...")
    
    # 1. Convert to WAV using FFmpeg subprocess to avoid torchaudio backend issues
    temp_wav = INPUT_DIR / f"temp_{f.stem}.wav"
    ffmpeg = r"C:\Users\kbsama\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(f), "-ar", str(model.samplerate), str(temp_wav)], check=True)
    
    # 2. Load WAV (this will use soundfile backend which is safe)
    import soundfile as sf
    wav_np, sr = sf.read(str(temp_wav), dtype='float32')
    wav_np = wav_np.T
    if len(wav_np.shape) == 1:
        wav_np = wav_np[None, :]
    wav = torch.from_numpy(wav_np)
    wav = convert_audio(wav, sr, model.samplerate, model.audio_channels)
    
    # Add batch dimension
    wav = wav.unsqueeze(0).to(device)
    
    # Apply model
    with torch.no_grad():
        sources = apply_model(model, wav, shifts=1, split=True, overlap=0.25)[0]
    
    # Sources correspond to model.sources
    vocal_idx = model.sources.index('vocals')
    vocal_tensor = sources[vocal_idx].cpu()
    
    # Save with soundfile
    target_name = f"extracted_{f.stem}.wav"
    target_path = RAW_DIR / target_name
    
    vocal_np = vocal_tensor.numpy().T
    sf.write(str(target_path), vocal_np, model.samplerate)
    print(f"-> Successfully extracted vocals to {target_name}")
    
    # Cleanup temp
    temp_wav.unlink(missing_ok=True)

print("\nAll extractions complete! You can now run make-dataset.")
