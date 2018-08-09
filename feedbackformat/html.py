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
    package_loader = jinja2.PackageLoader("feedbackformat", "templates")
    return _load_template(package_loader, name)


def grading_data_to_html(grading_data, custom_template_path, extends_base=False):
    """
    Format a "Grading feedback" JSON schema object as HTML.
    """
    # Get default feedback template
    feedback_template = _load_package_template("feedback_template.html")
    if custom_template_path:
        # Extend default template with given custom template
        grading_data["feedback_template"] = feedback_template
        feedback_template = _load_template_file(custom_template_path)
    return feedback_template.render(**grading_data, extends_base=extends_base)


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
    parser.add_argument("--grader-container",
        action="store_true",
        help="Print generated output to stderr instead of stdout. Additionally, print points and max points to stdout."
    )
    parser.add_argument("--full-document",
        action="store_true",
        help="Embed results into a full HTML5 document."
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
    # Input is valid, render to html
    html_feedback = grading_data_to_html(grading_data, args.custom_template, args.full_document)
    if args.grader_container:
        print(html_feedback, file=sys.stderr)
        print("TotalPoints: {}\nMaxPoints: {}".format(grading_data["points"], grading_data["maxPoints"]))
    else:
        print(html_feedback)
