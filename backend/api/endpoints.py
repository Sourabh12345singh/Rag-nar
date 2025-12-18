from fastapi import APIRouter, UploadFile, File, HTTPException
from api.pipeline import RAGPipeline
import os
import shutil
from typing import List
import glob
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

pipeline = RAGPipeline()

@router.post("/upload")
async def upload_pdfs(files: List[UploadFile] = File(...)):  # Save uploaded PDF files to books folder
    try:
        os.makedirs("books", exist_ok=True)
        for file in files:
            if not file.filename.endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
            file_path = os.path.join("books", file.filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        logger.info(f"Uploaded {len(files)} files to books folder")
        return {"status": "success", "files_uploaded": len(files)}
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

@router.post("/process")
async def process_pdfs():  # Extract text, chunk, embed, and store in Qdrant
    try:
        result = pipeline.process_pdfs()
        logger.info("Processed PDFs successfully")
        return result
    except Exception as e:
        logger.error(f"Process error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDFs: {str(e)}")

@router.get("/query")
async def query_similar_chunks(query: str, top_k: int = 3):  # Search chunks and generate AI response
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        chunks = pipeline.search_similar_chunks(query, top_k=top_k)
        gemini_response = pipeline.generate_gemini_response(query, chunks)
        logger.info("Query processed successfully")
        return {"chunks": chunks, "gemini_response": gemini_response}
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

@router.post("/clear-books")
async def clear_books_folder():  # Delete all PDFs and reset Qdrant collection
    try:
        # Delete PDF files
        books_folder = "books"
        deleted_count = 0
        if os.path.exists(books_folder):
            pdf_files = glob.glob(os.path.join(books_folder, "*.pdf"))
            for pdf_file in pdf_files:
                logger.info(f"Deleting file: {pdf_file}")
                os.remove(pdf_file)
                deleted_count += 1
            logger.info(f"Deleted {deleted_count} PDF files from books folder")
        else:
            logger.info("No books folder found")

        # Clear Qdrant collection
        pipeline.clear_collection()

        return {
            "status": "success",
            "message": f"Deleted {deleted_count} PDF files and cleared Qdrant collection"
        }
    except Exception as e:
        logger.error(f"Clear books error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear books folder or Qdrant collection: {str(e)}")
