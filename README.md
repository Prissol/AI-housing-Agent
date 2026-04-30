# AI Housing Map Compliance Project

This project lets users upload housing map images, checks compliance using AI-style logic, and provides a bylaw chatbot powered by Groq (LLaMA3-compatible model).

## Architecture

- **Frontend:** React (Vite)
- **Backend:** Python FastAPI
- **AI Processing:** OpenCV + placeholder rule engine (easy to replace with OCR/ML later)
- **LLM Chat:** Groq API with bylaw-restricted system prompt

## Full Project Structure

```text
.
├── client/
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       └── main.jsx
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── main.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── analyze.py
│   │   └── chat.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_analyzer.py
│   │   └── groq_service.py
│   ├── ai_model/
│   │   ├── __init__.py
│   │   └── rule_engine.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── logger.py
└── server/ (legacy Node backend kept unchanged)
```

## Backend Setup (FastAPI)

1. Open terminal in `backend/`
2. Create virtual environment and activate it
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create `.env` from `.env.example` and add your key:

```env
APP_ENV=development
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
BATCH_MAX_FILES=25
BATCH_CONCURRENCY=4
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=your_real_groq_api_key
```

5. Run backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup (React)

1. Open terminal in `client/`
2. Install dependencies:

```bash
npm install
```

3. Create `.env` from `.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

4. Run frontend:

```bash
npm run dev
```

## API Endpoints

### `POST /analyze-map`

- Accepts uploaded file field: `image`
- Returns:

```json
{
  "status": "Violation",
  "details": "Explanation about detected rule conditions",
  "confidence": 0.68,
  "risk_score": 0.41,
  "findings": [
    {
      "code": "BLURRY_IMAGE",
      "title": "Blurry drawing",
      "description": "Blurry input can hide setbacks, labels, or wall boundaries.",
      "severity": "high"
    }
  ],
  "metrics": {
    "width": 1920,
    "height": 1080,
    "edge_density": 0.072,
    "line_count": 184,
    "rectangle_count": 12,
    "foreground_ratio": 0.147,
    "sharpness_score": 121.5,
    "contrast_score": 49.2
  }
}
```

### `POST /analyze-maps`

- Accepts uploaded files field: `files` (multiple images)
- Processes files concurrently with controlled worker count (`BATCH_CONCURRENCY`)
- Returns partial results if some files fail

```json
{
  "results": [
    {
      "filename": "map1.png",
      "status": "Violation",
      "details": "Potential compliance risk detected...",
      "confidence": 0.63,
      "risk_score": 0.46,
      "error": null
    },
    {
      "filename": "bad-file.jpg",
      "status": "Failed",
      "details": "Image could not be analyzed.",
      "confidence": null,
      "risk_score": null,
      "error": "Image resolution too small. Minimum required size is 500x500."
    }
  ]
}
```

### `POST /analyze-files`

- Accepts uploaded files field: `files` (mixed file types in one request)
- Supported extensions: `.jpg`, `.jpeg`, `.png`, `.pdf`, `.xlsx`, `.csv`
- Returns grouped analysis:

```json
{
  "images": [
    { "filename": "map1.png", "status": "Violation", "details": "..." }
  ],
  "pdfs": [
    { "filename": "plans.pdf", "page": 1, "status": "No Violation", "details": "..." }
  ],
  "excels": [
    { "filename": "rules.xlsx", "row": 1, "status": "Violation", "details": "Road width too small." }
  ]
}
```

### `POST /chat`

- Request:

```json
{
  "query": "What is the front setback for a 10 marla plot?"
}
```

- Response:

```json
{
  "response": "Bylaw-focused Groq response"
}
```

## Notes

- The map analyzer now uses multiple realistic CV signals (line geometry, enclosed spaces, sharpness, contrast, and drawing density) instead of a simple dummy threshold.
- You can later plug in OCR + extracted bylaw entities and advanced ML detection without changing route structure.
- CORS, logging, environment configuration, and error responses are already wired for a scalable start.
