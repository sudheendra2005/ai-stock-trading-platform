# AI Stock Trading Platform

A cloud-based AI-powered stock analysis and paper trading platform built with React.js (frontend) and FastAPI (backend).

## Features

- User authentication (registration, login, JWT-based)
- AI-powered stock predictions (short-term and long-term)
- Paper trading simulation with virtual money (₹1,00,000 starting balance)
- Portfolio management and tracking
- Transaction history
- Responsive, modern UI with dark/light friendly colors
- Stock search and detailed information
- Technical analysis (Moving Averages, RSI, MACD, Volatility)

## Tech Stack

### Frontend
- React.js (Vite)
- Tailwind CSS
- React Router DOM
- Axios
- Recharts (for charts)
- Lucide React Icons

### Backend
- FastAPI
- Python
- SQLAlchemy (ORM)
- Pydantic (data validation)
- JWT Authentication
- Passlib (password hashing)
- yfinance (stock data)
- pandas, numpy (data processing)
- scikit-learn (ML models)
- PostgreSQL (database)

## Project Structure

```
ai-stock-trading-platform/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── context/
│   │   └── App.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── stocks.py
│   │   ├── wallet.py
│   │   ├── portfolio.py
│   │   └── transactions.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── prediction/
│   ├── database/
│   ├── middleware/
│   ├── utils/
│   ├── main.py
│   ├── config.py
│   └── database.py
│
└── README.md
```

## Setup Instructions

### Prerequisites
- Node.js (v16+)
- Python (v3.8+)
- PostgreSQL (or Supabase for cloud deployment)
- Git

### Backend Setup

1. Navigate to the backend directory:
```bash
cd ai-stock-trading-platform/backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```
Edit the `.env` file with your database credentials and secret key.

6. Run the backend server:
```bash
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`

#### Optional: Populate full market tickers (improves search)

To enable company-name and keyword fuzzy search across the entire NSE list, run the import script which writes `tickers.json` used by the backend:

```bash
# from the repository root
python scripts/import_nse_tickers.py
```

This creates `backend/data/tickers.json` (and `backend/app/data/tickers.json`) with NSE tickers which the backend uses for fuzzy/company-name lookup.

Note: the import script uses only Python's standard library (`urllib.request` + `csv`) so it does not require extra packages.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd ai-stock-trading-platform/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file in the frontend directory:
```bash
VITE_API_URL=http://localhost:8000
```

4. Run the frontend development server:
```bash
npm run dev
```
The frontend will be available at `http://localhost:5173`

## What I changed (quick)

- Frontend `Dashboard` / `Wallet` pages now consistently call the trading router endpoints (`/api/trading/*`) so wallet balance and transactions come from the backend.
- Search queries are URL-encoded before sending to the backend so multi-word queries work reliably.
- Backend trading router (`backend/routes/trading.py`) now performs fuzzy/company-name lookup using `backend/data/tickers.json` and built-in symbol names — this enables keyword searches like "Reliance" or "Tata Consultancy Services" to resolve to the correct ticker.
- Added `scripts/import_nse_tickers.py` to download NSE equities and write `tickers.json` for the backend.

If you want, I can also add a `/api/trading/search?q=` typeahead endpoint for UI suggestions.

### Environment Variables

#### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### Stocks
- `GET /api/stocks/trending` - Get trending stocks
- `GET /api/stocks/{symbol}` - Get stock details
- `GET /api/predict/{symbol}` - Get AI prediction for stock

### Wallet
- `GET /api/wallet` - Get wallet balance
- `POST /api/wallet/buy` - Buy stocks (paper trading)
- `POST /api/wallet/sell` - Sell stocks (paper trading)

### Portfolio
- `GET /api/portfolio` - Get user portfolio

### Transactions
- `GET /api/transactions` - Get transaction history

## Cloud Deployment

### Vercel Full-Stack Deployment
This repo now includes a root `vercel.json`, `api/index.py`, and root `requirements.txt` so Vercel can serve the Vite frontend and the FastAPI backend from one project.

1. Push the repository to GitHub.
2. Import the repository in Vercel.
3. Set these Vercel environment variables:
```bash
DATABASE_URL=postgresql://...
SECRET_KEY=your-long-random-jwt-secret
CRON_SECRET=your-long-random-cron-secret
RL_SYMBOLS=RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS,WIPRO.NS,AAPL,MSFT,GOOGL
RL_AGENT_TYPE=q
```
4. Leave `VITE_API_URL` empty for same-origin Vercel hosting. Set it only if the backend is deployed on a separate domain.
5. Deploy.

Vercel Cron calls `GET /api/cron/train-ai` every 6 hours. The endpoint captures market snapshots, trains/persists RL policies, and runs the ML predictor for the configured watchlist.

Important: Vercel Functions are request/cron based, not a permanently running 24/7 worker. For real continuous training, use a worker service such as Render/Railway/Fly.io, or keep the included `python -m rl.trainer` process running on a VM/container. The app stores trained RL policies in the SQL database so scheduled Vercel runs can keep learning state across invocations.

### Backend Worker Option
For a true always-on trainer:
```bash
cd backend
python -m rl.trainer
```
Set `TRAIN_INTERVAL_SECONDS`, `RL_SYMBOLS`, `RL_EPISODES`, and `DATABASE_URL` in the worker environment.

### Initial Dataset Bootstrap
Download the starter OHLCV datasets, cache them locally, warm ML predictions, capture market snapshots, and train initial RL policies:
```bash
cd backend
python scripts/bootstrap_market_data.py --episodes 20
```
Cached CSV files are stored in `backend/data/market_history/`. The API uses live yfinance data first, then those cached CSV files, then a synthetic demo fallback if a symbol cannot be downloaded.

### Database (Supabase)
1. Create Supabase project
2. Get database connection string
3. Update `DATABASE_URL` in backend `.env` file
4. The tables will be created automatically on first run

## Usage

1. Register a new account or login
2. Starting balance of ₹1,00,000 virtual money will be available
3. Use AI Predictions page to search for stocks and get recommendations
4. Buy/sell stocks using virtual money in the Wallet/Portfolio sections
5. Track your portfolio performance and transaction history

## Important Notes

- This platform uses **virtual paper money only** - no real money transactions
- All trading is simulated for educational and practice purposes
- AI predictions are based on technical analysis and should not be considered financial advice
- The ML models are simplified for demonstration; production systems would use more sophisticated approaches

## License

MIT License

## Acknowledgments

- Inspired by platforms like Groww and Zerodha
- Built with modern web development best practices
- Designed for learning and practice purposes only
