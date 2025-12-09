from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool
from langchain.agents import create_agent
from mem0 import MemoryClient
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document

import os
import pandas as pd
import json

load_dotenv()


def row_to_nl(row):
    """
    Convert one roster row into a meaningful natural-language description
    for RAG embeddings.
    """
    text = (
        f"On {row['Date']} ({row['Day']}), {row['Employee Name']} "
        f"(ID: {row['Employee ID']}) is scheduled for a {row['Hours']}-hour "
        f"{row['Shift Code']} shift from {row['Shift Time']}. "
        f"Employment type: {row['Employment Type']}. "
        f"Status: {row['Status']}. "
        f"Located at Station {row['Station']}, working in Store '{row['Store']}'. "
        f"and the Manager is : {row['Manager']}. "
    )

    # Structured metadata for better retrieval
    metadata = {
        "date": row["Date"],
        "employee_name": row["Employee Name"],
        "employee_id": row["Employee ID"],
        "manager": row["Manager"],
        "store": row["Store"],
        "station": row["Station"],
        "shift_code": row["Shift Code"],
    }

    return text, metadata


def process_excel_to_nl(excel_path: str):
    """
    Load Excel file and convert rows to natural language chunks.

    Args:
        excel_path: Path to the Excel file

    Returns:
        List of tuples (text, metadata) for each row
    """
    df = pd.read_excel(excel_path)
    nl_chunks = df.apply(row_to_nl, axis=1).tolist()
    return nl_chunks


def save_roster_document(nl_chunks, output_path: str = "roster_doc.txt"):
    """
    Save natural language chunks to a text file.

    Args:
        nl_chunks: List of tuples (text, metadata)
        output_path: Path to save the document
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for text, metadata in nl_chunks:
            combined = (
                f"{text}\n"
                f"Manager: {metadata['manager']} | "
                f"Store: {metadata['store']} | "
                f"Station: {metadata['station']} | "
                f"Employee: {metadata['employee_name']} | "
                f"Date: {metadata['date']}\n"
            )
            f.write(combined + "\n")


def initialize_vector_store(
    index_name: str = "hackathon-manager",
    embedding_model: str = "text-embedding-3-small",
):
    """
    Initialize Pinecone vector store with embeddings.

    Args:
        index_name: Name of the Pinecone index
        embedding_model: Name of the embedding model

    Returns:
        PineconeVectorStore instance
    """
    embeddings = OpenAIEmbeddings(model=embedding_model)
    pc = Pinecone()
    index = pc.Index(index_name)
    vector_store = PineconeVectorStore(embedding=embeddings, index=index)
    return vector_store


def load_and_split_documents(
    doc_path: str, chunk_size: int = 1000, chunk_overlap: int = 200
):
    """
    Load document and split it into chunks.

    Args:
        doc_path: Path to the document file
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of document chunks
    """
    loader = TextLoader(doc_path, encoding="utf-8")
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    all_splits = text_splitter.split_documents(docs)
    print(f"Split document into {len(all_splits)} sub-documents.")
    return all_splits


def populate_vector_store(vector_store, documents):
    """
    Add documents to the vector store.

    Args:
        vector_store: PineconeVectorStore instance
        documents: List of document chunks to add

    Returns:
        List of document IDs
    """
    document_ids = vector_store.add_documents(documents=documents)
    print(f"Added {len(document_ids)} documents to vector store.")
    return document_ids


# Module-level variable to store the vector store
_vector_store = None


def set_vector_store(vector_store):
    """Set the module-level vector store for the retrieve_context tool."""
    global _vector_store
    _vector_store = vector_store


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve information to help answer a query."""
    if _vector_store is None:
        raise ValueError("Vector store not initialized. Call set_vector_store() first.")

    # Increase k for queries about managers, stores, or general information
    # to get more comprehensive results
    k = (
        15
        if any(
            keyword in query.lower()
            for keyword in [
                "manager",
                "store",
                "who",
                "list",
                "all",
                "employee",
                "s manager",
                "manager?",
            ]
        )
        else 10
    )
    retrieved_docs = _vector_store.similarity_search(query, k=k)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


