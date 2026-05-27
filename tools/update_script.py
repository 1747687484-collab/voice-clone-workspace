import json
import re
import sys
from pathlib import Path

target = Path('voice_cover.py')
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update DEFAULT_CONFIG
config_str = """DEFAULT_CONFIG = {
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
        "denoise": True,
        "reverb": "subtle",
        "vocal_eq": True,
    },
    "rvc": {
        "recommended_f0_method": "rmvpe",
        "recommended_sample_rate": "48k",
        "recommended_first_batch_size": "6-8 for RTX 4060 Laptop 8GB",
    },
}"""
content = re.sub(r'DEFAULT_CONFIG = \{.*?\n\}', config_str, content, flags=re.DOTALL)

# 2. Update make-dataset filter
new_filters = """        filters = [f"highpass=f=60"]
        if getattr(args, "denoise", True):
            filters.append("afftdn")
        filters.append(f"loudnorm=I={loudness_i}:TP=-1.5:LRA=14")"""
old_filters = """        filters = [f"highpass=f=60", f"loudnorm=I={loudness_i}:TP=-1.5:LRA=11"]"""
content = content.replace(old_filters, new_filters)

# 3. Update make-dataset arguments
dataset_arg_inject = """    dataset.add_argument("--loudness-i", type=int, default=None, help="Integrated loudness target for voice clips.")
    dataset.add_argument("--denoise", action="store_true", default=True, help="Apply FFT denoise to remove mic static.")
    dataset.add_argument("--no-denoise", action="store_false", dest="denoise", help="Disable denoising.")"""
content = content.replace('    dataset.add_argument("--loudness-i", type=int, default=None, help="Integrated loudness target for voice clips.")', dataset_arg_inject)

# 4. Update mix filter
mix_old = """    if offset_ms >= 0:
        vocal_chain = f"[0:a]adelay={offset_ms}:all=1,volume={args.vocal_gain_db}dB[v]"
        inst_chain = f"[1:a]volume={args.instrumental_gain_db}dB[i]"
    else:
        vocal_chain = f"[0:a]volume={args.vocal_gain_db}dB[v]"
        inst_chain = f"[1:a]adelay={abs(offset_ms)}:all=1,volume={args.instrumental_gain_db}dB[i]\""""

mix_new = """    v_fx = ""
    if args.vocal_eq:
        v_fx += "equalizer=f=300:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1.5:g=1.5,"
    if args.reverb == "subtle":
        v_fx += "aecho=0.8:0.7:40:0.3,"
    elif args.reverb == "medium":
        v_fx += "aecho=0.8:0.75:60|80:0.4|0.25,"
        
    i_fx = ""
    if args.vocal_eq:
        i_fx += ",equalizer=f=2000:t=q:w=2:g=-1.5"

    if offset_ms >= 0:
        vocal_chain = f"[0:a]{v_fx}adelay={offset_ms}:all=1,volume={args.vocal_gain_db}dB[v]"
        inst_chain = f"[1:a]volume={args.instrumental_gain_db}dB{i_fx}[i]"
    else:
        vocal_chain = f"[0:a]{v_fx}volume={args.vocal_gain_db}dB[v]"
        inst_chain = f"[1:a]adelay={abs(offset_ms)}:all=1,volume={args.instrumental_gain_db}dB{i_fx}[i]"\""""
content = content.replace(mix_old, mix_new)

# 5. Update mix arguments
mix_arg_inject = """    mix.add_argument("--vocal-offset-ms", type=int, default=0, help="Delay vocals if positive, instrumental if negative.")
    mix.add_argument("--reverb", choices=["none", "subtle", "medium"], default="subtle", help="Add spatial reverb to vocals.")
    mix.add_argument("--vocal-eq", action="store_true", default=True, help="Apply EQ to make vocals sit in the mix.")
    mix.add_argument("--no-vocal-eq", action="store_false", dest="vocal_eq", help="Disable vocal EQ.")"""
content = content.replace('    mix.add_argument("--vocal-offset-ms", type=int, default=0, help="Delay vocals if positive, instrumental if negative.")', mix_arg_inject)

# 6. Add analyze command
analyze_code = """def cmd_analyze(args: argparse.Namespace) -> None:
    ffprobe = tool_path("ffprobe")
    if not ffprobe:
        raise AppError("ffprobe not found.")
    voice_name = safe_name(args.name)
    segments_dir = ROOT / "datasets" / voice_name / "segments"
    if not segments_dir.exists():
        raise AppError(f"Dataset segments not found: {segments_dir}")
    
    files = list(segments_dir.glob("*.wav"))
    if not files:
        raise AppError("No wav files found in dataset.")
        
    total_duration = 0.0
    for f in files:
        ok, out = capture_command([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(f)])
        if ok and out:
            total_duration += float(out)
            
    print_heading(f"Dataset Analysis: {voice_name}")
    print(f"Total segments: {len(files)}")
    print(f"Total duration: {total_duration / 60:.2f} minutes")
    if total_duration < 5.0:
        print("[WARNING] Dataset is less than 5 minutes. Consider recording more singing materials.")
    else:
        print("[OK] Dataset duration is sufficient.")
        
    print("\\nTip: A good dataset should contain a wide range of pitches (Do-Re-Mi) and varied singing techniques.")
"""
content = content.replace('def cmd_trim_test', analyze_code + '\n\ndef cmd_trim_test')

analyze_parser = """    analyze = subparsers.add_parser("analyze", help="Analyze the quality and duration of a prepared dataset.")
    analyze.add_argument("--name", default="my_voice", help="Voice model/dataset name.")
    analyze.set_defaults(func=cmd_analyze)
    
    trim ="""
content = content.replace('    trim =', analyze_parser)

with open(target, 'w', encoding='utf-8') as f:
    f.write(content)
print("Update applied to voice_cover.py")
