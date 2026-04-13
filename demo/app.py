import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import streamlit as st
import plotly.graph_objects as go
import anthropic
from clients.ams_client import get_ams_price, get_ams_price_comparison, search_ams_any
from clients.nass_client import get_nass_data, query_nass_flexible
from dotenv import load_dotenv

load_dotenv()

# ── PAGE CONFIG ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="USDA Agricultural Intelligence",
    page_icon="🌾",
    layout="wide"
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; }
    .main { background-color: #f7f5f0; }
    .block-container { padding-top: 2rem; max-width: 1200px; }
    h1 {
        font-family: 'Playfair Display', serif;
        color: #1a3d1f;
        font-size: 2.8rem;
        line-height: 1.1;
        margin-bottom: 0;
    }
    h2, h3 { font-family: 'Playfair Display', serif; color: #1a3d1f; }
    .tagline { color: #5a7a5f; font-size: 1.1rem; margin-top: 0.3rem; margin-bottom: 2rem; }
    .section-divider { border: none; border-top: 2px solid #d4c9a8; margin: 2.5rem 0; }
    .metric-card {
        background: white;
        border: 1px solid #e0d9c8;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .metric-label {
        color: #5a7a5f;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.4rem;
    }
    .metric-value {
        color: #1a3d1f;
        font-size: 1.9rem;
        font-weight: 700;
        font-family: 'Playfair Display', serif;
    }
    .answer-box {
        background: white;
        border-left: 4px solid #2d6a35;
        border-radius: 0 8px 8px 0;
        padding: 1.2rem 1.5rem;
        color: #1a3d1f;
        font-size: 1.05rem;
        line-height: 1.6;
        margin-top: 0.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .user-bubble { text-align: right; margin: 0.8rem 0; }
    .user-bubble span {
        background: #2d6a35;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 12px 12px 0 12px;
        font-size: 0.95rem;
        display: inline-block;
        max-width: 80%;
        text-align: left;
    }
    .source-tag {
        display: inline-block;
        background: #e8f0e9;
        color: #2d6a35;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        margin-top: 0.4rem;
        letter-spacing: 0.05em;
    }
    .stButton > button {
        background-color: #2d6a35;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: background 0.2s;
    }
    .stButton > button:hover { background-color: #1a3d1f; }
    .live-badge {
        display: inline-block;
        background: #2d6a35;
        color: white;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 20px;
        letter-spacing: 0.1em;
        vertical-align: middle;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── TOOL DEFINITIONS FOR CLAUDE ───────────────────────────────────────────
TOOLS = [
    {
        "name": "get_nass_data",
        "description": """Get USDA NASS data for any crop in any US state for a specific year.
        Use for yield, area planted, production, or price received.
        Best for simple single-year, single-state lookups.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "The crop e.g. CORN, SOYBEANS, WHEAT"
                },
                "statistic": {
                    "type": "string",
                    "description": "AREA PLANTED, YIELD, PRODUCTION, or PRICE RECEIVED"
                },
                "state": {
                    "type": "string",
                    "description": "Two letter state code e.g. IA, IL, KS"
                },
                "year": {
                    "type": "integer",
                    "description": "The year e.g. 2022"
                }
            },
            "required": ["commodity", "statistic", "state", "year"]
        }
    },
    {
        "name": "query_nass_flexible",
        "description": """Flexible USDA NASS query for any crop, any statistic, any time range.
        Use for any crop beyond corn and soybeans, multi-year trends,
        national level data, county level data, or any unusual statistic.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "e.g. CORN, SOYBEANS, WHEAT, SORGHUM FOR GRAIN, COTTON, TOBACCO, PEANUTS"
                },
                "statistic": {
                    "type": "string",
                    "description": "e.g. AREA PLANTED, YIELD, PRODUCTION, PRICE RECEIVED"
                },
                "state": {
                    "type": "string",
                    "description": "Two letter state code. Leave empty for national."
                },
                "year": {"type": "integer", "description": "Specific year"},
                "year_gte": {"type": "integer", "description": "Start year for trends"},
                "year_lte": {"type": "integer", "description": "End year for trends"},
                "agg_level": {
                    "type": "string",
                    "description": "STATE, NATIONAL, or COUNTY"
                },
                "unit": {"type": "string", "description": "e.g. BU, ACRES"}
            },
            "required": ["commodity", "statistic"]
        }
    },
    {
        "name": "get_ams_price",
        "description": """Get current live grain market prices from USDA AMS Market News.
        Use when someone asks about today's price or current market price
        for grain commodities. Works for corn, soybeans, wheat, oats, sorghum, canola.
        Available locations: iowa, illinois, kansas, nebraska, minnesota, indiana,
        ohio, missouri, texas, north dakota, south dakota, arkansas, tennessee,
        kentucky, virginia, pennsylvania, colorado, california, minneapolis.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "e.g. Corn, Soybeans, Wheat"
                },
                "location": {
                    "type": "string",
                    "description": "State or market e.g. iowa, kansas, minneapolis"
                }
            },
            "required": ["commodity"]
        }
    },
    {
        "name": "get_ams_price_comparison",
        "description": """Compare current grain prices across multiple locations.
        Use when a farmer wants to know where to sell for the best price.
        Returns prices ranked highest to lowest.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "e.g. Corn, Soybeans"
                },
                "locations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of locations e.g. ['iowa', 'illinois', 'nebraska']"
                }
            },
            "required": ["commodity", "locations"]
        }
    },
    {
        "name": "search_ams_any",
        "description": """Search USDA AMS Market News for ANY agricultural commodity.
        Use when someone asks about livestock, dairy, poultry, eggs, cotton,
        tobacco, wool — anything beyond grain prices.
        Examples: cattle prices, hog prices, milk prices, egg prices,
        broiler prices, sheep prices, turkey prices, wool prices.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "Any commodity e.g. cattle, hogs, milk, eggs, cotton, broilers, sheep, wool, turkey"
                },
                "location": {
                    "type": "string",
                    "description": "Optional location e.g. Omaha, Kansas City, national"
                }
            },
            "required": ["commodity"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute whichever tool Claude decided to call."""
    try:
        if tool_name == "get_nass_data":
            result = get_nass_data(
                commodity=tool_input["commodity"],
                statistic=tool_input["statistic"],
                state=tool_input["state"],
                year=tool_input["year"]
            )
        elif tool_name == "query_nass_flexible":
            result = query_nass_flexible(
                commodity=tool_input["commodity"],
                statistic=tool_input["statistic"],
                state=tool_input.get("state"),
                year=tool_input.get("year"),
                year_gte=tool_input.get("year_gte"),
                year_lte=tool_input.get("year_lte"),
                agg_level=tool_input.get("agg_level", "STATE"),
                unit=tool_input.get("unit")
            )
        elif tool_name == "get_ams_price":
            result = get_ams_price(
                commodity=tool_input["commodity"],
                location=tool_input.get("location", "iowa")
            )
        elif tool_name == "get_ams_price_comparison":
            result = get_ams_price_comparison(
                commodity=tool_input["commodity"],
                locations=tool_input["locations"]
            )
        elif tool_name == "search_ams_any":
            result = search_ams_any(
                commodity=tool_input["commodity"],
                location=tool_input.get("location")
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return json.dumps(result)

    except Exception as e:
        return json.dumps({"error": str(e)})

import time

def ask_claude(question: str, message_history: list) -> tuple[str, list]:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    system = """You are a USDA agricultural data assistant helping American farmers
    and researchers access crop and commodity data. You have access to two USDA data sources:

    1. NASS QuickStats — historical crop data (yield, acreage, production, prices received by farmers)
    2. AMS Market News — current live market prices for grains, livestock, dairy, poultry, eggs, cotton, and more

    Always use the tools to get real data. Never guess or make up numbers.
    Be concise and lead with the key number or finding.
    When comparing prices across locations, clearly recommend the best option.
    Always mention the data source and date in your response.
    If a tool returns an error, explain clearly what data is not available and why.
    Remember context from earlier in the conversation — if the user says
    'how about Illinois' after asking about Iowa corn, they mean the same
    commodity and statistic but for Illinois."""

    messages = message_history + [{"role": "user", "content": question}]

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            while True:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system,
                    tools=TOOLS,
                    messages=messages
                )

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            messages.append({
                                "role": "assistant",
                                "content": block.text
                            })
                            return block.text, messages
                    return "I couldn't find data for that question.", messages

                if response.stop_reason == "tool_use":
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = execute_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })

                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                else:
                    return "Unexpected response. Please try again.", messages

        except Exception as e:
            if "overloaded" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            return f"The AI service is temporarily busy. Please try again in a moment.", messages


