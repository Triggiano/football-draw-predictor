# Getting Started

Quick steps to run the project locally.

1. Backend

```powershell
cd backend
.\venv\Scripts\Activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

3. Notes
- Backend reads secrets from `backend/.env`.
- Frontend expects backend at `http://localhost:8000`.
