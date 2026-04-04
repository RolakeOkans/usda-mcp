# USDA MCP Server

MCP server that connects USDA's NASS QuickStats API to any MCP-compatible
AI model, allowing farmers, researchers, and USDA staff to ask plain English
questions about US agricultural data and get accurate, data-backed answers.

Built for the Challenge X Hackathon — Feb 28 to Apr 18, 2026.

---

## What This Does

Farmers, researchers, and USDA staff can ask plain English questions
about US agricultural data and get accurate, data-backed answers —
without needing to know what an API is or how to find the data themselves.

Examples of questions the server can answer:

**Planting decisions**
- "How many acres of corn were planted in Illinois in 2023?"
- "How does Iowa soybean acreage compare to 2020?"

**Yield and production**
- "What was the corn yield per acre in Kansas last year?"
- "Which state produced the most soybeans in 2022?"

**Pricing**
- "What price did Iowa farmers receive for corn in 2022?"
- "How has the soybean price changed over the last 5 years?"

**Comparisons**
- "Should I plant corn or soybeans based on recent prices?"
- "How does Illinois corn production compare to Iowa?"

The server connects to USDA's NASS QuickStats API, retrieves the
relevant data, and returns a clear answer in plain English.

---

## Current Status

- NASS QuickStats API connection — working
- 8 verified queries for corn and soybeans — working
- MCP server tools — in progress
- AMS Market News API — planned
- Demo interface — planned

---

## Project Structure
```
usda-mcp/
├── clients/
│   └── nass_client.py      # NASS QuickStats API wrapper
├── server/
│   └── tools/
│       └── nass.py         # MCP tools (in progress)
├── tests/
│   └── qa_log.csv          # Q&A evaluation log
├── demo/
│   └── app.py              # Demo interface
├── .env.example            # Template for API keys
└── requirements.txt
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/RolakeOkans/usda-mcp.git
cd usda-mcp
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Create a `.env` file in the root folder**
```
NASS_API_KEY=your_key_here
```

**4. Get your free NASS API key**

Register at https://www.nass.usda.gov/developer/index.php
You will receive your key by email within a few minutes.

---

## Verified Queries

All queries tested for Iowa, 2022.
The same parameters work for any US state and any year.

| Commodity | Statistic | Iowa 2022 Result |
|-----------|-----------|-----------------|
| Corn | Area planted | 12,900,000 acres |
| Corn | Yield | 200 bu / acre |
| Corn | Production | 2,470,000,000 bu |
| Corn | Price received | $6.62 / bu |
| Soybeans | Area planted | 10,100,000 acres |
| Soybeans | Yield | 58.5 bu / acre |
| Soybeans | Production | 586,755,000 bu |
| Soybeans | Price received | $14.20 / bu |

---

## Data Sources

| Source | What it contains | Status |
|--------|-----------------|--------|
| NASS QuickStats | Acreage, yield, production, price | Working |
| AMS Market News | Current and historical commodity prices | Planned |
| AMS Socrata | Transportation costs and volumes | Stretch goal |

---

## How It Works
```
User asks a plain English question
        ↓
AI model reads the question and decides which tool to call
        ↓
MCP server receives the tool call with parameters
        ↓
NASS API returns the raw data
        ↓
AI model interprets the data and returns a plain English answer
        ↓
User gets a useful, accurate answer
```

---

## Security

- API keys are stored in `.env` and never committed to GitHub
- Server follows OWASP MCP Top 10 security guidelines (in progress)
- MCP-compliant and AI-agnostic — works with any MCP-compatible client

Never commit your `.env` file. Use `.env.example` as a template.

---

## Team

| Role | Owner | Responsibilities |
|------|-------|-----------------|
| MCP / AI Layer | [teammate name] | MCP server, tool definitions, demo UI |
| Data / APIs | Morolake | API research, client code, field guide |
| Evaluation / Security | Neyssa | Q&A testing, OWASP security, accuracy metrics |
