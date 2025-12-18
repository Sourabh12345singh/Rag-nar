import os
from pathlib import Path
import fitz
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
from tqdm import tqdm
import logging
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from fastapi import HTTPException



load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, books_folder: str = "./books/", collection_name: str = "rag_collection"):  # Initialize pipeline with model and API keys
        self.books_folder = books_folder
        self.collection_name = collection_name
        self.qdrant_url = os.getenv("DB_API_URL")
        self.model = SentenceTransformer("thenlper/gte-base", device="cpu")
        self.qdrant_api_key, self.groq_api_key = self.load_environment()

    # load environment variables
    def load_environment(self):  # Load and validate API keys from .env
        try:
            qdrant_api_key = os.getenv("QDRANT_API_KEY")
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not qdrant_api_key:
                raise ValueError("QDRANT_API_KEY not found in environment variables.")
            if not groq_api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables.")
            return qdrant_api_key, groq_api_key
        except Exception as e:
            logger.error(f"Failed to load environment variables: {e}")
            raise

   # if any collection exists delete it for increased performance
    def clear_collection(self):  # Delete Qdrant collection if exists
        try:
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=60.0)
            if client.collection_exists(collection_name=self.collection_name):
                client.delete_collection(collection_name=self.collection_name)
                logger.info(f"Deleted Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection {self.collection_name} does not exist")
        except Exception as e:
            logger.error(f"Failed to clear Qdrant collection: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to clear Qdrant collection: {str(e)}")    
 
