# ContaBot — AI-Powered Financial Management Telegram Bot

<p align="center">
  <b>Smart business management through natural language conversations</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/OpenAI-Function%20Calling-412991?logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?logo=telegram&logoColor=white" alt="Telegram">
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white" alt="SQLite">
</p>

---

## Overview

ContaBot is a production-ready Telegram bot for small business financial management. Instead of navigating complex menus, users interact in **natural language** — the AI understands intent, extracts parameters, and executes operations automatically.

**What makes it different:** Most bots use rigid command parsing. ContaBot uses **OpenAI Function Calling** with **conversational memory** to enable multi-turn dialogs. If you say _"registra un ingreso de 100 dólares"_ and forget the cash box, the AI **asks you** instead of failing.

---

## Key Features

### AI Engine
- **OpenAI Function Calling** — Structured intent detection with 15+ tool schemas (no fragile JSON parsing)
- **Conversational Memory** — Per-user sliding window context with TTL-based cleanup
- **Multi-turn Dialogs** — AI asks clarifying questions when information is missing
- **AI Financial Advisor** — Automated analysis of spending trends, cash flow, debt positions, and stock alerts
- **AI-Enriched Responses** — Financial insights generated from real business data
- **Graceful Fallback** — Rule-based intent parser when OpenAI is unavailable

### Business Operations
- **Accounting**: Income, expenses, transfers between cash boxes with multi-currency support (USD, CUP, EUR)
- **Inventory**: Product tracking, purchase entries, standard & consignment sales, profit margin calculation
- **Logistics**: Container management, warehouse inventory, inter-warehouse transfers
- **Debt Management**: Payables (suppliers) and receivables (sellers) with automatic debt generation
- **Reporting**: Transaction history, CSV/Excel export, profit reports

### Architecture
- **Clean layered design**: Handlers → Services → Repositories → SQLite
- **Interactive forms**: Multi-step Telegram ConversationHandlers with button navigation
- **Auto-cancel**: Smart conversation lifecycle management
- **Admin-only**: Role-based access control via decorator

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Telegram User                    │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              AI Layer (ai/)                      │
│  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ OpenAI       │  │ Conversation Memory     │  │
│  │ Function     │  │ (per-user sliding       │  │
│  │ Calling      │  │  window + TTL)          │  │
│  └──────┬───────┘  └─────────────────────────┘  │
│         │  fallback                              │
│  ┌──────▼───────┐  ┌─────────────────────────┐  │
│  │ Rule-based   │  │ Financial Advisor       │  │
│  │ Intent Parser│  │ (trend analysis,        │  │
│  │              │  │  alerts, insights)      │  │
│  └──────┬───────┘  └─────────────────────────┘  │
│         │                                        │
│  ┌──────▼───────┐                               │
│  │ Action       │                               │
│  │ Executor     │                               │
│  └──────┬───────┘                               │
└─────────┼───────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────┐
│            Handlers (handlers/)                  │
│  Commands │ ConversationHandlers │ Menus         │
└─────────┬───────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────┐
│            Services (services/)                  │
│  ContabilidadService │ InventarioService │ ...   │
└─────────┬───────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────┐
│         Repositories (database/)                 │
│  SQLite │ Foreign Keys │ Migrations              │
└─────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key (optional, for AI features)

### Installation

```bash
git clone https://github.com/your-username/conta-bot.git
cd conta-bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your credentials
```

```env
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_USER_IDS=123456789
OPENAI_API_KEY=sk-...  # Optional
```

### Run

```bash
python bot.py
```

---

## Usage Examples

### Natural Language (AI)

| Message | What happens |
|---------|-------------|
| _"Ver balance"_ | Shows all cash box balances |
| _"Ingreso de 500 USD en CFG"_ | Records $500 income |
| _"Registra un gasto"_ | AI asks: _"¿Cuánto y en qué caja?"_ |
| _"¿Cómo va el negocio?"_ | AI Financial Advisor generates dashboard |
| _"Análisis de gastos"_ | Spending breakdown with trends & charts |
| _"Venta de SHIRT01, 3 unidades, 90 USD"_ | Records sale, updates stock |