# ── HEADER ────────────────────────────────────────────────────────────────
st.markdown("<h1>🌾 USDA Agricultural Intelligence</h1>", unsafe_allow_html=True)
st.markdown(
    '<p class="tagline">Real-time crop prices and historical data for American farmers — '
    'powered by USDA NASS QuickStats and AMS Market News</p>',
    unsafe_allow_html=True
)

# ── SECTION 1: LIVE MARKET PRICES ─────────────────────────────────────────
st.markdown(
    '<h2>Today\'s Grain Prices <span class="live-badge">● LIVE</span></h2>',
    unsafe_allow_html=True
)
st.caption("Pulled live from USDA AMS Market News on page load")

STATES = [
    "iowa", "illinois", "kansas", "nebraska", "minnesota",
    "indiana", "ohio", "missouri", "north dakota", "texas"
]
STATE_LABELS = [
    "Iowa", "Illinois", "Kansas", "Nebraska", "Minnesota",
    "Indiana", "Ohio", "Missouri", "N. Dakota", "Texas"
]


@st.cache_data(ttl=300)
def load_market_prices():
    corn = get_ams_price_comparison("Corn",     STATES)
    soy  = get_ams_price_comparison("Soybeans", STATES)
    return corn, soy


with st.spinner("Fetching live prices from USDA..."):
    corn_data, soy_data = load_market_prices()

