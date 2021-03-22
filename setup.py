"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    readmefile_contents = f.read()

setup(
    name='graderutils',
    version='3.3.1',
    description='Utilities for Python based grader test pipelines',
    long_description=readmefile_contents,

    url='https://github.com/apluslms/python-grader-utils',
    author='Matias Lindgren',
    author_email='matias.lindgren@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
    ],

    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'PyYAML ~= 3.13',       # Parse configuration files
        'Jinja2 ~= 2.10',       # Render HTML feedback with templates
        'html5lib ~= 1.0',      # Parse HTML
        'hypothesis ~= 3.69',   # Generics for UnitTests
        'jsonschema ~= 2.6',    # Validators for JSON schemas
        'python_jsonschema_objects ~= 0.3.3', # JSON schema to Python object mappings
    ],
)
