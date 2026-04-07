import logging
import os
import threading
import json
from pathlib import Path

# ONLY light imports at the top
from langchain_aws import BedrockEmbeddings
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Path to the documents folder (Absolute path for container WORKDIR)
DATA_DIR = os.environ.get(
    "DATA_DIR",
    "/app/knowledge_base/pdfs"
)

_vectorstore = None
_vs_lock = threading.Lock()

def _get_or_create_vectorstore():
    """Build the vector store if it hasn't been built yet (Shielded Imports)."""
    global _vectorstore
    
    with _vs_lock:
        if _vectorstore is not None:
            return _vectorstore

        logger.info(f"Building Knowledge Base from {DATA_DIR}...")
        
        # --- SHIELDED HEAVY IMPORTS ---
        try:
            from langchain_community.document_loaders import PyPDFLoader
            from langchain_community.vectorstores import InMemoryVectorStore
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            logger.debug("Local imports successful.")
        except Exception as e:
            logger.error(f"Failed to import community libs: {e}")
            raise e

        # Bedrock Embeddings config
        embedding_model_id = os.environ.get(
            "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
        )
        region = os.environ.get("AWS_REGION", "us-east-1")
        embeddings = BedrockEmbeddings(model_id=embedding_model_id, region_name=region)

        # 1. Load PDFs
        documents = []
        pdf_path = Path(DATA_DIR)
        
        if pdf_path.exists():
            pdf_files = list(pdf_path.glob("*.pdf"))
            logger.info(f"Indexing {len(pdf_files)} documentation files...")
            
            for pdf_file in pdf_files:
                try:
                    loader = PyPDFLoader(str(pdf_file))
                    docs = loader.load()
                    documents.extend(docs)
                except Exception as e:
                    logger.error(f"Could not load {pdf_file.name}: {e}")
        else:
            logger.warning(f"Documentation directory not found at {DATA_DIR}")

        # 2. Split and Index
        if documents:
            logger.info(f"Loaded {len(documents)} pages. Splitting into chunks...")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            splits = text_splitter.split_documents(documents)
            
            logger.info(f"Creating vector index for {len(splits)} chunks...")
            _vectorstore = InMemoryVectorStore.from_documents(
                documents=splits,
                embedding=embeddings
            )
            logger.info("Knowledge Base index built successfully.")
        else:
            logger.warning("No documents loaded - initializing empty index.")
            _vectorstore = InMemoryVectorStore(embedding=embeddings)

        return _vectorstore

@tool
def search_knowledge_base(query: str) -> str:
    """Useful for searching Amazon's financial reports (10-K, Earnings)."""
    try:
        vs = _get_or_create_vectorstore()
        # Search for top 5 matches
        results = vs.similarity_search(query, k=5)
        
        if not results:
            return "No relevant documentation found for the provided query."
            
        context = "\n\n".join([doc.page_content for doc in results])
        return context
    except Exception as e:
        logger.error(f"Knowledge Base Tool Failure: {e}")
        return f"Error accessing financial data: {e}"

def get_knowledge_base_tool():
    """Return the search_knowledge_base tool (LangChain format)."""
    return Tool(
        name="search_knowledge_base",
        func=search_knowledge_base,
        description=(
            "Search Amazon's official financial reports. Use this for revenue, "
            "segment growth, business results, and official forecasts."
        ),
    )
