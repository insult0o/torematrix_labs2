from typing import Dict, Any
import json

COORDINATES_SCHEMA = {
    "type": "object",
    "properties": {
        "layout_bbox": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 4,
                    "maxItems": 4
                }
            ]
        },
        "text_bbox": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 4,
                    "maxItems": 4
                }
            ]
        },
        "points": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    }
                }
            ]
        },
        "system": {
            "type": "string",
            "enum": ["pixel", "point", "normalized"]
        }
    }
}

METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "coordinates": {
            "anyOf": [
                {"type": "null"},
                COORDINATES_SCHEMA
            ]
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "detection_method": {"type": "string"},
        "page_number": {
            "anyOf": [
                {"type": "null"},
                {"type": "integer", "minimum": 0}
            ]
        },
        "languages": {
            "type": "array",
            "items": {"type": "string"}
        },
        "custom_fields": {
            "type": "object"
        }
    }
}

def validate_metadata(metadata: Dict[str, Any]) -> bool:
    from jsonschema import validate, ValidationError
    try:
        validate(instance=metadata, schema=METADATA_SCHEMA)
        return True
    except ValidationError:
        return False