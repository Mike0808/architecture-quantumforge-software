import os
import re

# Папка с файлами
folder_path = "phrase_folder"

# Словарь замен
dict_file = "dictionary.txt"

# Чтение словаря
replacements = {}
with open(dict_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "→" in line:
            src, dst = line.split("→", 1)
            replacements[src.strip()] = dst.strip()

# Функция для регистронезависимой замены
def replace_insensitive(text, replacements):
    def replacement_func(match):
        word = match.group(0)
        # Берём ключ в нижнем регистре
        return replacements[match.re.pattern.lower()]
    
    for src, dst in replacements.items():
        # Создаём шаблон для игнорирования регистра
        pattern = re.compile(re.escape(src), re.IGNORECASE)
        text = pattern.sub(lambda m: dst, text)
    return text

# Замена в файлах папки
for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        text = replace_insensitive(text, replacements)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Обработан файл: {filename}")
print("Все файлы обработаны.")