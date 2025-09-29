import os
import re

# Folder containing files
folder_path = "phrase_folder"

# Read dictionary.txt
replacements = {}
with open("dictionary.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "→" in line:
            src, dst = line.split("→", 1)
            replacements[src.strip()] = dst.strip()

# Function to replace phrases in filename (case-insensitive)
def replace_phrases(filename, replacements):
    new_name = filename
    for src, dst in replacements.items():
        # Replace ignoring case
        pattern = re.compile(re.escape(src), re.IGNORECASE)
        new_name = pattern.sub(dst, new_name)
    return new_name

# Rename files in folder
for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)
    if os.path.isfile(file_path):
        new_filename = replace_phrases(filename, replacements)
        if new_filename != filename:
            new_path = os.path.join(folder_path, new_filename)
            os.rename(file_path, new_path)
            print(f"Renamed: {filename} → {new_filename}")
