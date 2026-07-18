# PostgreSQL Setup

Install and run PostgreSQL locally, then set `DATABASE_URL` in `backend/.env`.

Example local connection string for Postgres:

```
postgresql://postgres:password@localhost:5432/stalemate
```

Using Docker:

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: stalemate
    ports:
      - '5432:5432'
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```
