# Stalemate Protocol (workspace)

Frontend (Next.js + Tailwind)

- Enter the frontend folder and run:

```bash
cd frontend
npm install
npm run dev
```

Backend (FastAPI)

- Create and activate the virtual environment, then run the app:

On Windows (using the included venv):

```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Environment

- Copy `.env.example` to `.env` and update `DATABASE_URL` for PostgreSQL.
