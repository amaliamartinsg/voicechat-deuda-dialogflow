from langchain_community.embeddings import HuggingFaceEmbeddings
from config.project_config import SETTINGS

MODEL_NAME = SETTINGS.embedding_model_name
embeddings_model = HuggingFaceEmbeddings(model_name=MODEL_NAME)
vector_size = len(embeddings_model.embed_query("test"))
