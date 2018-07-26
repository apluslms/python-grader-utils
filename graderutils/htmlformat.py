"""
Render "Grading feedback" JSON schema objects as HTML using Jinja2 templates.
"""
import json
import jinja2


def _load_template(loader, name):
    return jinja2.Environment(loader=loader).get_template(name)


def _load_template_file(name):
    file_loader = jinja2.FileSystemLoader("./")
    return _load_template(file_loader, name)


def _load_package_template(name):
    package_loader = jinja2.PackageLoader("graderutils", "static")
    return _load_template(package_loader, name)


def json_to_html(grading_feedback_json):
    """
    Format a "Grading feedback" JSON schema object as HTML.
    """
    package_loader = jinja2.PackageLoader("graderutils", "static")
    env = jinja2.Environment(loader=package_loader, trim_blocks=True, lstrip_blocks=True)
    default_template = env.get_template("feedback_template.html")
    grading_data = json.loads(grading_feedback_json)
    return default_template.render(**grading_data)
