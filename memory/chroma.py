from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# Load embedding model
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def get_vectorstore():
    return Chroma(
        persist_directory="data/chroma_db",
        embedding_function=embeddings
    )

def load_documents():
    # Load all PDFs from data/docs and store them in ChromaDB
    docs_path = "data/docs"
    all_docs = []

    for filename in os.listdir(docs_path):
        if filename.endswith(".pdf"):
            print(f"Loading: {filename}")
            loader = PyPDFLoader(os.path.join(docs_path, filename))
            pages = loader.load()
            all_docs.extend(pages)

    # Split text into chunks for vector storage
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(all_docs)
    print(f"✅ {len(chunks)} chunks created")

    # Save chunks to ChromaDB
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="data/chroma_db"
    )
    print("✅ Documents saved to ChromaDB!")

def suche_in_docs(question: str):
    # Search for relevant chunks in ChromaDB
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(question, k=2)

    if not results:
        return "No relevant documents found."

    context = ""
    for doc in results:
        context += f"{doc.page_content[:300]}\n\n"
    return context

if __name__ == "__main__":
    load_documents()
    print(suche_in_docs("What is Progressive Overload?"))