import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# Database configuration
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = str(BASE_DIR / "vector_db")
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embeddings():
    print("Loading embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}
    )

    print("Embedding model loaded successfully!")
    return embeddings


def build_vector_store(transcript: str) -> Chroma:
    print("\nSTEP 1: Building vector store...")

    if not transcript or not transcript.strip():
        raise ValueError(
            "Transcript is empty. Cannot create Chroma DB."
        )

    # Split transcript into smaller chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_text(transcript)
    print(f"STEP 2: Created {len(chunks)} transcript chunks")

    if not chunks:
        raise ValueError(
            "No transcript chunks were created."
        )

    # Convert chunks into LangChain documents
    docs = [
        Document(
            page_content=chunk,
            metadata={"chunk_index": i}
        )
        for i, chunk in enumerate(chunks)
    ]

    # Load embedding model
    print("STEP 3: Loading embedding model...")
    embeddings = get_embeddings()

    # Create database directory
    os.makedirs(CHROMA_DIR, exist_ok=True)

    print(f"STEP 4: Creating Chroma DB at:\n{CHROMA_DIR}")

    # Store documents and embeddings in Chroma
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR
    )

    print("STEP 5: Chroma DB created successfully!")

    return vector_store


def load_vector_store() -> Chroma:
    print("Loading existing Chroma DB...")

    if not os.path.exists(CHROMA_DIR):
        raise FileNotFoundError(
            f"Chroma DB not found at: {CHROMA_DIR}\n"
            "Build the vector store first."
        )

    embeddings = get_embeddings()

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )

    print("Chroma DB loaded successfully!")
    return vector_store


def get_retriever(vector_store: Chroma, k: int = 4):
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )