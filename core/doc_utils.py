# --- Standard Library ---
import os
import json
from typing import List, Dict, Any

# --- Third-Party Libraries ---
import pandas as pd

# --- Application Modules ---
from langchain.schema import Document
from logging_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)


def parse_csv_file(file_path: str) -> List[Document]:
    """Parse a CSV file and return a list of Documents."""
    docs = []
    try:
        df = pd.read_csv(file_path)
        for i, row in df.iterrows():
            content = ", ".join(f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col]))
            metadata = {"source": file_path, "row": i}
            docs.append(Document(page_content=content, metadata=metadata))
    except Exception as e:
        logger.error(f"Error parsing CSV {file_path}: {e}")
    return docs


def parse_json_file(file_path: str) -> List[Document]:
    """Parse a JSON file (array or line-delimited) and return a list of Documents."""
    docs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_char = f.read(1)
            f.seek(0)
            if (first_char == '['):
                data = json.load(f)
                for i, item in enumerate(data):
                    content = json.dumps(item)
                    docs.append(Document(page_content=content, metadata={"source": file_path, "index": i}))
            else:
                for i, line in enumerate(f):
                    try:
                        item = json.loads(line)
                        content = json.dumps(item)
                        docs.append(Document(page_content=content, metadata={"source": file_path, "line": i}))
                    except Exception:
                        continue
    except Exception as e:
        logger.error(f"Error parsing JSON {file_path}: {e}")
    return docs


def parse_text_file(file_path: str) -> List[Document]:
    """Parse a plain text or markdown file and return a single Document."""
    docs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            docs.append(Document(page_content=content, metadata={"source": file_path}))
    except Exception as e:
        logger.error(f"Error parsing text {file_path}: {e}")
    return docs


# --- File Parsing ---
def parse_files_to_documents(file_paths: List[str]) -> List[Document]:
    """Parse a list of files of various types into Documents."""
    all_docs = []
    for file_path in file_paths:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            all_docs.extend(parse_csv_file(file_path))
        elif ext in ['.json', '.jsonl']:
            all_docs.extend(parse_json_file(file_path))
        elif ext in ['.txt', '.md', '.markdown']:
            all_docs.extend(parse_text_file(file_path))
        else:
            logger.warning(f"Unsupported file type for {file_path}, skipping.")
    return all_docs


def get_memory_documents(memory_history: List[Dict[str, Any]]) -> List[Document]:
    """Convert conversation history to Documents for memory integration."""
    docs = []
    for i, msg in enumerate(memory_history):
        content = json.dumps(msg)
        docs.append(Document(page_content=content, metadata={"type": "memory", "index": i}))
    return docs