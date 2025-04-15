# ⚔️ RAGnar – PDF Query Pipeline with RAG

**RAGnar** is a full-stack Retrieval-Augmented Generation (RAG) system designed to query PDF documents intelligently. It combines a sleek **Vite + React + TypeScript** frontend with a powerful **FastAPI** backend that uses **Qdrant Cloud** for vector storage and **Gemini**  for language responses.

On each page refresh, RAGnar ensures a fresh state by clearing all uploaded PDFs from the `books/` directory and wiping the associated Qdrant `love_stories` collection.

---

## 🗂️ Project Structure

```
📦 RAGnar
├── backend/       # FastAPI backend for file handling, embeddings, and querying
├── frontend/      # Vite + React + TypeScript user interface
└── books/         # Temporary folder for uploaded PDFs (auto-cleared on refresh)
```

---

## ✨ Features

- 📄 **PDF Upload**: Upload one or more PDF files via the frontend UI.
- 🧠 **RAG Processing**: Text is extracted and converted to embeddings using `thenlper/gte-base`.
- 📦 **Vector Storage**: Embeddings are stored in Qdrant (`love_stories` collection).
- 💬 **Smart Querying**: Ask questions and get Gemini-powered answers with cited chunks.
- 🔁 **Auto Reset**: Every page reload clears previous uploads and data for a clean session.

---

## 🚀 Tech Stack

- **Frontend**: Vite + React + TypeScript
- **Backend**: FastAPI (Python 3.8+)
- **Vector DB**: Qdrant Cloud
- **Embeddings**: `thenlper/gte-base`
- **LLM Responses**: Gemini 

---

## ⚙️ Setup Instructions

### 🔧 Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add environment variables to `.env`:**
   ```
   DB_API_URL
   QDRANT_API_KEY
   GROQ_API_KEY
   ```

5. **Run the backend server:**
   ```bash
   uvicorn main:app --reload
   ```

---

### 💻 Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

---

## 📌 Notes

- All uploaded PDFs are stored temporarily in the `books/` folder.
- On each page reload, `books/` and the Qdrant `love_stories` collection are cleared to maintain a clean state.
- Make sure your Qdrant collection name is **`love_stories`** in your `.env` or code.

---

## ⚔️ Author

Forged in code and guided by fate,  
**RAGnar** draws its name from the fearless Viking, **Ragnar Lothbrok**.  
Crafted by Sourabh, for those who seek knowledge like warriors seek glory.


---



## 📷 Screenshots / Demo

![image](https://github.com/user-attachments/assets/141f5db9-fa23-4f8f-8619-60f861e82586)

![image](https://github.com/user-attachments/assets/d33b467f-4679-402f-ab8e-658e39653310)


---


