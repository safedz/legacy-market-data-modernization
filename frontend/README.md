# Pearl Protocol frontend

React + Vite dashboard for the Pearl Protocol pipeline and Spring Boot backend.

## Run

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Sign in with `analyst` / `analyst123` (or `admin` / `admin123`). The backend must be running on
`http://localhost:8080`. To use another address, copy `.env.example` to `.env` and edit `VITE_API_URL`.

The dev server must stay on port 5173: the backend only accepts that origin (`CORS_ORIGIN`).

## Screens and the endpoints they use

| Screen | Route | Endpoint |
|---|---|---|
| Public site | `#/` | none |
| Sign in | `#/login` | `GET /api/pipeline/summary` (proves the credentials) |
| Dashboard | `#/dashboard` | `/api/pipeline/summary`, `/api/quality`, `/api/surveillance/alerts` |
| Surveillance alerts | `#/alerts` | `/api/surveillance/alerts` |
| Trade search | `#/trades` | `/api/trades[?orderId=]` |
| Rejected records | `#/rejected` | `/api/rejected-records` |
| Order lineage | `#/lineage/:orderId` | `/api/lineage/{orderId}` |
| Data quality | `#/quality` | `/api/quality` |

## Commands

- `npm test` runs the formatting-helper unit tests.
- `npm run build` writes a static site to `dist/`.

## Notes

- Credentials are kept in `sessionStorage` for the tab only; signing out or closing the tab clears them.
- The backend returns at most 1,000 alerts and 1,000 trades, and the pages say so.
- Prices are dollars; trade time is seconds after midnight, exchange local time.
