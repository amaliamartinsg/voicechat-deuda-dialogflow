import uuid
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

COLLECTION_NAME = "clients_info_energix"
MD_FILE = "condiciones_pago_energix.md"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = end
    return chunks

def main():
    import os
    print(open(os.path.join(os.path.dirname(__file__), "..", "data", "mds", MD_FILE)))
    with open(os.path.join(os.path.dirname(__file__), "..", "data", "mds", MD_FILE), "r", encoding="utf-8") as f:
        text = f.read()

    chunks = split_text(text)

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    vectors = model.encode(chunks, normalize_embeddings=True)

    client = QdrantClient(url="http://localhost:6333")

    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=model.get_sentence_embedding_dimension(),
                distance=Distance.COSINE,
            ),
        )

    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=np.asarray(vector, dtype=np.float32).tolist(),
                payload={
                    "text": chunk,
                    "source": "condiciones_generales_energix.md",
                    "section_index": i,
                    "type": "legal_conditions",
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)

    print(f"✅ Ingestados {len(points)} chunks en '{COLLECTION_NAME}'")

if __name__ == "__main__":
    main()