### Traditional Commands

| Command | Description |
|---------|-------------|
| `/start` | Interactive menu |
| `/balance` | View balances |
| `/ingreso` | Record income (guided form) |
| `/gasto` | Record expense (guided form) |
| `/stock` | View inventory |
| `/deudas` | View debts |
| `/historial 30` | Last 30 days of transactions |
| `/contenedores` | Container management |
| `/exportar` | Export to CSV |

---

## AI Features Deep Dive

### Function Calling vs JSON Parsing

Traditional approach (fragile):
```
User: "ingreso 100 dólares" → LLM → raw JSON → hope it parses → action
```

ContaBot approach (robust):
```
User: "ingreso 100 dólares" → LLM + Tool schemas → structured function call → action
```

OpenAI's function calling guarantees valid, typed parameters — no regex cleanup of malformed JSON.

### Conversation Memory

```
User: "Registra un ingreso"
Bot:  "🤔 ¿Cuánto dinero y en qué caja?"     ← AI detects missing params
User: "200 dólares en CFG"
Bot:  "✅ Ingreso registrado: 200.00 USD en CFG"  ← Context from previous turn
```

### Financial Advisor

The AI advisor analyzes real business data and generates:
- **Executive summary**: Total capital, accumulated profit
- **Cash flow analysis**: 7-day and 30-day income/expense trends
- **Debt position**: Net payables vs receivables  
- **Automated alerts**: Low balance, large debts, high expense volume, critical stock
- **Recommendations**: AI-generated actionable business advice

---

## Project Structure

```
conta-bot/
├── bot.py                          # Entry point
├── ai/                             # AI engine
│   ├── openai_service.py           # OpenAI Function Calling (async)
│   ├── function_schemas.py         # 15+ tool schemas
│   ├── conversation_memory.py      # Per-user sliding window memory
│   ├── financial_advisor.py        # AI financial analysis engine
│   ├── intent_parser.py            # Rule-based fallback parser
│   ├── action_executor.py          # Intent → action dispatcher
│   └── chatbot_handler.py          # Telegram message handler
├── core/                           # Configuration
│   ├── config.py                   # Env vars + .env + config_secret.py
│   └── constants.py                # Type definitions
├── database/                       # Data layer
│   ├── models.py                   # 18-table schema
│   ├── repositories.py             # CRUD + domain queries
│   ├── connection.py               # Context manager with auto-commit
│   ├── migrations.py               # Schema upgrades
│   └── init_db.py                  # Database initialization
├── services/                       # Business logic
│   ├── contabilidad_service.py     # Accounting operations
│   ├── inventario_service.py       # Inventory management
│   ├── contenedores_service.py     # Container operations
│   └── ...                         # 9 service modules
├── handlers/                       # Telegram interface
│   ├── menu_handlers.py            # Interactive button menus
│   ├── form_handlers.py            # Multi-step forms
│   ├── contabilidad_handlers.py    # Financial commands
│   └── ...                         # 14 handler modules
├── utils/                          # Shared utilities
│   ├── validators.py               # Input validation
│   ├── currency.py                 # Multi-currency conversion
│   ├── decorators.py               # @admin_only access control
│   └── exporters.py                # CSV/Excel export
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.10+ |
| Bot Framework | python-telegram-bot 22.5 |
| AI | OpenAI API (gpt-4o-mini) with Function Calling |
| Database | SQLite with foreign keys & migrations |
| Export | ReportLab (PDF), OpenPyXL (Excel) |
| Config | python-dotenv + environment variables |

---

## Deployment

The bot is ready for deployment on platforms like Render, Railway, or any VPS.

```bash
# Set environment variables on your platform:
TELEGRAM_BOT_TOKEN=...
ADMIN_USER_IDS=...
OPENAI_API_KEY=...  # Optional

# Start command:
python bot.py
```

See [RENDER_DEPLOY.md](RENDER_DEPLOY.md) for detailed Render deployment instructions.

---

## License

MIT
