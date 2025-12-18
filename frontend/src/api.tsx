const API_BASE_URL = "http://localhost:8080";

interface Chunk {
  source: string;
  score: number;
  text: string;
}

interface QueryResponse {
  chunks: Chunk[];
  gemini_response: string;
}

// Upload PDF files to backend
export const uploadPDFs = async (
  files: File[]
): Promise<{ status: string; files_uploaded: number }> => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }
  return response.json();
};

// Process PDFs: extract, chunk, embed, and store
export const processPDFs = async (): Promise<{
  status: string;
  chunks: number;
  books: number;
}> => {
  const response = await fetch(`${API_BASE_URL}/process`, {
    method: "POST",
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Processing failed");
  }
  return response.json();
};

// Query RAG system with user question
export const queryDocuments = async (
  query: string,
  topK: number = 3
): Promise<QueryResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/query?query=${encodeURIComponent(query)}&top_k=${topK}`,
    {
      method: "GET",
    }
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Query failed");
  }
  return response.json();
};

// Clear all PDFs and reset Qdrant collection
export const clearBooks = async (): Promise<{
  status: string;
  message: string;
}> => {
  const response = await fetch(`${API_BASE_URL}/clear-books`, {
    method: "POST",
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to clear books");
  }
  return response.json();
};
