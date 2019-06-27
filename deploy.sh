#!/bin/bash

# NOTE: To actually perform the twine upload, you'll need access to the PyPi.org account.
python setup.py clean && \
python setup.py build && \
python setup.py test && \
pip install wheel && python setup.py sdist bdist_wheel && \
pip install twine && python -m twine upload --repository-url https://upload.pypi.org/legacy/ dist/*
