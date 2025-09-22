import os

scripts = [
    "clear.py", # Clean the output folder
    "process_saic.py", # Extract data and divide by National, State and region
    "divide.py", # Divide (National / Estatal)
    "regional.py", # Divide regions into subfolders with each region name ready to divide
    "divide2.py", # Divide (Estatal / Regional)
    "final.py" # Divide (Nacional / Estatal) / (Estatal / Regional)
    # Add other scripts here: "other_script.py", etc.
]

for script in scripts:
    print(f"Running {script}...")
    exit_code = os.system(f"python {script}")
    if exit_code != 0:
        print(f"⚠️ {script} failed with exit code {exit_code}")
    else:
        print(f"✅ {script} finished successfully")
