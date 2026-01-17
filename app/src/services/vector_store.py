from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import Distance, VectorParams
from src.services.embeddings import embeddings_model, vector_size
from qdrant_client.http.exceptions import UnexpectedResponse
from config.project_config import SETTINGS

qdrant_url = SETTINGS.qdrant_url
collection_name = SETTINGS.qdrant_collection
threshold = SETTINGS.threshold
qdrant_client = SETTINGS.qdrant_client
k_docs = SETTINGS.k_docs

def create_collection_if_not_exists():
    try:
        qdrant_client.get_collection(collection_name)
        print(f"Qdrant: colección '{collection_name}' encontrada.")
    except UnexpectedResponse:
        print(f"Qdrant: colección '{collection_name}' no existe. Creando...")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        print(f"Qdrant: colección '{collection_name}' creada.")

create_collection_if_not_exists()

qdrant_langchain = QdrantVectorStore.from_existing_collection(
    embedding=embeddings_model,
    collection_name=collection_name,
    url=SETTINGS.qdrant_url,
)

