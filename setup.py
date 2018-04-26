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
    long_description = f.read()

setup(
    name='graderutils',
    version='2.6.0',
    description='Utilities for Python based grader test pipelines',
    long_description=long_description,

    url='https://github.com/Aalto-LeTech/python-grader-utils',
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
        'PyYAML',       # Parse configuration files
        'Jinja2',       # Render HTML feedback with templates
        'html5lib',     # Parse HTML
        'hypothesis',   # Generics for UnitTests
    ],

)
