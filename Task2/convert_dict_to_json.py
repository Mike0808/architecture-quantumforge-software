import json

# Read the dictionary.txt
input_file = "dictionary.txt"
output_file = "terms_map.json"

data = {}
with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "→" in line:
            key, value = line.split("→", 1)
            data[key.strip()] = value.strip()

# Write to JSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Converted {input_file} to {output_file}")
