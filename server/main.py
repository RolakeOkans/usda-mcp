import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from clients.nass_client import get_nass_data, query_nass_flexible

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("usda-nass-server")

# create the server
server = Server("usda-nass")

@server.list_tools()
async def list_tools():
    logger.info("Tools list requested")
    return [
        types.Tool(
            name="get_nass_data",
            description="""Get USDA agricultural data for corn and soybeans.
            Use this when someone asks about crop yield, acres planted,
            production, or price received for corn or soybeans in any US state.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "The crop: CORN or SOYBEANS"
                    },
                    "statistic": {
                        "type": "string",
                        "description": "What to measure: AREA PLANTED, YIELD, PRODUCTION, or PRICE RECEIVED"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two letter state code e.g. IA for Iowa, IL for Illinois"
                    },
                    "year": {
                        "type": "integer",
                        "description": "The year e.g. 2022"
                    }
                },
                "required": ["commodity", "statistic", "state", "year"]
            }
        ),
        types.Tool(
            name="query_nass_flexible",
            description="""Flexible USDA NASS query for any agricultural question.
            Use this for:
            - Any crop beyond corn and soybeans e.g. WHEAT, COTTON, SORGHUM
            - Trend questions spanning multiple years e.g. 2018 to 2022
            - National level data not specific to one state
            - County level data
            - Area harvested vs area planted
            - Inventory data
            - Any question the basic get_nass_data tool cannot answer""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "The crop e.g. CORN, SOYBEANS, WHEAT, COTTON, SORGHUM"
                    },
                    "statistic": {
                        "type": "string",
                        "description": "What to measure e.g. AREA PLANTED, AREA HARVESTED, YIELD, PRODUCTION, PRICE RECEIVED, INVENTORY"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two letter state code e.g. IA. Leave empty for national data."
                    },
                    "year": {
                        "type": "integer",
                        "description": "Specific year e.g. 2022. Use year_gte and year_lte for ranges."
                    },
                    "year_gte": {
                        "type": "integer",
                        "description": "Get data from this year onwards e.g. 2018 for trends"
                    },
                    "year_lte": {
                        "type": "integer",
                        "description": "Get data up to this year e.g. 2022 for trends"
                    },
                    "agg_level": {
                        "type": "string",
                        "description": "Geographic level: STATE, NATIONAL, or COUNTY. Default is STATE."
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement e.g. ACRES, BU, BU / ACRE. Leave empty to auto-detect."
                    }
                },
                "required": ["commodity", "statistic"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    if name == "get_nass_data":
        result = get_nass_data(
            commodity=arguments["commodity"],
            statistic=arguments["statistic"],
            state=arguments["state"],
            year=arguments["year"]
        )
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=str(result))]

    if name == "query_nass_flexible":
        result = query_nass_flexible(
            commodity=arguments["commodity"],
            statistic=arguments["statistic"],
            state=arguments.get("state"),
            year=arguments.get("year"),
            year_gte=arguments.get("year_gte"),
            year_lte=arguments.get("year_lte"),
            agg_level=arguments.get("agg_level", "STATE"),
            unit=arguments.get("unit")
        )
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=str(result))]

    logger.warning(f"Unknown tool called: {name}")
    return [types.TextContent(type="text", text="Unknown tool")]

async def main():
    logger.info("Starting USDA NASS MCP Server")
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())