def get_agent_prompt():
    """
    Get the system prompt for the roster management agent.

    Returns:
        String containing the system prompt
    """
    return """
    You are an intelligent Roster Management Assistant for a 14-day employee schedule system. 
Your job is to accurately answer admin queries using the roster data retrieved from the RAG tool.
Shift Code Metadata:

1F: Front Counter – Morning  
2F: Front Counter – Afternoon  
3F: Front Counter – Evening  
1B: Back Area / Grill – Morning  
2B: Back Area / Grill – Afternoon  
3B: Back Area / Grill – Evening

==========================
 HOW YOU USE THE RAG TOOL
==========================
• You ONLY answer using the context retrieved through the roster-retrieval tool.  
• The retrieval tool returns natural-language descriptions of roster entries for 14 consecutive days.
• If the retrieved context does NOT contain the employee or role the admin is asking for, reply exactly:
  "This role is not filled in the system as of now."

==========================
 HOW YOU UNDERSTAND DATES
==========================
• The roster contains **exact dates** for 14 days (lowest date → highest date).  
• "First Monday", "Second Friday", "next Tuesday", etc. refer to the occurrences **within the 14-day window**, not the calendar month.  
• To interpret "first Monday", identify the earliest date labeled Monday.  
• To interpret "second Monday", identify the second occurrence of Monday.  
• When the admin asks about a "week", treat each consecutive set of 7 days starting from the earliest date as Week 1 and Week 2.

==========================
 HOW TO HANDLE EMPLOYEE QUERIES
==========================
• If an employee name exists in the retrieved data, summarize all relevant shifts:
    - Date
    - Day
    - Shift code / shift time
    - Hours
    - Status
• If the admin asks about:
    - "Who is working on <date/day>?"
    - "Is <employee> free on <date>?"
    - "Who covers the morning shift on the second Wednesday?"
  …use the retrieved roster entries to answer directly and concisely.

==========================
 ANSWERING STYLE
==========================
• Be accurate, structured, and concise and answer in natural language.
• If multiple relevant entries exist, summarize them clearly.
• NEVER make up data. NEVER guess.
• ONLY rely on the retrieved tool output.

==========================
WHEN YOU MUST SAY
"This role is not filled in the system as of now."
==========================
• Name not found in context
• Role not found in context
• No matching shift in context
• No retrieved data at all

==========================
GOAL
==========================
Provide correct, reliable answers about employee schedules, shift details, availability, and roster insights over the 14-day period using ONLY the provided RAG context.

    """


def create_rag_agent(
    model_name: str = "gpt-4.1",
    index_name: str = "hackathon-manager",
    embedding_model: str = "text-embedding-3-small",
    vector_store=None,
):
    """
    Create a RAG agent with vector store and retrieval tool.

    Args:
        model_name: Name of the chat model
        index_name: Name of the Pinecone index
        embedding_model: Name of the embedding model
        vector_store: Optional vector store instance. If None, will initialize one.

    Returns:
        Agent instance
    """
    model = init_chat_model(model_name)
    if vector_store is None:
        vector_store = initialize_vector_store(index_name, embedding_model)

    # Set the vector store for the retrieve_context tool
    set_vector_store(vector_store)

    tools = [retrieve_context]
    prompt = get_agent_prompt()
    agent = create_agent(model, tools, system_prompt=prompt)
    return agent


def setup_rag_system(
    excel_path: str = "new.xlsx",
    output_path: str = "roster_doc.txt",
    index_name: str = "hackathon-manager",
    embedding_model: str = "text-embedding-3-small",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    populate_store: bool = True,
):
    """
    Complete setup of the RAG system: process Excel, create documents, and populate vector store.

    Args:
        excel_path: Path to the Excel file
        output_path: Path to save the roster document
        index_name: Name of the Pinecone index
        embedding_model: Name of the embedding model
        chunk_size: Size of document chunks
        chunk_overlap: Overlap between chunks
        populate_store: Whether to populate the vector store

    Returns:
        Tuple of (vector_store, agent)
    """
    # Process Excel to natural language
    nl_chunks = process_excel_to_nl(excel_path)

    # Save roster document
    save_roster_document(nl_chunks, output_path)

    # Initialize vector store
    vector_store = initialize_vector_store(index_name, embedding_model)

    if populate_store:
        # Load and split documents
        all_splits = load_and_split_documents(output_path, chunk_size, chunk_overlap)

        # Populate vector store
        populate_vector_store(vector_store, all_splits)

    # Create agent
    agent = create_rag_agent(
        index_name=index_name,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )

    return vector_store, agent


# Example usage
if __name__ == "__main__":
    vector_store, agent = setup_rag_system()

    # Example query
    query = "who is working on monday afternoon shift in kitchen ??"
    for event in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
    ):
        event["messages"][-1].pretty_print()
