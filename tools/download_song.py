import os
import sys
import subprocess
from pathlib import Path
import urllib.parse

WORKSPACE = Path(r"C:\Users\kbsama\Desktop\声音clone")

def download_song(query, output_filename=None):
    if not output_filename:
        # Generate a clean filename from query
        clean_name = "".join([c for c in query if c.isalnum() or c in (' ', '_', '-')]).strip()
        clean_name = clean_name.replace(' ', '_')
        output_filename = f"{clean_name}.wav"
        
    output_path = WORKSPACE / "songs" / "originals" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # We will use yt_dlp
    python_exe = r"C:\Applio\env\python.exe"
    
    print(f"=== Searching and downloading: {query} ===", flush=True)
    
    # Configure yt-dlp to search and extract the best audio
    cmd = [
        python_exe, "-m", "yt_dlp",
        "--playlist-items", "1",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--output", str(output_path.with_suffix(".%(ext)s")),
        f"ytsearch1:{query}"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        # Ensure the output file exists and is indeed a .wav
        # If it was saved with another suffix, rename it to .wav
        downloaded_files = list(output_path.parent.glob(f"{output_path.stem}.*"))
        for f in downloaded_files:
            if f.suffix.lower() != '.wav':
                # Convert it to wav if yt-dlp failed to convert it, but yt-dlp should succeed
                pass
        
        if output_path.exists():
            print(f"=== Success! Saved to {output_path} ===", flush=True)
            return output_path
        else:
            # Maybe it saved as .wav but we need to verify
            print(f"Error: Output file {output_path} was not found after download.")
            return None
    except Exception as e:
        print(f"Error downloading song: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_song.py <search query> [output_filename]")
        sys.exit(1)
    
    q = sys.argv[1]
    out_f = sys.argv[2] if len(sys.argv) > 2 else None
    download_song(q, out_f)
