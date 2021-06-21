"""
Build Python objects from JSON schemas for convenient Python dict JSON schema validation and serialization.
"""
import os.path

import yaml
from python_jsonschema_objects import ObjectBuilder

from graderutils import GraderUtilsError

class SchemaError(GraderUtilsError): pass

SCHEMAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "schemas"))


def build_schemas(schemas_data):
    """
    Build schemas from files and resolve schema dependencies.
    """
    schemas = {}
    classes = {}
    for schema_key, schema_path in schemas_data.items():
        if not os.path.exists(schema_path):
            raise SchemaError("Cannot build JSON schema object {}, schema path does not exist: {}".format(schema_key, schema_path))
        # Load schema file contents
        with open(schema_path) as schema_file:
            schema = yaml.safe_load(schema_file)
        schemas[schema_key] = schema
        # Build all abstract base classes for instantiating the properties of current schema
        classes[schema_key] = ObjectBuilder(schema, resolved=schemas).build_classes()
    # Merge schema dicts and classes under one schema key
    return {key: {"schema": schemas[key], "classes": classes[key]} for key in schemas}


def build_feedback_schemas(version="v1_1"):
    """
    Build all schemas.
    """
    schema_keys = (
        "grading_feedback",
    )
    schemas_data = {key: os.path.join(SCHEMAS_DIR, "{}_{}.yaml".format(key, version)) for key in schema_keys}
    return build_schemas(schemas_data)
