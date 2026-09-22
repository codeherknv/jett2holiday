# Jett 2 Holiday — Real-Time Dynamic Pricing & Demand Forecasting (APS-02)

**Jett 2 Holiday** is an intelligent dynamic pricing and demand forecasting platform designed for the travel and tourism industry (hotels + flights). It decouples statistical forecasting (Prophet / Regression) from deterministic, explainable rule engines with strict floor and ceiling guardrails.

---

## 🏛 Repository Structure

```
jett2holiday/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application & REST endpoint routers
│   │   ├── database.py          # SQLite connection helper (APS-02.db)
│   │   ├── schemas.py           # Pydantic contract schemas
│   │   └── mock_data.py         # Contract stubs & Phase 2 ML TODO markers
│   ├── tests/
│   │   └── test_endpoints.py    # Endpoint contract test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js        # Fetch API wrapper for all 4 backend endpoints
│   │   ├── components/
│   │   │   ├── Header.jsx       # Control Plane navigation & locale switcher (EN/HI)
│   │   │   ├── MetricsRow.jsx   # Floor guardrail, ceiling cap & daily move KPIs
│   │   │   ├── ForecastChart.jsx# Dual-axis Recharts (Price vs Demand Index) + Bounds
│   │   │   ├── ExplainabilityCard.jsx # Factor decomposition & multilingual audit
│   │   │   ├── SimulatorCard.jsx# What-if scenario sliders & simulation trigger
│   │   │   └── EventModal.jsx   # Telemetry event emitter
│   │   ├── App.jsx              # Main Dashboard shell & state management
│   │   ├── index.css            # Tailwind + Glassmorphism design system
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── ml/
│   ├── explore_dataset.py       # Table schema & row count explorer for APS-02.db
│   ├── dataset_exploration.ipynb# Jupyter notebook for EDA
│   ├── requirements.txt         # ML packages (pandas, scikit-learn, prophet)
│   └── README.md
├── data/
│   ├── README.md                # Description of APS-02.db schema
│   ├── init_db.py               # SQLite schema & sample data initializer
│   └── APS-02.db                # SQLite database
├── docker-compose.yml           # Backend + Frontend compose config
├── .gitignore                   # Python + Node ignores
└── README.md                    # Project documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+ and `npm`
- *(Optional)*: **Docker & Docker Compose**

---

### 1. Backend Setup (FastAPI)

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate a Python virtual environment
# On Windows:
python -m venv venv
.\venv\Scripts\activate

# On Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the FastAPI development server
uvicorn app.main:app --reload --port 8000
```

- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### 2. Frontend Setup (React + Vite + Tailwind)

```bash
# 1. Open a new terminal and navigate to frontend
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

- **Dashboard UI**: [http://localhost:5173](http://localhost:5173)

---

### 3. Running with Docker Compose

To launch both backend and frontend together with a single command:

```bash
docker-compose up --build
```

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

---

### 4. ML Dataset Exploration

```bash
# Initialize or inspect the SQLite database schema
python data/init_db.py

# Run the dataset explorer
python ml/explore_dataset.py
```

---

## 📡 API Contracts Summary

| Method | Endpoint | Description | Input Payload / Query | Response Shape |
|---|---|---|---|---|
| `POST` | `/pricing/calculate` | Computes dynamic candidate price & clamps to guardrails | `{ "entity_id": str, "target_date": str }` | `{ "effective_price": float, "base_price": float, "demand_index": float, "occupancy_factor": float, "lead_time_factor": float, "seasonality_factor": float, "bound_clamped": bool }` |
| `GET` | `/pricing/explain` | Decomposes dynamic price into factor weights & multilingual summaries | `?entity_id=htl_sng_001_deluxe&date=2026-10-15` | `{ "effective_price": float, "base_price": float, "factors": [...], "explanation_en": str, "explanation_hi": str }` |
| `POST` | `/pricing/simulate` | Runs a 30-day what-if pricing curve simulation | `{ "entity_id": str, "base_multiplier": float, "daily_move_limit": float }` | `{ "simulated_price_curve": [...], "revenue_delta_pct": float, "booking_rate_delta_pct": float, "breaches": int }` |
| `POST` | `/events` | Ingests telemetry (search, view, booking, cancellation) | `{ "entity_id": str, "event_type": str, "timestamp": str, "lead_time_days": int }` | `{ "status": "logged" }` |

---

## 🔬 Phase 2 Implementation Roadmap (TODO Markers)

All files contain `# TODO: [Phase 2]` annotations indicating where real algorithms will connect:
1. **Demand Index Forecasting**: Fit Meta Prophet / Linear Regression models on 13 months of telemetry events from `pricing_events` with IQR outlier clipping.
2. **Deterministic Pricing Engine**: Evaluate dynamic multipliers ($\text{Candidate Price} = \text{Baseline Price} \times (1 + \sum \text{factors})$) and clamp against `price_bounds`.
3. **Audit History Storage**: Persist every calculated price and explanation into `price_history`.
4. **Multilingual Templates**: Generate dynamic English (`en-IN`) and Hindi (`hi`) narratives using BCP-47 locale tags.