corn_prices = {r["region"]: r.get("avg_price") for r in corn_data if "error" not in r}
soy_prices  = {r["region"]: r.get("avg_price") for r in soy_data  if "error" not in r}
corn_vals   = [corn_prices.get(s) for s in STATES]
soy_vals    = [soy_prices.get(s)  for s in STATES]

fig = go.Figure()
fig.add_trace(go.Bar(
    name="Corn",
    x=STATE_LABELS,
    y=corn_vals,
    marker_color="#2d6a35",
    text=[f"${v:.2f}" if v else "N/A" for v in corn_vals],
    textposition="outside",
    textfont=dict(size=11, color="#1a3d1f")
))
fig.add_trace(go.Bar(
    name="Soybeans",
    x=STATE_LABELS,
    y=soy_vals,
    marker_color="#c8a84b",
    text=[f"${v:.2f}" if v else "N/A" for v in soy_vals],
    textposition="outside",
    textfont=dict(size=11, color="#1a3d1f")
))
fig.update_layout(
    barmode="group",
    plot_bgcolor="#f7f5f0",
    paper_bgcolor="#f7f5f0",
    yaxis=dict(title="$ per bushel", gridcolor="#e0d9c8", tickprefix="$"),
    xaxis=dict(gridcolor="#e0d9c8"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=40, b=20, l=10, r=10),
    height=400,
    font=dict(family="Source Sans 3", color="#1a3d1f")
)
st.plotly_chart(fig, use_container_width=True)

cols = st.columns(len(STATES))
for i, (state, label) in enumerate(zip(STATES, STATE_LABELS)):
    corn_v = corn_prices.get(state)
    soy_v  = soy_prices.get(state)
    with cols[i]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div style="font-size:0.8rem;color:#5a7a5f;margin-top:0.3rem;">
                🌽 Corn<br>
                <span style="font-size:1.1rem;font-weight:700;color:#2d6a35;">
                    {"${:.2f}".format(corn_v) if corn_v else "—"}
                </span>
            </div>
            <div style="font-size:0.8rem;color:#5a7a5f;margin-top:0.5rem;">
                🫘 Soybeans<br>
                <span style="font-size:1.1rem;font-weight:700;color:#c8a84b;">
                    {"${:.2f}".format(soy_v) if soy_v else "—"}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── SECTION 2: HISTORICAL LOOKUP ──────────────────────────────────────────
