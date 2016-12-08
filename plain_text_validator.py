import sys
import re
import htmlgenerator
import test_config


def validate_plain_text(file_data, blacklist, missing_attribute_name):
    """
    Validates the contents of a plain text file.
    """
    with open(file_data["name"]) as f:
        content = [line.strip().lower() for line in f.readlines()]

    errors = dict()
    missing_required_names = []
    used_forbidden_names = []

    for required_name in map(str.lower, file_data.get("required", set())):
        pattern = re.compile(required_name)
        if not re.findall(pattern, "".join(content)):
            missing_required_names.append({
                "type": missing_attribute_name,
                "attribute_name": required_name
            })

    if missing_required_names:
        errors["attribute_errors"] = missing_required_names

    for forbidden_name in map(str.lower, blacklist):
        pattern = re.compile(forbidden_name)
        for line_no, line in enumerate(content):
            matches = re.findall(pattern, line)
            if matches:
                used_forbidden_names.append({
                    "name": forbidden_name,
                    "lineno": line_no,
                    "line_content": line
                })

    if used_forbidden_names:
        errors["forbidden_names"] = used_forbidden_names

    return errors


def get_validation_errors():
    if not hasattr(test_config, "MODULE"):
        raise RuntimeError("ERROR: No module name and/or module attributes defined in test_config.py.")

    MODULE = test_config.MODULE

    # Get set of blacklisted names or an empty set if there are none in test_config
    BLACKLIST = getattr(test_config, "BLACKLIST", set())

    validation_errors = validate_plain_text(MODULE, BLACKLIST, "SQL statement")

    return validation_errors


if __name__ == "__main__":

    validation_errors = get_validation_errors()

    if validation_errors:
        # Render dict with html template
        html_errors = htmlgenerator.errors_as_html(validation_errors)
        print(html_errors, file=sys.stderr)

        # Signal MOOC grader of errors
        sys.exit(1)

