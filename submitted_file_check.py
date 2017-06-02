"""
Minimal file validation from the command line.
TODO: This could be merged into importvalidator.
"""
import importlib.util
import importlib
import json
import htmlgenerator
import sys
import argparse
import imghdr
import subprocess
import urllib.parse as uparse

# Non-interactive rendering to png
MATPLOTLIB_RENDERER_BACKEND = "AGG"


def get_image_type_errors(image, expected_type):
    errors = {}
    actual_type = imghdr.what(image)

    if actual_type != expected_type:
        errors["image_type_error"] = True
        errors["expected_type"] = expected_type
        errors["actual_type"] = actual_type

    return errors


def get_import_errors(module):
    errors = {}
    try:
        importlib.import_module(module)
    except ImportError as import_error:
        errors["import_error"] = str(import_error)
    except SyntaxError as syntax_error:
        errors["syntax_error"] = syntax_error.text
        errors["lineno"] = syntax_error.lineno
    except TypeError as type_error:
        errors["type_error"] = str(type_error)
    except ValueError as value_error:
        errors["value_error"] = str(value_error)
    except Exception as error:
        errors["misc_error"] = str(error)

    return errors

def get_labview_errors(filename):
    errors = {}
    with open(filename, "rb") as f:
        header = f.read(16)
        if header != b'RSRC\r\n\x00\x03LVINLBVW':
            errors["file_type_error"] = "The file wasn't a proper labVIEW-file"
    return errors

def validate_html(filename):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    html_validator_url = 'https://validator.w3.org/nu/?out=json'
    css_validator_url = 'https://jigsaw.w3.org/css-validator'
    quoted_filename = uparse.quote(filename)
    if filename.endswith('.css'):
        cmd = ["curl", "-H", "Content-Type: text/css; charset=utf-8", "--data-binary", "@{}".format(quoted_filename), css_validator_url]
    else:
        cmd = ["curl", "-H", "Content-Type: text/html; charset=utf-8", "--data-binary", "@{}".format(quoted_filename), html_validator_url]

    mystdout = subprocess.run(cmd, stdout=subprocess.PIPE)
    output = mystdout.stdout.decode('utf-8')

    return output

def get_html_errors(filename):
    errors = {}
    with open(filename, "r") as f:
        err = validate_html(filename)

        #edit strings so that browser interprets html tags as a raw text
        err = err.replace("<", "&#60")
        err = err.replace(">", "&#62")
        if err:
            errors["html_style_error"] = err
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--python")
    parser.add_argument("--image")
    parser.add_argument("--labview")
    parser.add_argument("--html")
    parser.add_argument("--css")
    parser.add_argument("--xlsx")
    parser.add_argument("--pdf")
    args = parser.parse_args()

    errors = None

    if args.python:
        import matplotlib
        matplotlib.use(MATPLOTLIB_RENDERER_BACKEND)
        module_name = args.python.split(".py")[0]
        errors = get_import_errors(module_name)
    elif args.image:
        image_file = args.image
        image_type = image_file.split(".")[-1]
        errors = get_image_type_errors(image_file, image_type)
    elif args.labview:
        filename = args.labview
        errors = get_labview_errors(filename)
    elif args.html:
        filename = args.html
        errors = get_html_errors(filename)
    elif args.css:
        filename = args.css
        errors = {}
    elif args.xlsx:
        filename = args.xlsx
        errors = {}
    elif args.pdf:
        filename = args.pdf
        errors = {}

    if errors:
        print(htmlgenerator.errors_as_html(errors), file=sys.stderr)
        sys.exit(1)
