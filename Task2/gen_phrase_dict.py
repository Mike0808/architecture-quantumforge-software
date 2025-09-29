from faker import Faker
import random
import string

fake = Faker()

# Список исходных фраз
phrases = [
    "Darth",
    "Eternal", 
    "Empire", 
    "Conquest",
    "Galactic", 
    "War",
    "Korriban",
    "Revan",
    "Sith", 
    "Order",
    "Yoda",
    "Anakin",
    "Skywalker",
    "Obi-Wan",
    "Kenobi",
    "Mace", 
    "Windu",
    "Count", 
    "Dooku",
    "Darth",
    "Sidious",
    "Maul",
    "Vader",
    "Luke",
    "Leia",
    "Solo",
    "Chewbacca",
    "Calrissian",
    "Clone",
    "First Order",
    "Asajj",
    "Ventress",
    "Dark Side",
    "Light Side",
    "Darkness",
    "Chosen One",
    "Jedi Council",
    "Force Ghost",
    "Starships",
    "Death Star",
    "Millennium Falcon",
    "X-Wing",
    "XWing",
    "TIE Fighter",
    "TIEFighter",
    "Star Destroyer",
    "Imperial March",
    "Jedi Order",
    "Grand Army",
    "Rule of Two",
    "Temple",
    "Purge",
    "Order 66",
    "bounty hunter",
    "Supreme Chancellor",
    "Force-sensitive",
    "Holocron",
    "Midichlorian",
    "Podracing",
    "Wookiee",
    "Obiwan",
    "Galactic",
    "Quigon",
    "Tano",
    "Ren",
    "Kenobi",
    "Palpatine",
    "Moraband",
    "Dathomir",
    "Malachor",
    "Jedha",
    "Scarif",
    "Tatooine",
    "Naboo",
    "Coruscant",
    "Alderaan",
    "Ahsoka",
    "Obi-Wan",
    "Anakin",
    "Skywalker",
    "Leia",
    "Han",
    "Chewie",
    "Lando",
    "Vader",
    "Sidious",
    "Dooku",
    "Maul",
    "Yoda",
    "Mace",
    "Windu",
    "Dooku",
    "Jinn",
    "Tano",
    "Ventress",
    "Fett",
    "Boba",
    "Jango",
    "Ren",
    "Kylo",
    "Padmé",
    "Amidala",
    "Qui-Gon",
    "Clone",
    "prophecy",
    "Hoth",
    "Endor",
    "Jakku",
    "Mustafar",
    "planet",
    "moon",
    "station",
    "base",
    "battle",
    "Separatist",
    "jabba",
    "Hutt",
    "Wookiee",
    "droid",
    "trooper",
    "blaster",
    "jabba's",
    "princess",
    "pilot",
    "smuggler",
    "mercenary",
    "assassin",
    "skirmish",
    "siege",
    "invasion",
    "rebellion",
    "resistance",
    "stormtrooper",
    "Dagobah",
    "Kamino",
    "Geonosis",
    "Utapau",
    "Yavin",
    "Kashyyyk",
    "Holocron",
    "Padawan",
    "Master",
    "Knight",
    "Apprentice",
    "DarkSide",
    "LightSide",
    "Bane",
    "Darth",
    "Sith",
    "Jedi",
    "Temple",
    "Empire",
    "Lightsaber",
    "Rebellion",
    "Resistance", 
    "Mandalorian",
    "C-3PO",
    "R2-D2",
    "BB-8",
    "Conquest",
    "War",
    "Republic",
    "Side",
]

# Генерация фейковых фраз
# def generate_fake_phrase(original):
#     words = original.split()
#     fake_words = [fake.lore() for _ in words]
#     return " ".join(fake_words).title()

def generate_lorem_phrase(original):
    words_count = len(original.split())
    # используем faker.text для генерации слов, выбираем случайные
    lorem_words = fake.text(max_nb_chars=200).split()
    # если сгенерированных слов меньше, повторяем их
    while len(lorem_words) < words_count:
        lorem_words += fake.text(max_nb_chars=200).split()
    return " ".join(lorem_words[:words_count]).title()

# Удаляем дубликаты без учёта регистра, сохраняя оригинальный регистр первой встречи
seen = {}
for phrase in phrases:
    lower = phrase.lower()
    if lower not in seen:
        seen[lower] = phrase

# Финальный список уникальных фраз
unique_phrases = list(seen.values())

# Генерация бессмысленных фраз
def generate_gibberish_phrase(original):
    words_count = len(original.split())
    
    def gibberish_word(min_len=3, max_len=8):
        length = random.randint(min_len, max_len)
        return ''.join(random.choices(string.ascii_letters, k=length)).title()
    
    return " ".join(gibberish_word() for _ in range(words_count))

# Создание словаря
fake_dict = {phrase: generate_gibberish_phrase(phrase) for phrase in unique_phrases}

# Сохранение в файл
with open("dictionary.txt", "w", encoding="utf-8") as f:
    for k, v in fake_dict.items():
        f.write(f"{k} → {v}\n")

print("Словарь сгенерирован и сохранён в dictionary.txt")
