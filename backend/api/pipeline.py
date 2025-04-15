
import os
from pathlib import Path
import fitz
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
from tqdm import tqdm
import logging
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from fastapi import HTTPException



load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, books_folder: str = "./books/", collection_name: str = "love_stories"):
        self.books_folder = books_folder
        self.collection_name = collection_name
        self.qdrant_url = os.getenv("DB_API_URL")
        # print(f"Qdrant URL: {self.qdrant_url}")
        self.model = SentenceTransformer("thenlper/gte-base", device="cpu")
        self.qdrant_api_key, self.gemini_api_key = self.load_environment()

    def load_environment(self):
        try:
            
            qdrant_api_key = os.getenv("DB_API")
            gemini_api_key = os.getenv("API_KEY")
            # print(gemini_api_key)
            if not qdrant_api_key:
                raise ValueError("QDRANT_API_KEY not found in environment variables.")
            return qdrant_api_key, gemini_api_key
        except Exception as e:
            logger.error(f"Failed to load environment variables: {e}")
            raise

    def clear_collection(self):
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

    def extract_text_from_pdfs(self, folder_path: str) -> list[dict]:
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

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
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

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.WriteTimeout),
        before_sleep=lambda retry_state: logger.warning(f"Retrying due to timeout: attempt {retry_state.attempt_number}")
    )
    def upsert_with_retry(self, client, collection_name, points):
        client.upsert(collection_name=collection_name, points=points)

    def store_in_qdrant(self, embeddings: list[list[float]], chunks: list[str], source_map: list[str]):
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

    def search_similar_chunks(self, query: str, top_k: int = 3) -> list[dict]:
        logger.info(f"Searching for chunks similar to query: {query[:50]}...")
        try:
            query_embedding = self.model.encode(
                [query], show_progress_bar=False, normalize_embeddings=True
            ).tolist()[0]
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=60.0)
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
            logger.error(f"Search failed: {e}")
            raise

    def generate_gemini_response(self, query: str, chunks: list[dict]) -> str:
        logger.info("Generating formal response with Gemini API")
        try:
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            context = "Relevant information from documents:\n"
            for i, chunk in enumerate(chunks, 1):
                context += f"Document {i} (Source: {chunk['source']}):\n{chunk['text']}\n\n"
            full_prompt =  (
                            f"Query: {query}\n\n"
                            f"Using the information provided below, generate a clear, formal, and informative answer to the query.\n"
                            f"If the answer can be found in the documents, respond based only on that.\n"
                            f"remember u have to answer by your side any how ... provide general answer also if nothing is found on the documents\n\n"
                            f"However, if the documents do **not** contain sufficient or relevant information to answer the query, "
                            f"mention that explicitly and proceed to generate a well-informed response as if it were a standard web search (like Google or Gemini would do), "
                            # f"remember u have to answer by your side any how ... provide general answer also if nothing comman\n\n"
                            f"---\n"
                            f"Document Context:\n{context}\n"
                            f"---"
                        )

            
            response = model.generate_content(full_prompt)
            logger.info("Generated Gemini response")
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate Gemini response: {e}")
            raise

    def process_pdfs(self):
        pdf_data = self.extract_text_from_pdfs(self.books_folder)
        if not pdf_data:
            raise ValueError("No PDF data extracted.")
        all_chunks, source_map = [], []
        for book in tqdm(pdf_data, desc="Chunking texts"):
            chunks = self.chunk_text(book["text"])
            all_chunks.extend(chunks)
            source_map.extend([book["file"]] * len(chunks))
        logger.info(f"Prepared {len(all_chunks)} chunks from {len(pdf_data)} books")
        embeddings = self.embed_chunks(all_chunks)
        self.store_in_qdrant(embeddings, all_chunks, source_map)
        return {"status": "success", "chunks": len(all_chunks), "books": len(pdf_data)}
