import os
import sys
import subprocess
from pathlib import Path
import torch
import soundfile as sf
import torchaudio

# Suppress torchaudio warnings
import warnings
warnings.filterwarnings("ignore")

from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import convert_audio

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_song.py <path_to_song>")
        sys.exit(1)
        
    song_path = Path(sys.argv[1])
    song_name = song_path.stem
    
    workspace = Path(r"C:\Users\kbsama\Desktop\声音clone")
    out_dir = workspace / "songs" / "stems" / song_name
    out_dir.mkdir(parents=True, exist_ok=True)
    
    vocals_out = out_dir / "vocals.wav"
    inst_out = out_dir / "instrumental.wav"
    
    if vocals_out.exists() and inst_out.exists():
        print(f"Stems already exist in {out_dir}")
        return
        
    print(f"Loading Demucs model to separate {song_name}...")
    model = get_model('htdemucs')
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    
    # 1. Convert input to WAV using FFmpeg to avoid torchaudio backend crashes
    temp_wav = out_dir / f"temp_{song_name}.wav"
    ffmpeg = r"C:\Users\kbsama\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(song_path), "-ar", str(model.samplerate), str(temp_wav)], check=True)
    
    # 2. Load WAV with soundfile backend (safe)
    print("Reading audio data...")
    wav_np, sr = sf.read(str(temp_wav), dtype='float32')
    if len(wav_np.shape) == 1:
        wav_np = wav_np[:, None]
    wav = torch.from_numpy(wav_np).T
    
    wav = convert_audio(wav, sr, model.samplerate, model.audio_channels)
    wav = wav.unsqueeze(0).to(device)
    
    # 3. Apply model
    print("Separating sources...")
    with torch.no_grad():
        sources = apply_model(model, wav, shifts=1, split=True, overlap=0.25)[0]
        
    # Sources map: ['drums', 'bass', 'other', 'vocals']
    vocal_idx = model.sources.index('vocals')
    
    vocals = sources[vocal_idx]
    # Instrumental is the sum of everything else
    instrumental = torch.zeros_like(vocals)
    for i in range(len(model.sources)):
        if i != vocal_idx:
            instrumental += sources[i]
            
    # 4. Save using soundfile
    print("Saving stems...")
    sf.write(str(vocals_out), vocals.cpu().numpy().T, model.samplerate)
    sf.write(str(inst_out), instrumental.cpu().numpy().T, model.samplerate)
    
    # Cleanup
    temp_wav.unlink(missing_ok=True)
    print(f"Successfully separated {song_name}!")

if __name__ == "__main__":
    main()
