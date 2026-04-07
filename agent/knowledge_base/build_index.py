"""
build_index.py — Download Amazon financial PDFs and build a FAISS vector index.

Run this script locally before building the Docker image:
    cd agent
    python knowledge_base/build_index.py

Requires AWS credentials configured for Amazon Bedrock (Titan Embed V2).
"""

import logging
import os
import sys
from pathlib import Path

import requests
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DOCUMENTS = [
    {
        "url": "https://s2.q4cdn.com/299287126/files/doc_financials/2025/ar/Amazon-2024-Annual-Report.pdf",
        "name": "Amazon-2024-Annual-Report.pdf",
        "source": "Amazon 2024 Annual Report",
    },
    {
        "url": "https://s2.q4cdn.com/299287126/files/doc_financials/2025/q3/AMZN-Q3-2025-Earnings-Release.pdf",
        "name": "AMZN-Q3-2025-Earnings-Release.pdf",
        "source": "AMZN Q3 2025 Earnings Release",
    },
    {
        "url": "https://s2.q4cdn.com/299287126/files/doc_financials/2025/q2/AMZN-Q2-2025-Earnings-Release.pdf",
        "name": "AMZN-Q2-2025-Earnings-Release.pdf",
        "source": "AMZN Q2 2025 Earnings Release",
    },
]

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "faiss_index"
DOWNLOAD_DIR = SCRIPT_DIR / "pdfs"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def download_pdfs() -> list[Path]:
    """Download PDFs to a local directory."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    paths = []

    for doc in DOCUMENTS:
        filepath = DOWNLOAD_DIR / doc["name"]
        if filepath.exists():
            logger.info(f"Already downloaded: {doc['name']}")
        else:
            logger.info(f"Downloading: {doc['url']}")
            response = requests.get(doc["url"], timeout=120)
            response.raise_for_status()
            filepath.write_bytes(response.content)
            logger.info(f"Saved to {filepath} ({len(response.content) / 1024:.0f} KB)")
        paths.append(filepath)

    return paths


def load_and_split(pdf_paths: list[Path]) -> list:
    """Load PDFs and split into text chunks."""
    all_docs = []

    for i, path in enumerate(pdf_paths):
        logger.info(f"Loading PDF: {path.name}")
        loader = PyPDFLoader(str(path))
        pages = loader.load()

        # Add source metadata
        source_name = DOCUMENTS[i]["source"]
        for page in pages:
            page.metadata["source"] = source_name
            page.metadata["filename"] = path.name

        all_docs.extend(pages)
        logger.info(f"  Loaded {len(pages)} pages from {path.name}")

    logger.info(f"Total pages loaded: {len(all_docs)}")

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(all_docs)
    logger.info(f"Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    return chunks


def build_faiss_index(chunks: list) -> None:
    """Generate embeddings and build a FAISS index."""
    logger.info(f"Initialising Bedrock embeddings (model={EMBEDDING_MODEL}, region={AWS_REGION})")
    embeddings = BedrockEmbeddings(
        model_id=EMBEDDING_MODEL,
        region_name=AWS_REGION,
    )

    logger.info("Building FAISS index (this may take a few minutes)...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(OUTPUT_DIR))
    logger.info(f"FAISS index saved to {OUTPUT_DIR}")


def main():
    logger.info("=" * 60)
    logger.info("Building FAISS Knowledge Base Index")
    logger.info("=" * 60)

    pdf_paths = download_pdfs()
    chunks = load_and_split(pdf_paths)
    build_faiss_index(chunks)

    logger.info("=" * 60)
    logger.info("Done! Index ready at: %s", OUTPUT_DIR)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
