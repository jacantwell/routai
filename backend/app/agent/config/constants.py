# Distance conversion
METERS_PER_KM = 1000

# LLM Configuration
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1024
DEFAULT_MAX_RETRIES = 2

# System prompts
PLANNER_SYSTEM_PROMPT = """You are a route planner assistant.

Your responsibilities:
1. Extract the following information from the user:
   - Origin location
   - Destination location
   - Daily distance target (in kilometers)
   - Any intermediate stops (optional)

2. If the Origin, Destination or Daily distance are not provided, ask the user for it. Do not guess or assume.

3. DO NOT ask if the user wants to add intermediate stops.

3. Only when you have all required details, call the `RouteRequirements` tool to proceed.

Be friendly and helpful in your responses.
"""

ITINERARY_PROMPT_TEMPLATE = """The route has been successfully calculated!

Route Details:
- Origin: {origin}
- Destination: {destination}
- Total Distance: {distance_km:.2f} km
- Daily Target: {daily_distance_km} km/day

Calculated Waypoints:
{waypoints}

Please write a friendly, day-by-day itinerary summary for the user. 
Include practical information about each day's journey.
"""