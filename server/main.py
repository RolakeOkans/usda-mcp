import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from clients.nass_client import get_nass_data, query_nass_flexible
from clients.ams_client import get_ams_price, get_ams_price_comparison, search_ams_any
from server.security import (
    check_rate_limit,
    validate_nass_inputs,
    validate_ams_inputs,
    check_for_prompt_injection,
    redact_sensitive_data,
    log_security_summary
)

# logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "usda_nass_server.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("usda-nass-server")
logger.info(f"Logging to file: {log_file}")

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
            - Any crop beyond corn and soybeans e.g. WHEAT, COTTON, SORGHUM FOR GRAIN
            - Trend questions spanning multiple years e.g. 2018 to 2022
            - National level data not specific to one state
            - County level data
            - Area harvested vs area planted
            - Inventory data""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "The crop e.g. CORN, SOYBEANS, WHEAT, SORGHUM FOR GRAIN, COTTON"
                    },
                    "statistic": {
                        "type": "string",
                        "description": "e.g. AREA PLANTED, AREA HARVESTED, YIELD, PRODUCTION, PRICE RECEIVED, INVENTORY"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two letter state code e.g. IA. Leave empty for national data."
                    },
                    "year": {
                        "type": "integer",
                        "description": "Specific year e.g. 2022"
                    },
                    "year_gte": {
                        "type": "integer",
                        "description": "Get data from this year onwards e.g. 2018"
                    },
                    "year_lte": {
                        "type": "integer",
                        "description": "Get data up to this year e.g. 2022"
                    },
                    "agg_level": {
                        "type": "string",
                        "description": "STATE, NATIONAL, or COUNTY"
                    },
                    "unit": {
                        "type": "string",
                        "description": "e.g. ACRES, BU, BU / ACRE"
                    }
                },
                "required": ["commodity", "statistic"]
            }
        ),
        types.Tool(
            name="get_ams_price",
            description="""Get current grain market prices from USDA AMS Market News.
            Use when someone asks about today's price or current market price
            for grain commodities like corn, soybeans, wheat, oats, sorghum.
            Available locations: iowa, illinois, kansas, nebraska, minnesota,
            indiana, ohio, missouri, texas, north dakota, south dakota,
            arkansas, tennessee, kentucky, virginia, pennsylvania,
            colorado, california, minneapolis.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "The grain e.g. Corn, Soybeans, Wheat, Oats, Sorghum"
                    },
                    "location": {
                        "type": "string",
                        "description": "US state or market region e.g. iowa, kansas, minneapolis"
                    }
                },
                "required": ["commodity"]
            }
        ),
        types.Tool(
            name="get_ams_price_comparison",
            description="""Compare current grain prices across multiple locations.
            Use when a farmer wants to know where to sell for the best price.
            Returns prices ranked highest to lowest.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "The grain e.g. Corn, Soybeans"
                    },
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of locations e.g. ['iowa', 'illinois', 'nebraska']"
                    }
                },
                "required": ["commodity", "locations"]
            }
        ),
        types.Tool(
            name="search_ams_any",
            description="""Search USDA AMS Market News for ANY agricultural commodity.
            Use this when someone asks about commodities not covered by grain prices:
            - Livestock prices (cattle, hogs, sheep, goats)
            - Poultry prices (broilers, turkeys, chickens)
            - Dairy prices (milk, cheese, butter, cream)
            - Egg prices
            - Cotton prices
            - Tobacco prices
            - Wool prices
            - Any other commodity AMS reports on""",
            inputSchema={
                "type": "object",
                "properties": {
                    "commodity": {
                        "type": "string",
                        "description": "Any agricultural commodity e.g. cattle, hogs, milk, eggs, cotton, tobacco, broilers, sheep, wool"
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional location filter e.g. Omaha, Kansas City, national"
                    }
                },
                "required": ["commodity"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    logger.info(f"Tool called: {name} with arguments: {redact_sensitive_data(arguments)}")

    if not check_rate_limit(name):
        return [types.TextContent(type="text", text=str({
            "error": "Rate limit exceeded. Please wait a moment before trying again."
        }))]

    if name == "get_nass_data":
        error = validate_nass_inputs(
            commodity=arguments.get("commodity", ""),
            statistic=arguments.get("statistic", ""),
            state=arguments.get("state"),
            year=arguments.get("year")
        )
        if error:
            logger.warning(f"Input validation failed: {error}")
            return [types.TextContent(type="text", text=str(error))]

        result = get_nass_data(
            commodity=arguments["commodity"],
            statistic=arguments["statistic"],
            state=arguments["state"],
            year=arguments["year"]
        )
        result_str = str(result)
        if check_for_prompt_injection(result_str):
            logger.warning("Prompt injection detected in NASS response — blocking")
            return [types.TextContent(type="text", text=str({"error": "Response could not be verified as safe."}))]
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=result_str)]

    if name == "query_nass_flexible":
        error = validate_nass_inputs(
            commodity=arguments.get("commodity", ""),
            statistic=arguments.get("statistic", ""),
            state=arguments.get("state"),
            year=arguments.get("year")
        )
        if error:
            logger.warning(f"Input validation failed: {error}")
            return [types.TextContent(type="text", text=str(error))]

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
        result_str = str(result)
        if check_for_prompt_injection(result_str):
            logger.warning("Prompt injection detected in NASS flexible response — blocking")
            return [types.TextContent(type="text", text=str({"error": "Response could not be verified as safe."}))]
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=result_str)]

    if name == "get_ams_price":
        error = validate_ams_inputs(
            commodity=arguments.get("commodity", ""),
            location=arguments.get("location")
        )
        if error:
            logger.warning(f"Input validation failed: {error}")
            return [types.TextContent(type="text", text=str(error))]

        result = get_ams_price(
            commodity=arguments["commodity"],
            location=arguments.get("location", "iowa")
        )
        result_str = str(result)
        if check_for_prompt_injection(result_str):
            logger.warning("Prompt injection detected in AMS response — blocking")
            return [types.TextContent(type="text", text=str({"error": "Response could not be verified as safe."}))]
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=result_str)]

    if name == "get_ams_price_comparison":
        error = validate_ams_inputs(commodity=arguments.get("commodity", ""))
        if error:
            logger.warning(f"Input validation failed: {error}")
            return [types.TextContent(type="text", text=str(error))]

        result = get_ams_price_comparison(
            commodity=arguments["commodity"],
            locations=arguments["locations"]
        )
        result_str = str(result)
        if check_for_prompt_injection(result_str):
            logger.warning("Prompt injection detected in AMS comparison response — blocking")
            return [types.TextContent(type="text", text=str({"error": "Response could not be verified as safe."}))]
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=result_str)]

    if name == "search_ams_any":
        error = validate_ams_inputs(
            commodity=arguments.get("commodity", ""),
            location=arguments.get("location")
        )
        if error:
            logger.warning(f"Input validation failed: {error}")
            return [types.TextContent(type="text", text=str(error))]

        result = search_ams_any(
            commodity=arguments["commodity"],
            location=arguments.get("location")
        )
        result_str = str(result)
        if check_for_prompt_injection(result_str):
            logger.warning("Prompt injection detected in AMS any response — blocking")
            return [types.TextContent(type="text", text=str({"error": "Response could not be verified as safe."}))]
        logger.info(f"Tool result: {result}")
        return [types.TextContent(type="text", text=result_str)]

    logger.warning(f"Unknown tool called: {name}")
    return [types.TextContent(type="text", text="Unknown tool")]


async def main():
    log_security_summary()
    logger.info("Starting USDA NASS MCP Server")
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())