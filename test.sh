#!/bin/bash
coverage run --source=mail2vk -m unittest2 discover -p '*.py' -s tests
coverage report -m
