# BidWicket 🏏

> **Cricket Management & Live Auction SaaS Platform**  
> Full-stack: FastAPI + MongoDB (Beanie) · React + TypeScript + Vite · Real-time WebSockets

---

## Architecture

```
Bid-Wicket-Original/
├── backend/          # FastAPI + Beanie + WebSockets
│   ├── app/
│   │   ├── api/routes/   auth, users, tournaments, teams, players, matches, auctions
│   │   ├── core/         config, security (JWT/bcrypt), database
│   │   ├── models/       Beanie documents (MongoDB)
│   │   ├── schemas/      Pydantic request/response schemas
│   │   ├── services/     AuctionService (race-condition safe)
│   │   └── websockets/   ConnectionManager (match & auction rooms)
│   └── requirements.txt
└── frontend/         # React 18 + Vite + TanStack Query
    └── src/
        ├── pages/    Dashboard, Tournaments, Teams, Players, Matches, Auctions, AuctionRoom
        ├── context/  AuthContext (JWT + refresh)
        ├── hooks/    useWebSocket
        ├── services/ api.ts (Axios + auto-refresh)
        └── types/    Shared TypeScript interfaces
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | ≥ 3.11 |
| Node.js | ≥ 18 |
| MongoDB Atlas | Free tier works |

---

## 1 · Backend Setup

```powershell
cd backend

# Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# ↑ Open .env and fill in MONGO_URI and SECRET_KEY
```

### `.env` values

```dotenv
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/bidwicket?retryWrites=true&w=majority
SECRET_KEY=change-me-to-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
```

### Start the backend

```powershell
uvicorn app.main:app --reload --port 8000
```

API docs available at → **http://localhost:8000/docs**

---

## 2 · Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

App available at → **http://localhost:5173**

## 3 · Collaborator Setup (Git Pull)

If you are cloning this project onto a new machine, follow these exact commands to get up and running instantly:

```bash
# 1. Clone & Enter Directory
git clone <your-repository-url>
cd Bid-Wicket-Original

# 2. Setup Backend & Seed Database
cd backend
python -m venv .venv

# Activate Virtual Environment (Windows)
.\.venv\Scripts\Activate.ps1
# Activate Virtual Environment (Mac/Linux)
# source .venv/bin/activate

# Install dependencies strictly tied to working legacy DB drivers
pip install -r requirements.txt

# Setup ENV
cp .env.example .env
# --> IMPORTANT: Open .env and insert the MongoDB Atlas URL! <--

# Seed the Database
python seed.py

# Keep Backend Running
uvicorn app.main:app --port 8000
```

Open a second terminal:

```bash
# 3. Setup Frontend
cd frontend
npm install

# Write frontend ENV
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env
echo "VITE_WS_URL=ws://localhost:8000/api/v1" >> .env

# Run Frontend
npm run dev
```

---

## 4 · First Run

1. Open **http://localhost:5173/register**
2. Create an **Organizer** account (select role during registration)
3. Create a Tournament → Create Teams → Add Players
4. Create an Auction → Add players to it → Go Live
5. Open two browser windows with different **Team Owner** accounts to test concurrent bidding

---

## Roles

| Role | Permissions |
|------|------------|
| `viewer` | Read-only access to all data |
| `team_owner` | Manage own team, place bids in auctions |
| `organizer` | Create/manage tournaments, teams, players, matches, auctions |
| `admin` | Full access including user management |

> **Note:** Admin role cannot be self-assigned at registration. Promote via DB or Admin API.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login → JWT tokens |
| GET | `/api/v1/tournaments/` | List tournaments |
| POST | `/api/v1/auctions/{id}/items/{item_id}/bid` | Place bid |
| WS | `ws://localhost:8000/api/v1/auctions/{id}/ws` | Auction room |
| WS | `ws://localhost:8000/api/v1/matches/{id}/ws` | Live match scores |

Full interactive docs: **http://localhost:8000/docs**
