import os
import sys
import subprocess
import time

ROOT_FOLDER_ID = "1mWKMVs2ibWWZG0bCO3QwK0yZtYGabZh5"

CONSTITUENCIES = [
    # BBMP South (7)
    "BBMP South/Basavanagudi",
    "BBMP South/BTM Layout",
    "BBMP South/Jayanagar",
    "BBMP South/Padmanabanagar",
    "BBMP South/Bommanahalli",
    "BBMP South/Vijayanagar",
    "BBMP South/Govindarajanagar",
    
    # BBMP Central (7)
    "BBMP Central/Chamrajapet",
    "BBMP Central/Chickpet",
    "BBMP Central/Gandhinagar",
    "BBMP Central/Rajajinagar",
    "BBMP Central/Rajarajeshwarinagar",
    "BBMP Central/Shivajinagar",
    "BBMP Central/Shantinagar",
    
    # BBMP North (7)
    "BBMP North/CV Ramannagar",
    "BBMP North/Hebbal",
    "BBMP North/KR Puram",
    "BBMP North/Sarvagnanagar",
    "BBMP North/Malleshwaram",
    "BBMP North/Mahalakshmi Layout",
    "BBMP North/Pulakeshinagar",
    
    # Bangalore Urban (7)
    "Bangalore_Urban/Anekal",
    "Bangalore_Urban/South Bangalore",
    "Bangalore_Urban/Mahadevapura",
    "Bangalore_Urban/Dasarahalli",
    "Bangalore_Urban/Yeshwanthpura",
    "Bangalore_Urban/Byatarayanapura",
    "Bangalore_Urban/Yelahanka"
]

def is_already_done(c_path):
    """Check if the master excel already exists locally or on Google Drive."""
    clean_name = c_path.split('/')[-1]
    expected_filename = f"{clean_name}_Master_Electoral_Roll.xlsx"
    
    # 1. Fast local check
    if os.path.exists(expected_filename) and os.path.getsize(expected_filename) > 500 * 1024:
        return True
        
    # 2. Direct remote file check
    cmd = [
        "/Users/s.premkumar/.local/bin/rclone", "lsf",
        f"gdrive:{c_path}/{expected_filename}",
        "--drive-root-folder-id", ROOT_FOLDER_ID
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if expected_filename.lower() in proc.stdout.lower():
            return True
    except Exception:
        pass
    return False

def main():
    print(f"\n=======================================================")
    print(f" BENGALURU ALL-CONSTITUENCIES MASTER BATCH RUNNER")
    print(f" Total Constituencies: {len(CONSTITUENCIES)}")
    print(f" Workers per constituency: 6")
    print(f"=======================================================\n")
    
    start_all = time.time()
    
    for idx, c_path in enumerate(CONSTITUENCIES, 1):
        clean_name = c_path.split('/')[-1]
        print(f"\n>>> [{idx}/{len(CONSTITUENCIES)}] Checking {clean_name} ({c_path})...", flush=True)
        
        # Check if already done
        if is_already_done(c_path):
            print(f" [SKIP] {clean_name} Master Electoral Roll already exists on Google Drive!", flush=True)
            continue
            
        print(f" Starting extraction for {clean_name}...", flush=True)
        t_start = time.time()
        
        cmd = [
            "/Users/s.premkumar/.local/bin/uv", "run",
            "--with", "pyobjc-framework-Vision,pyobjc-framework-Quartz,pillow,pymupdf,pandas,openpyxl",
            "python3", "process_constituency.py",
            "--constituency", c_path,
            "--workers", "6"
        ]
        
        ret = subprocess.run(cmd)
        t_elapsed = time.time() - t_start
        
        if ret.returncode != 0:
            print(f" [ERROR] Failed processing {clean_name} after {t_elapsed/60:.1f} mins", flush=True)
        else:
            print(f" [COMPLETED] Finished {clean_name} in {t_elapsed/60:.1f} mins!", flush=True)
            
            # Clean up local PDF cache to keep disk space free
            local_cache = os.path.abspath(f"./downloads/{clean_name}")
            if os.path.exists(local_cache):
                subprocess.run(["rm", "-rf", local_cache])
                print(f" Cleaned up local cache {local_cache}", flush=True)

    total_time = time.time() - start_all
    print(f"\n=======================================================")
    print(f" All 28 Constituencies Processed in {total_time/3600:.2f} hours!")
    print(f"=======================================================\n", flush=True)

if __name__ == "__main__":
    main()
