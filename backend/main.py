


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router
import os

app = FastAPI(title="PDF RAG Pipeline")

# Add CORS middleware to allow requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    os.makedirs("books", exist_ok=True)  # Ensure books folder exists for PDF uploads
    uvicorn.run(app, host="0.0.0.0", port=8000)
