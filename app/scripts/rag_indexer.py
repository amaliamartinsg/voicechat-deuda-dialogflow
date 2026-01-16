import os
import re
import uuid
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np
from tqdm import tqdm

from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


# -----------------------------
# Config
# -----------------------------
COLLECTION_NAME = "clients_info_energix"

DEFAULT_CHUNK_SIZE = 900      # ~caracteres, simple y estable
DEFAULT_CHUNK_OVERLAP = 150   # solape para mantener contexto

OCR_LANG = os.getenv("OCR_LANG", "spa")  # "spa" o "spa+eng"
TESSERACT_CMD = os.getenv("TESSERACT_CMD")  # opcional: ruta binario tesseract


@dataclass
class Chunk:
    text: str
    source_file: str
    page: int
    chunk_index: int


def normalize_text(text: str) -> str:
    text = text.replace("\u00ad", "")  # soft hyphen
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """
    Chunker simple por caracteres, intentando cortar por saltos de línea / punto.
    """
    text = normalize_text(text)
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)

        # intenta “cerrar” el chunk en un separador razonable si no estamos al final
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "))
            if cut > int(chunk_size * 0.6):
                end = start + cut + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # siguiente inicio con overlap
        start = max(end - overlap, end)

        if start == end:
            break

    return chunks


def try_extract_text_pdf(pdf_path: str) -> List[Tuple[int, str]]:
    """
    Devuelve [(page_number, text)] si hay texto embebido.
    """
    reader = PdfReader(pdf_path)
    pages_text = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages_text.append((i + 1, normalize_text(t)))
    return pages_text


def should_use_ocr(pages_text: List[Tuple[int, str]], min_chars_total: int = 200) -> bool:
    total = sum(len(t) for _, t in pages_text)
    return total < min_chars_total


def ocr_pdf_to_text_by_page(pdf_path: str, dpi: int = 300) -> List[Tuple[int, str]]:
    """
    OCR página a página. Requiere poppler y tesseract.
    """
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    images = convert_from_path(pdf_path, dpi=dpi)
    out = []
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang=OCR_LANG)
        out.append((i + 1, normalize_text(text)))
    return out


def build_chunks_from_pdf(pdf_path: str, chunk_size: int, overlap: int) -> List[Chunk]:
    pages_text = try_extract_text_pdf(pdf_path)
    if should_use_ocr(pages_text):
        pages_text = ocr_pdf_to_text_by_page(pdf_path)

    chunks: List[Chunk] = []
    base = os.path.basename(pdf_path)

    for page_num, page_text in pages_text:
        if not page_text:
            continue
        pieces = split_text(page_text, chunk_size=chunk_size, overlap=overlap)
        for idx, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    text=piece,
                    source_file=base,
                    page=page_num,
                    chunk_index=idx,
                )
            )
    return chunks


def ensure_collection(client: QdrantClient, collection: str, vector_size: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection in existing:
        # opcional: podrías validar que el size coincide
        return

    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def batched(iterable: List[Chunk], batch_size: int) -> Iterable[List[Chunk]]:
    for i in range(0, len(iterable), batch_size):
        yield iterable[i : i + batch_size]


def main(
    pdf_paths: List[str],
    qdrant_url: str,
    qdrant_api_key: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    batch_size: int = 64,
) -> None:
    
    from src.services.embeddings import embeddings_model, vector_size

    # Qdrant client
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    ensure_collection(client, COLLECTION_NAME, vector_size)

    # Procesado
    all_chunks: List[Chunk] = []
    for pdf in pdf_paths:
        print(f"\n📄 Procesando: {pdf}")
        chunks = build_chunks_from_pdf(pdf, chunk_size=chunk_size, overlap=chunk_overlap)
        print(f"  -> chunks generados: {len(chunks)}")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No se generaron chunks (¿PDFs vacíos o OCR fallando?).")
        return

    # Upsert por lotes
    for chunk_batch in tqdm(list(batched(all_chunks, batch_size)), desc="⬆️  Upsert Qdrant"):
        texts = [c.text for c in chunk_batch]
        vectors = embeddings_model.encode(texts, normalize_embeddings=True)
        vectors = np.asarray(vectors, dtype=np.float32)

        points = []
        for c, v in zip(chunk_batch, vectors):
            point_id = str(uuid.uuid4())
            payload = {
                "text": c.text,
                "source_file": c.source_file,
                "page": c.page,
                "chunk_index": c.chunk_index,
                "collection": COLLECTION_NAME,
            }
            points.append(PointStruct(id=point_id, vector=v.tolist(), payload=payload))

        client.upsert(collection_name=COLLECTION_NAME, points=points)

    print(f"\n✅ Ingest completado. Colección: {COLLECTION_NAME} | Total chunks: {len(all_chunks)}")


if __name__ == "__main__":

    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent.parent / ".env")
    pdfs = [
        "app/data/pdfs/CONDICIONES_GENERALES.pdf",
        "app/data/pdfs/FAQs_Energix (1).pdf"
    ]

    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

    main(
        pdf_paths=pdfs,
        qdrant_url=QDRANT_URL,
        qdrant_api_key=QDRANT_API_KEY,
    )
