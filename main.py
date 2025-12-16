from flask import Flask, request, jsonify
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Part, Tool
import os
import logging

# Import your custom tools
from tools.validation_tools import validate_address
from tools.maps_tools import get_geocode_and_place_id, get_aerial_view_insights
from tools.bigquery_tools import get_demographics_by_zip, find_comparable_properties_in_bq

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "ccibt-hack25ww7-729")
REGION = os.environ.get("GCP_REGION", "us-central1") # Or your chosen region
# Using gemini-1.5-pro-preview-0409 for advanced reasoning and larger context window.
# If not available or for lower cost/faster responses, try "gemini-pro"
VERTEX_AI_MODEL_NAME = "gemini-2.5-flash-preview-09-2025" 

# --- Setup Logging ---
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialize Vertex AI ---
try:
    aiplatform.init(project=PROJECT_ID, location=REGION)
    model = GenerativeModel(VERTEX_AI_MODEL_NAME)
    logger.info(f"Vertex AI initialized with project '{PROJECT_ID}' in region '{REGION}'. Using model '{VERTEX_AI_MODEL_NAME}'.")
except Exception as e:
    logger.critical(f"Failed to initialize Vertex AI: {e}", exc_info=True)
    # Re-raise to prevent deployment if Vertex AI cannot be initialized
    raise SystemExit(f"Vertex AI initialization failed: {e}")

# --- Define the ADK Tools for Gemini ---
# Register your Python functions as tools that Gemini can call
validation_tool = Tool(function_declarations=[validate_address])

maps_tool = Tool(
    function_declarations=[
        get_geocode_and_place_id,
        get_aerial_view_insights
    ]
)

bigquery_tool = Tool(
    function_declarations=[
        get_demographics_by_zip,
        find_comparable_properties_in_bq
    ]
)

# Combine all tools for the agent to use
available_tools = [validation_tool, maps_tool, bigquery_tool]
logger.info(f"Agent initialized with {len(available_tools)} tool sets.")

# --- Flask App for Cloud Run ---
app = Flask(__name__)

@app.route("/", methods=["POST"])
def analyze_property():
    """
    Handles POST requests to analyze a property and generate a deal memo.
    Expects a JSON payload like: {"address": "123 Main St, Anytown, CA 90210"}
    """
    try:
        data = request.get_json(silent=True) # silent=True to avoid error on empty body
        if not data:
            logger.warning("Received empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload or empty request body."}), 400

        property_address = data.get("address")

        if not property_address:
            logger.warning("Missing 'address' in request payload.")
            return jsonify({"error": "Missing 'address' in request payload."}), 400

        logger.info(f"Received request to analyze: {property_address}")

        # --- Gemini Agent Orchestration ---
        # The main prompt that guides Gemini to use its tools and generate the memo
        prompt_template = """
        You are an expert commercial real estate loan analysis agent named 'CRE-Analyst-AI'. Your task is to generate
        a comprehensive deal memo for the following property, leveraging your available tools to gather all necessary information.

        Property for Analysis: {property_address}

        Follow these steps meticulously, using your tools where appropriate:

        1.  **Validate Address:** First, use your `validate_address` tool to perform a basic check on the provided address. If the address is deemed invalid, immediately stop and return an error message explaining why.
        2.  **Gather Property Details:** If the address is valid, use your `get_geocode_and_place_id` tool to obtain its precise geographic coordinates (latitude, longitude), Place ID, and parsed address components (city, state, zip_code). Then, use `get_aerial_view_insights` to get any available aerial information or a visual inspection link.
        3.  **Analyze Demographics:** Use the `get_demographics_by_zip` tool (with the zip code from geocoding) to gather key demographic statistics for the area from BigQuery public datasets.
        4.  **Find Comparables:** Use the `find_comparable_properties_in_bq` tool (with the city and state from geocoding) to retrieve up to 5 relevant comparable commercial properties from your custom BigQuery dataset. Infer a broad 'property_type' if possible, or state if it's unknown.
        5.  **Synthesize and Generate Memo:** Once all information is gathered, synthesize it into a professional, data-driven, and actionable deal memo. Structure the memo with the following sections, ensuring all relevant gathered data is incorporated:

            *   **Executive Summary:** A concise overview summarizing the property, key market insights, potential risks, and a high-level valuation perspective.
            *   **Property Overview:** Detailed information about the subject property including its formatted address, geographic coordinates, Google Place ID, and any aerial view insights or links.
            *   **Market and Demographic Analysis:** Key demographic data for the area (e.g., total population, median household income, housing units, median rent). Discuss the implications of these trends for the commercial real estate market.
            *   **Risk Assessment:** Identify potential risks based on location, market data (e.g., population decline, low income), or any insights from aerial views (e.g., proximity to flood zones - if such tools were integrated).
            *   **Collateral Valuation Insights:** Present the findings from the comparable properties search. Discuss average prices, square footage, and how the subject property compares to these. Provide insights that support a valuation perspective (e.g., "based on comps, the property's value appears to be in the range of X to Y").

        If any tool call fails, mention the failure in the memo and explain what data could not be retrieved.
        """
        
        # Pass the property_address into the prompt template
        final_prompt = prompt_template.format(property_address=property_address)

        logger.info("Sending prompt to Gemini with tools.")
        response = model.generate_content(
            Part.from_text(final_prompt),
            tools=available_tools,
            tool_config={"function_calling_config": "AUTO"}
        )

        # Extract the final generated memo from Gemini's response
        generated_memo = ""
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    generated_memo += part.text
                elif hasattr(part, 'function_call'):
                    # This should ideally not happen for the *final* memo content,
                    # but if it does, it's good to log for debugging.
                    logger.warning(f"Gemini's final response contained an unexpected function_call: {part.function_call}")
                    generated_memo += f"\n\n**[Warning: Agent attempted to call a tool in final response unexpectedly: {part.function_call.name}]**\n\n"
        
        if not generated_memo.strip(): # Check if memo is empty or just whitespace
            logger.error("Gemini returned an empty or nearly empty deal memo.")
            return jsonify({"error": "Agent failed to generate a comprehensive memo. Gemini's output was empty."}), 500

        logger.info("Deal memo generated successfully.")
        return jsonify({"deal_memo": generated_memo}), 200

    except Exception as e:
        logger.exception("An unexpected error occurred during property analysis request.")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
