from sentence_transformers import SentenceTransformer
import json

embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
vector = embedder.encode("Как найти человека?").tolist()
print(json.dumps(vector))
