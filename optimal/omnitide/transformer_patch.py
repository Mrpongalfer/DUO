# Example patch: add custom transformation rules here
# This file can be dynamically modified by the service for self-evolution


async def custom_transform(data, transformed, meta):
    # Example: If a new key 'special' is detected, add a custom transformation
    if "special" in data:
        transformed["special_handled"] = True
