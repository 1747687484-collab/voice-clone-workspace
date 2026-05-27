import os
import subprocess
import sys
from datetime import datetime

# Fix Windows console encoding for subprocess piping
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

APPLIO_DIR = r"C:\Applio"
PYTHON_EXE = os.path.join(APPLIO_DIR, "env", "python.exe")
CORE_PY = os.path.join(APPLIO_DIR, "core.py")

MODEL_NAME = "kbsama_v2"
DATASET_PATH = r"C:\Users\kbsama\Desktop\声音clone\datasets\kbsama_v2\segments"
SAMPLE_RATE = "48000"
F0_METHOD = "rmvpe"
BATCH_SIZE = "6"
TOTAL_EPOCH = "200"
SAVE_EVERY = "20"
# Prevent Out-Of-Memory (WinError 1455) by limiting multiprocessing
CPU_CORES = "2"

def run_cmd(step_name, cmd_args):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === Starting {step_name} ===", flush=True)
    cmd = [PYTHON_EXE, CORE_PY] + cmd_args
    print(f"Running: {' '.join(cmd)}", flush=True)
    
    # Run the process
    process = subprocess.Popen(cmd, cwd=APPLIO_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    
    for line in iter(process.stdout.readline, ''):
        print(line, end='', flush=True)
        
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] === ERROR: {step_name} failed with exit code {return_code} ===", flush=True)
        sys.exit(return_code)
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] === SUCCESS: {step_name} ===", flush=True)

if __name__ == "__main__":
    print(f"Auto-training pipeline for {MODEL_NAME} started!")
    
    # 1. Preprocess
    run_cmd("Preprocess", [
        "preprocess",
        "--model_name", MODEL_NAME,
        "--dataset_path", DATASET_PATH,
        "--sample_rate", SAMPLE_RATE,
        "--cut_preprocess", "Automatic",
        "--cpu_cores", CPU_CORES
    ])
    
    # 2. Extract
    run_cmd("Extract", [
        "extract",
        "--model_name", MODEL_NAME,
        "--f0_method", F0_METHOD,
        "--sample_rate", SAMPLE_RATE,
        "--include_mutes", "2",
        "--cpu_cores", CPU_CORES
    ])
    
    # 3. Train
    run_cmd("Train", [
        "train",
        "--model_name", MODEL_NAME,
        "--sample_rate", SAMPLE_RATE,
        "--batch_size", BATCH_SIZE,
        "--total_epoch", TOTAL_EPOCH,
        "--save_every_epoch", SAVE_EVERY,
        "--save_only_latest", "False",
        "--save_every_weights", "True",
        "--cache_data_in_gpu", "False"
    ])
    
    # 4. Index
    run_cmd("Index", [
        "index",
        "--model_name", MODEL_NAME
    ])
    
    print("\nAll training steps completed successfully!")
