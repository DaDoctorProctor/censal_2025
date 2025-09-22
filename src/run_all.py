import os

scripts = [
    "clear.py",
    "process_saic.py",
    "divide.py",
    "regional.py",
    "divide2.py",
    "final.py"
    # Add other scripts here: "other_script.py", etc.
]

for script in scripts:
    print(f"Running {script}...")
    exit_code = os.system(f"python {script}")
    if exit_code != 0:
        print(f"⚠️ {script} failed with exit code {exit_code}")
    else:
        print(f"✅ {script} finished successfully")
