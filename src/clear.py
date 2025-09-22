import os
import shutil

# Path to your folder
folder_path = "output/csv"

# Check if the folder exists
if os.path.exists(folder_path):
    # Iterate over all files in the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            # Remove file or folder
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Delete file
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Delete folder and its contents
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
    print(f"All files in '{folder_path}' have been cleared.")
else:
    print(f"The folder '{folder_path}' does not exist.")
