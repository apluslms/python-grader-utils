"""
Render "Grading feedback" JSON schema objects into HTML using Jinja2 templates.
"""
import argparse
import json
import sys

import jinja2
import jsonschema

from graderutils import schemaobjects


def _load_template(loader, name):
    return jinja2.Environment(loader=loader, trim_blocks=True, lstrip_blocks=True).get_template(name)


def _load_template_file(name):
    file_loader = jinja2.FileSystemLoader("./")
    return _load_template(file_loader, name)


def _load_package_template(name):
    package_loader = jinja2.PackageLoader("graderutils", "static")
    return _load_template(package_loader, name)


def grading_data_to_html(grading_data, custom_template_path):
    """
    Format a "Grading feedback" JSON schema object as HTML.
    """
    # Get default feedback template
    feedback_template = _load_package_template("feedback_template.html")
    if custom_template_path:
        # Extend default template with given custom template
        grading_data["feedback_template"] = feedback_template
        feedback_template = _load_template_file(custom_template_path)
    return feedback_template.render(**grading_data)


def json_to_html(grading_json, custom_template_path=''):
    return grading_data_to_html(json.loads(grading_json), custom_template_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSON grading feedback to HTML converter")
    parser.add_argument("--verbose", '-v',
        action="store_true",
        help="Show validation errors"
    )
    parser.add_argument("--custom-template",
        type=str,
        default='',
        help="Path to a custom HTML template that extends or replaces the default template"
    )
    args = parser.parse_args()
    grading_data = json.load(sys.stdin)
    # Validate given grading json
    schemas = schemaobjects.build_schemas()
    try:
        jsonschema.validate(grading_data, schemas["grading_feedback"]["schema"])
    except jsonschema.ValidationError as e:
        if args.verbose:
            raise
        else:
            print("Input does not conform to JSON schema 'Grading feedback'. Run with --verbose to show full validation error.")
            sys.exit(1)
    # Valid input, render and print to stdout
    print(grading_data_to_html(grading_data, args.custom_template))
