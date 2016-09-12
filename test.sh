#!/bin/bash

coverage run --source=mail2vk -m unittest2 discover -p '*.py' -s tests
STATUS=$?
coverage report -m
coveralls --output=coverage.json

if [ $STATUS -ne 0 ]; then
    exit $STATUS
fi
