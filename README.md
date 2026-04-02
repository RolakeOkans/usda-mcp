# USDA MCP Server

MCP server that connects USDA's NASS QuickStats and AMS Market News APIs
to any MCP-compatible AI model, allowing farmers, researchers, and USDA
staff to ask plain English questions about US agricultural data and get
accurate, data-backed answers.

Built for the Challenge X Hackathon — Feb 28 to Apr 18, 2026.
Team: Root Access

---

## What This Does

Farmers, researchers, and USDA staff can ask plain English questions
about US agricultural data and get accurate, data-backed answers —
without needing to know what an API is or how to find the data themselves.

**Historical data (NASS QuickStats)**
- "What was the corn yield in Iowa in 2022?"
- "How has soybean production in Illinois trended from 2018 to 2022?"
- "How many acres of wheat were planted in Kansas in 2021?"
- "What price did Iowa farmers receive for corn in 2022?"
- "What was national corn production in 2022?"

**Current market prices (AMS Market News)**
- "What is the current corn price in Iowa?"
- "What is today's soybean price in Illinois?"
- "Where should I sell my soybeans — iowa, illinois, or nebraska?"
- "What is the current wheat price in Kansas?"

---

## Tools

The server exposes 4 MCP tools:

| Tool | Data Source | What it does |
|------|-------------|--------------|
| `get_nass_data` | NASS QuickStats | Fast lookup for corn and soybean yield, acreage, production, price received in any state and year |
| `query_nass_flexible` | NASS QuickStats | Any crop, any statistic, multi-year trends, national or county level data |
| `get_ams_price` | AMS Market News | Current cash grain prices by location |
| `get_ams_price_comparison` | AMS Market News | Compare current prices across multiple states to find the best market |

---

## Project Structure
```
usda-mcp/
├── clients/
│   ├── nass_client.py       # NASS QuickStats API wrapper
│   └── ams_client.py        # AMS Market News API wrapper
├── server/
│   ├── main.py              # MCP server — 4 tools
│   ├── security.py          # OWASP MCP Top 10 mitigations
│   └── tools/
│       └── __init__.py
├── tests/
│   └── qa_log.csv           # Q&A evaluation log
├── demo/
│   └── app.py               # Demo interface (planned)
├── logs/
│   └── usda_nass_server.log # Auto-generated server log
├── .env                     # API keys (never committed)
├── .env.example             # Template for API keys
├── requirements.txt         # Pinned dependencies
├── SECURITY.md              # OWASP MCP Top 10 documentation
└── README.md
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/RolakeOkans/usda-mcp.git
cd usda-mcp
```

**2. Create a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Create a `.env` file in the root folder**
```
NASS_API_KEY=your_nass_key_here
AMS_API_KEY=your_ams_key_here
```

**5. Get your API keys**

NASS: Register at https://www.nass.usda.gov/developer/index.php

AMS: Register at https://mymarketnews.ams.usda.gov

Both are free and issued within minutes.

---

## Connect to Claude Desktop

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "usda-nass": {
      "command": "/path/to/your/python",
      "args": ["/path/to/usda-mcp/server/main.py"],
      "env": {
        "NASS_API_KEY": "your_key_here",
        "AMS_API_KEY": "your_key_here"
      }
    }
  }
}
```

Replace paths with your actual Python and project paths.

---

## Verified Data — NASS QuickStats

All queries tested and confirmed working for Iowa, 2022.

| Commodity | Statistic | Iowa 2022 Result |
|-----------|-----------|-----------------|
| Corn | Area planted | 12,900,000 ACRES |
| Corn | Yield | 200 BU / ACRE |
| Corn | Production | 2,470,000,000 BU |
| Corn | Price received | $6.62 / BU |
| Soybeans | Area planted | 10,100,000 ACRES |
| Soybeans | Yield | 58.5 BU / ACRE |
| Soybeans | Production | 586,755,000 BU |
| Soybeans | Price received | $14.20 / BU |

---

## Verified Data — AMS Market News

Current prices confirmed working as of April 2, 2026.

| Commodity | Location | Price |
|-----------|----------|-------|
| Corn | Minneapolis | $4.08 / bu |
| Soybeans | Minneapolis | $11.10 / bu |
| Corn | Iowa | $4.12 / bu |
| Corn | Texas | $4.90 / bu |
| Soybeans | Illinois | $11.76 / bu |
| Wheat | Kansas | $5.34 / bu |

---

## Data Sources

| Source | What it covers | Status |
|--------|---------------|--------|
| NASS QuickStats | Acreage, yield, production, price received — any crop, any state, any year | Working |
| AMS Market News | Current cash grain prices at elevators — 19 states + dynamic search | Working |
| AMS Socrata | Transportation costs and volumes | Stretch goal |
| ERS | Forecasted prices | Stretch goal |

---

## How It Works
```
User asks a plain English question
        ↓
AI model reads the question and decides which tool to call
        ↓
MCP server validates and sanitizes the input
        ↓
NASS or AMS API returns the raw data
        ↓
Server scans response for security issues
        ↓
AI model interprets the data and returns a plain English answer
        ↓
All tool calls logged to logs/usda_nass_server.log
```

---

## Security

This server addresses all 10 OWASP MCP Top 10 risks.
See [SECURITY.md](SECURITY.md) for full details.

Summary:
- API keys stored in `.env`, never committed, redacted from all logs
- Read-only server — GET requests only, no write access to any USDA system
- Input sanitization on all tool arguments
- Rate limiting at 30 requests per minute per tool
- Prompt injection detection on all API responses
- Full audit logging of every tool call

Never commit your `.env` file. It is listed in `.gitignore`.

---

## Team — Root Access

| Role | Owner | Responsibilities |
|------|-------|-----------------|
| Data / APIs | Morolake | API research, NASS client, AMS client, MCP server, security |
| MCP / AI Layer | [Gabriela] | AI layer, demo UI |
| Evaluation / Security | [Neyssa] | Q&A testing, accuracy metrics |

---

## Hackathon

Challenge X+ USDA
Timeline: Feb 28 to Apr 18, 2026
Showcase: April 18, 2026