# extract text from pdfs
    def extract_text_from_pdfs(self, folder_path: str) -> list[dict]:  # Extract text from all PDFs in folder
        logger.info(f"Extracting text from PDFs in {folder_path}")
        text_data = []
        try:
            folder = Path(folder_path)
            if not folder.exists():
                raise FileNotFoundError(f"Folder {folder_path} does not exist.")
            pdf_files = list(folder.glob("*.pdf"))
            if not pdf_files:
                logger.warning(f"No PDF files found in {folder_path}")
                return text_data
            for file_path in tqdm(pdf_files, desc="Processing PDFs"):
                try:
                    with fitz.open(file_path) as doc:
                        pdf_text = "".join(page.get_text() + "\n" for page in doc)
                        text_data.append({"file": file_path.name, "text": pdf_text.strip()})
                except Exception as e:
                    logger.error(f"Failed to process {file_path.name}: {e}")
                    continue
            logger.info(f"Extracted text from {len(text_data)} PDFs")
            return text_data
        except Exception as e:
            logger.error(f"Error during PDF extraction: {e}")
            raise
    
    # split text into chunks to manageable sizes nd also store in qdrant
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:  # Split text into overlapping chunks
        if not text:
            logger.warning("Empty text provided for chunking")
            return []
        chunks = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunks.append(text[start:end])
            start += chunk_size - overlap
        logger.debug(f"Created {len(chunks)} chunks")
        return chunks
    
    # generate embeddings for chunks
    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:  # Generate vector embeddings using sentence-transformers
        logger.info("Generating embeddings")
        if not chunks:
            logger.warning("No chunks provided for embedding")
            return []
        try:
            embeddings = self.model.encode(
                chunks, show_progress_bar=True, batch_size=16, normalize_embeddings=True
            )
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
 
    # store embeddings and chunks in qdrant with retry mechanism
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.WriteTimeout),
        before_sleep=lambda retry_state: logger.warning(f"Retrying due to timeout: attempt {retry_state.attempt_number}")
    )
    # upsert with retry
    def upsert_with_retry(self, client, collection_name, points):  # Upload vectors with retry on timeout
        client.upsert(collection_name=collection_name, points=points)

    # store data in qdrant
    def store_in_qdrant(self, embeddings: list[list[float]], chunks: list[str], source_map: list[str]):  # Store embeddings and text in Qdrant vector DB
        logger.info(f"Storing {len(embeddings)} points in Qdrant collection {self.collection_name}")
        try:
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=60.0)
            if not client.collection_exists(collection_name=self.collection_name):
                logger.info(f"Creating collection {self.collection_name}")
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=len(embeddings[0]) if embeddings else 768, distance=Distance.COSINE
                    )
                )
            batch_size = 100
            for i in tqdm(range(0, len(embeddings), batch_size), desc="Uploading batches"):
                batch_end = min(i + batch_size, len(embeddings))
                points = [
                    PointStruct(
                        id=i + j,
                        vector=embedding,
                        payload={"text": chunk, "source": source}
                    )
                    for j, (embedding, chunk, source) in enumerate(
                        zip(embeddings[i:batch_end], chunks[i:batch_end], source_map[i:batch_end])
                    )
                ]
                self.upsert_with_retry(client, self.collection_name, points)
            logger.info(f"Stored {len(embeddings)} points in Qdrant")
        except Exception as e:
            logger.error(f"Failed to store data in Qdrant: {e}")
            raise
    
    # search for similar chunks in qdrant
    def search_similar_chunks(self, query: str, top_k: int = 3) -> list[dict]:  # Find most similar document chunks using vector search
        logger.info(f"Searching for chunks similar to query: {query[:50]}...")
        try:
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=60.0)
            
            # Check if collection exists
            if not client.collection_exists(collection_name=self.collection_name):
                logger.warning(f"Collection {self.collection_name} does not exist. Returning empty results.")
                return []
            
            query_embedding = self.model.encode(
                [query], show_progress_bar=False, normalize_embeddings=True
            ).tolist()[0]
            
            search_results = client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True
            )
            results = [
                {
                    "text": result.payload.get("text", ""),
                    "source": result.payload.get("source", "unknown"),
                    "score": result.score
                }
                for result in search_results
            ]
            logger.info(f"Found {len(results)} similar chunks")
            return results
        except Exception as e:
            logger.warning(f"Search failed: {e}. Returning empty results.")
            return []

    # generate formal response using Groq API
    def generate_gemini_response(self, query: str, chunks: list[dict]) -> str:  # Generate AI response using Groq with document context
        logger.info("Generating response with Groq API")
        try:
            client = Groq(api_key=self.groq_api_key)
            
            if chunks and len(chunks) > 0:
                # If we have document context, use it
                context = "Relevant information from documents:\n"
                for i, chunk in enumerate(chunks, 1):
                    context += f"Document {i} (Source: {chunk['source']}):\n{chunk['text']}\n\n"
                user_message = (
                    f"Query: {query}\n\n"
                    f"Using the information provided below, generate a clear, formal, and informative answer to the query.\n"
                    f"If the answer can be found in the documents, respond based only on that.\n"
                    f"If the documents do not contain sufficient information, provide a general answer as well.\n\n"
                    f"---\n"
                    f"Document Context:\n{context}\n"
                    f"---"
                )
            else:
                # No documents available, act as general assistant
                user_message = f"Answer the following question in a clear, informative, and helpful manner:\n\n{query}"

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
                model="llama-3.3-70b-versatile",  # Updated model
            )
            
            response_text = chat_completion.choices[0].message.content
            logger.info("Generated Groq response")
            if response_text:
                return response_text
            else:
                logger.warning("Empty response from Groq API")
                return "I apologize, but I couldn't generate a response at this time. Please try again."
        except Exception as e:
            logger.error(f"Failed to generate Groq response: {e}")
            return f"Error generating response: {str(e)}"
    
    # process pdfs end-to-end 
    # final method to call all other methods
    def process_pdfs(self):  # Orchestrate full pipeline: extract, chunk, embed, and store
        pdf_data = self.extract_text_from_pdfs(self.books_folder)
        if not pdf_data:
            raise ValueError("No PDF files found. Please upload PDF files first before processing.")
        all_chunks, source_map = [], []
        for book in tqdm(pdf_data, desc="Chunking texts"):
            chunks = self.chunk_text(book["text"])
            all_chunks.extend(chunks)
            source_map.extend([book["file"]] * len(chunks))
        logger.info(f"Prepared {len(all_chunks)} chunks from {len(pdf_data)} books")
        embeddings = self.embed_chunks(all_chunks)
        self.store_in_qdrant(embeddings, all_chunks, source_map)
        return {"status": "success", "chunks": len(all_chunks), "books": len(pdf_data)}
