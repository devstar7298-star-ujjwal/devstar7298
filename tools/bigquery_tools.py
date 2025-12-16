from google.cloud import bigquery
import os
import logging

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())

BIGQUERY_PROJECT_ID = os.environ.get("BIGQUERY_PROJECT_ID")
if not BIGQUERY_PROJECT_ID:
    logging.error("BIGQUERY_PROJECT_ID environment variable not set. Defaulting to ccibt-hack25ww7-729.")
    BIGQUERY_PROJECT_ID = "ccibt-hack25ww7-729"

client = bigquery.Client(project=BIGQUERY_PROJECT_ID)

def get_demographics_by_zip(zip_code: str) -> dict:
    """
    Tool to query BigQuery Public Datasets (e.g., ACS) for demographic information.
    """
    if not zip_code:
        logging.warning("Demographic query failed: Zip code is required.")
        return {"error": "Zip code is required for demographic query."}

    query = f"""
    SELECT
        sum(total_pop) as total_population_2020,
        avg(median_income) as median_household_income_2020,
        sum(households) as total_households_2020,
        avg(median_rent) as median_rent_2020
    FROM
        `bigquery-public-data.census_bureau_acs.zip_code_2020_5yr`
    WHERE
        geo_id = '{zip_code}'
    GROUP BY
        geo_id
    """

    try:
        logging.info(f"Executing BigQuery demographic query for zip: {zip_code}")
        query_job = client.query(query)
        results = [dict(row) for row in query_job] # Convert Row objects to dicts
        if results:
            logging.info(f"Demographics found for {zip_code}.")
            return {"demographics": results[0]}
        else:
            logging.warning(f"No demographics found for zip code: {zip_code} in public datasets.")
            return {"demographics": "No data found for this zip code in public datasets."}
    except Exception as e:
        logging.error(f"BigQuery demographic query failed for zip '{zip_code}': {e}", exc_info=True)
        return {"error": f"BigQuery demographic query failed: {e}."}

def find_comparable_properties_in_bq(
    city: str,
    state: str,
    property_type: str = None,
    min_sqft: float = None,
    max_price: float = None,
    limit: int = 5
) -> dict:
    """
    Tool to find comparable commercial properties from your custom BigQuery table.
    """
    if not city or not state:
        logging.warning("Comparable properties query failed: City and State are required.")
        return {"error": "City and State are required to find comparables."}

    # Your custom table name, assumed to be in cre_data dataset
    custom_table_id = f"`{BIGQUERY_PROJECT_ID}.cre_data.commercial_comparables`"

    query = f"""
    SELECT
        property_type, price, beds, baths, sqft, address, city, state, zip_code, year_built
    FROM
        {custom_table_id}
    WHERE
        LOWER(city) = LOWER('{city}') AND LOWER(state) = LOWER('{state}')
    """
    if property_type:
        query += f" AND LOWER(property_type) = LOWER('{property_type}')"
    if min_sqft is not None: # Use is not None to handle 0
        query += f" AND sqft >= {min_sqft}"
    if max_price is not None:
        query += f" AND price <= {max_price}"

    query += f" ORDER BY price DESC LIMIT {limit}"

    try:
        logging.info(f"Executing BigQuery comparables query for {city}, {state} (Type: {property_type}).")
        query_job = client.query(query)
        results = [dict(row) for row in query_job] # Convert Row objects to dicts
        if results:
            logging.info(f"Found {len(results)} comparable properties.")
            return {"comparable_properties": results}
        else:
            logging.warning(f"No comparable properties found for {city}, {state} with specified criteria.")
            return {"comparable_properties": "No comparable properties found for the given criteria."}
    except Exception as e:
        logging.error(f"BigQuery comparables query failed for {city}, {state}: {e}", exc_info=True)
        return {"error": f"BigQuery comparables query failed: {e}."}
