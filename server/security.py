import re
import time
import logging
from collections import defaultdict

logger = logging.getLogger("usda-nass-server")

# MCP02: Scope is intentionally read-only
# This server has no write access to any USDA system
# Tools only call GET endpoints on public APIs
ALLOWED_OPERATIONS = ["GET"]
SERVER_SCOPE = "read-only"

# MCP10: Server is stateless — no user data persists between calls
# Each tool invocation is fully isolated
SERVER_STATE = "stateless"

# valid values for input validation
VALID_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

VALID_STATISTICS = {
    "AREA PLANTED", "AREA HARVESTED", "YIELD",
    "PRODUCTION", "PRICE RECEIVED", "INVENTORY"
}

VALID_AGG_LEVELS = {"STATE", "NATIONAL", "COUNTY"}

# MCP05: rate limiting — max requests per minute per tool
RATE_LIMIT = 30
_request_counts = defaultdict(list)

# MCP06: patterns that may indicate prompt injection in returned data
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "you are now",
    "new instructions",
    "system prompt",
    "disregard",
    "forget your instructions",
    "override",
    "jailbreak",
    "act as",
]


def check_rate_limit(tool_name: str) -> bool:
    """
    MCP05: Rate limiting — returns True if request is allowed.
    Prevents abuse and protects USDA API keys from being blocked.
    """
    now = time.time()
    window = 60

    _request_counts[tool_name] = [
        t for t in _request_counts[tool_name]
        if now - t < window
    ]

    if len(_request_counts[tool_name]) >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for tool: {tool_name}")
        return False

    _request_counts[tool_name].append(now)
    return True


def sanitize_string(value: str, max_length: int = 100) -> str:
    """
    MCP05: Strip characters that could be used for injection attacks.
    Only allows letters, numbers, spaces, and safe punctuation.
    """
    if not value:
        return ""
    sanitized = re.sub(r'[^a-zA-Z0-9\s/._\-]', '', str(value))
    return sanitized.strip()[:max_length]


def validate_nass_inputs(
    commodity: str,
    statistic: str,
    state: str = None,
    year: int = None
) -> dict | None:
    """
    MCP05: Validate inputs for NASS queries.
    Returns None if valid, or an error dict if invalid.
    """
    commodity = sanitize_string(commodity).upper()
    statistic = sanitize_string(statistic).upper()

    if not commodity:
        return {"error": "Commodity is required"}

    if len(commodity) > 50:
        return {"error": "Commodity name too long"}

    if not statistic:
        return {"error": "Statistic is required"}

    if statistic not in VALID_STATISTICS:
        logger.warning(f"Unusual statistic requested: {statistic}")

    if state:
        state = sanitize_string(state).upper()
        if len(state) != 2 or state not in VALID_STATES:
            return {"error": f"Invalid state code: {state}. Use two letter code like IA or IL"}

    if year:
        if not isinstance(year, int) or year < 1850 or year > 2030:
            return {"error": f"Invalid year: {year}. Must be between 1850 and 2030"}

    return None


def validate_ams_inputs(
    commodity: str,
    location: str = None
) -> dict | None:
    """
    MCP05: Validate inputs for AMS price queries.
    Returns None if valid, or an error dict if invalid.
    """
    commodity = sanitize_string(commodity)

    if not commodity:
        return {"error": "Commodity is required"}

    if len(commodity) > 50:
        return {"error": "Commodity name too long"}

    if location:
        location = sanitize_string(location)
        if len(location) > 50:
            return {"error": "Location name too long"}

    return None


def check_for_prompt_injection(data: str) -> bool:
    """
    MCP06: Scan API response data for prompt injection patterns.
    Returns True if suspicious content is detected.
    Protects against malicious content embedded in USDA data responses.
    """
    data_lower = data.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in data_lower:
            logger.warning(f"Potential prompt injection detected in API response: '{pattern}'")
            return True
    return False


def redact_sensitive_data(data: dict) -> dict:
    """
    MCP01: Remove sensitive fields before logging.
    Ensures API keys and secrets never appear in log files.
    """
    sensitive_keys = {"key", "api_key", "password", "token", "secret", "authorization"}
    return {
        k: "***REDACTED***" if k.lower() in sensitive_keys else v
        for k, v in data.items()
    }


def log_security_summary():
    """
    MCP08: Log server security configuration on startup.
    Provides audit trail of security posture.
    """
    logger.info("=== SECURITY CONFIGURATION ===")
    logger.info(f"Server scope: {SERVER_SCOPE}")
    logger.info(f"Server state: {SERVER_STATE}")
    logger.info(f"Allowed operations: {ALLOWED_OPERATIONS}")
    logger.info(f"Rate limit: {RATE_LIMIT} requests per minute per tool")
    logger.info(f"Input validation: enabled")
    logger.info(f"Prompt injection detection: enabled")
    logger.info(f"Secret redaction in logs: enabled")
    logger.info("==============================")