st.markdown("<h2>Historical Crop Data</h2>", unsafe_allow_html=True)
st.caption("Source: USDA NASS QuickStats — any crop, any state, back to 1997")

STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

COMMODITIES = sorted([
    "BARLEY", "CANOLA", "CORN", "COTTON", "FLAXSEED",
    "HAY", "OATS", "PEANUTS", "POTATOES", "RICE",
    "RYE", "SOYBEANS", "SORGHUM FOR GRAIN", "SUGARBEETS",
    "SUGARCANE", "SUNFLOWER", "SWEET POTATOES", "TOBACCO", "WHEAT"
])

col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])
with col1:
    state_name = st.selectbox(
        "State",
        list(STATE_CODES.keys()),
        index=list(STATE_CODES.keys()).index("Iowa")
    )
with col2:
    commodity = st.selectbox("Commodity", COMMODITIES)
with col3:
    year = st.selectbox("Year", list(range(2024, 1996, -1)), index=2)
with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    lookup = st.button("Look Up")

if lookup:
    state_code = STATE_CODES[state_name]
    with st.spinner(f"Fetching {commodity} data for {state_name} {year}..."):
        area   = get_nass_data(commodity, "AREA PLANTED",   state_code, year)
        yield_ = get_nass_data(commodity, "YIELD",          state_code, year)
        prod   = get_nass_data(commodity, "PRODUCTION",     state_code, year)
        price  = get_nass_data(commodity, "PRICE RECEIVED", state_code, year)

    metrics = [
        ("Area Planted",   area,   "ACRES"),
        ("Yield",          yield_, "BU / ACRE"),
        ("Production",     prod,   "BU"),
        ("Price Received", price,  "$ / BU"),
    ]

    mcols = st.columns(4)
    for i, (label, data, unit) in enumerate(metrics):
        with mcols[i]:
            if isinstance(data, dict) and "error" not in data:
                raw = data.get("value", "—")
                try:
                    num = float(str(raw).replace(",", ""))
                    val = f"${num:.2f}" if "PRICE" in label.upper() else f"{num:,.0f}"
                except:
                    val = raw
            else:
                val = "No data"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val}</div>
                <div style="color:#5a7a5f;font-size:0.8rem;margin-top:0.3rem;">{unit}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(
        f'<span class="source-tag">USDA NASS QuickStats — {state_name} {commodity} {year}</span>',
        unsafe_allow_html=True
    )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── SECTION 3: CONVERSATIONAL Q&A ─────────────────────────────────────────
st.markdown("<h2>Ask a Question</h2>", unsafe_allow_html=True)
st.caption("Any agricultural question — grains, livestock, dairy, poultry, cotton, and more")

# clear button
if st.button("Clear conversation", key="clear_btn"):
    st.session_state.chat_history = []
    st.session_state.messages     = []
    st.rerun()

# display full conversation history
for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        st.markdown(f"""
        <div class="user-bubble">
            <span>{chat["content"]}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="answer-box">{chat["content"]}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<span class="source-tag">📊 USDA NASS QuickStats + AMS Market News</span>',
            unsafe_allow_html=True
        )

# claude-style chat input — clears automatically, Enter or arrow to submit
question = st.chat_input("Ask anything about US agriculture...")

if question:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.warning("Anthropic API key not configured. Add ANTHROPIC_API_KEY to your .env file.")
    else:
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        with st.spinner("Searching USDA data..."):
            answer, updated_messages = ask_claude(
                question,
                st.session_state.messages
            )

        st.session_state.messages = updated_messages

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer
        })

        st.rerun()

# ── FOOTER ─────────────────────────────────────────────────────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown(
    '<p style="color:#5a7a5f;font-size:0.8rem;text-align:center;">'
    'Data sourced from USDA NASS QuickStats and USDA AMS Market News · '
    'Built for USDA Challenge X Hackathon 2026 · Team Root Access'
    '</p>',
    unsafe_allow_html=True
)