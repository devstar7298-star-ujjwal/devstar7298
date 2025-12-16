import logging

logging.basicConfig(level=logging.INFO)

def validate_address(address: str) -> dict:
    """
    Validates if an address string appears to be a reasonable input.
    Checks for non-empty and minimum length.
    """
    if not address:
        logging.warning("Validation failed: Address cannot be empty.")
        return {"valid": False, "reason": "Address cannot be empty."}
    if len(address) < 10: # Simple heuristic for a hackathon
        logging.warning(f"Validation failed: Address '{address}' is too short.")
        return {"valid": False, "reason": "Address is too short to be valid."}
    logging.info(f"Address '{address}' appears valid based on basic checks.")
    return {"valid": True, "reason": "Address format appears valid."}
