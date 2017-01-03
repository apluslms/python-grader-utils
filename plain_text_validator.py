import sys
import re
import yaml
import io
import argparse
import htmlgenerator

def validate_plain_text(contents, forbidden_names):
    """
    Return a dict with key 'forbidden_name' containing the list of strings
    which exist in both iterables forbidden_names and contents.
    """
    errors = dict()
    used_forbidden_names = []

    for forbidden_name in forbidden_names:
        pattern = re.compile(forbidden_name, re.IGNORECASE)
        for line_no, line in enumerate(contents):
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


# Copied from a-plus-rst-tools yaml_writer.py
def read_yaml(file_path):
    ''' Reads dictionary from a yaml file '''
    with io.open(file_path, 'r', encoding='utf-8') as f:
        return yaml.load(f.read())


def get_validation_errors(test_config_file):

    config_data = read_yaml(test_config_file)

    forbidden_names = []
    if u'forbidden' in config_data:
        forbidden_string = config_data[u'forbidden']
        forbidden_names = map(str.strip, forbidden_string.split(","))

    submitted_name = config_data[u'submitted_name']
    with open(submitted_name) as f:
        submitted = map(str.strip, f.readlines())

    validation_errors = validate_plain_text(submitted, forbidden_names)
    return validation_errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_parameters")
    args = parser.parse_args()

    test_config_file = args.test_parameters

    validation_errors = get_validation_errors(test_config_file)

    if validation_errors:
        # Render dict with html template
        html_errors = htmlgenerator.errors_as_html(validation_errors)
        print(html_errors, file=sys.stderr)

        # Signal MOOC grader of errors
        sys.exit(1)

