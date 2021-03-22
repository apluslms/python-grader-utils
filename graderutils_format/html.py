"""
Render "Grading feedback" JSON schema objects into HTML using Jinja2 templates.
"""
import argparse
import json
import os
import sys

import jinja2
import jsonschema

from graderutils import schemaobjects


def _load_template(loader, name):
    return jinja2.Environment(loader=loader, trim_blocks=True, lstrip_blocks=True).get_template(name)


def _load_template_file(template_paths, name):
    file_loader = jinja2.FileSystemLoader(template_paths)
    return _load_template(file_loader, name)


def _load_package_template(name):
    package_loader = jinja2.PackageLoader("graderutils_format", "templates")
    return _load_template(package_loader, name)


def grading_data_to_html(grading_data, extends_base=False, grader_container=False):
    """
    Format a "Grading feedback" JSON schema object as HTML.
    """
    # Get default feedback template
    feedback_template = _load_package_template("feedback.html")
    if "feedback_template" in grading_data:
        # Extend default template with given custom template
        custom_template = grading_data["feedback_template"]
        grading_data["feedback_template"] = feedback_template
        template_paths = ["./"]
        if grader_container and "PYTHONPATH" in os.environ:
            # If running in grade-python, custom templates are expected to be in the exercise dir specified by PYTHONPATH
            template_paths.append(os.environ["PYTHONPATH"])
        feedback_template = _load_template_file(template_paths, custom_template)
    return feedback_template.render(**grading_data, extends_base=extends_base)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSON grading feedback to HTML converter")
    parser.add_argument("--verbose", '-v',
        action="store_true",
        help="Show validation errors"
    )
    parser.add_argument("--grader-container",
        action="store_true",
        help="Print points and max points to stdout after HTML output."
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
            print("Input does not conform to JSON schema 'Grading feedback'. Run graderutils_format.html with --verbose to show full validation error.")
            sys.exit(1)
    # Input is valid, render to html
    html_feedback = grading_data_to_html(grading_data, args.full_document, args.grader_container)
    print(html_feedback)
    if args.grader_container:
        print("TotalPoints: {}\nMaxPoints: {}".format(grading_data.get("points", 0), grading_data.get("maxPoints", 0)))
