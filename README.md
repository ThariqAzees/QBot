# QBot -- Anna University Regulations Assistant

A full-stack RAG (Retrieval-Augmented Generation) application for Anna University's B.E./B.Tech academic regulations, curricula, and CEG academic calendar.

Built with **Zero Mandatory Paid APIs**:
- **Embeddings**: Local Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`, 384-dimensional, runs 100% locally on CPU at 0 cost).
- **LLM / Generation**: Google Gemini API (`gemini-flash-lite-latest` on the generous free tier via [Google AI Studio](https://aistudio.google.com/app/apikey)).
- **Database & Vector Store**: MongoDB Atlas Vector Search (`document_chunks` collection with cosine similarity index).
- **Web Interface**: ChatGPT-style UI with React, Vite, conversation history, Markdown rendering, and citation cards.

---

## Architecture

```
PDFs --extract--> pages --chunk (token windows)--> text chunks
                                                        |
                                          Local Sentence Transformers (384-d)
                                                        |
                                        MongoDB Atlas (document_chunks)
                                             + Atlas Vector Search index

User question --(rewrite standalone, using chat history)--> standalone Q
            --embed (local)--> vector search (top-k chunks) --> context
            --> Google Gemini (context + history) --> answer
            --> similarity classification (high/medium/low)
            --> low? --> suggest related past questions
            --> persist turn to MongoDB chat_history
```

---

## Setup & Configuration

### 1. Python Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Create `.env` (or copy from `.env.example`):
```env
# Google Gemini API Key (Free tier at https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# MongoDB Atlas connection string
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.vf6uutb.mongodb.net/?appName=Cluster0
```

### 3. Ingest Documents into MongoDB Atlas
Extracts text from university PDFs, generates 384-dim embeddings locally on CPU, and stores 904 chunks in Atlas:
```powershell
python ingest.py
```

### 4. Create History Vector Index
Sets up the vector search index for past question suggestions:
```powershell
python setup_history_index.py
```

---

## Running the Application

### Option A: ChatGPT-Style Web Application (Recommended)

1. **Start the FastAPI Backend**:
   ```powershell
   cd D:\AI_QBOT\UNIV_Qbot\qbot
   python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start the React Frontend**:
   ```powershell
   cd D:\AI_QBOT\UNIV_Qbot\qbot\frontend
   npm run dev
   ```

3. Open your browser at **[http://localhost:5173](http://localhost:5173)**.

---

### Option B: Terminal CLI Chat
```powershell
python cli.py
```

---

## Evaluation Benchmark
Run evaluation against ground-truth regulations questions (`data/evaluation_questions.csv`):
```powershell
python evaluate.py --limit 10
```
