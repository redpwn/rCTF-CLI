#!/bin/sh

if [ "$1" = "pip" ]; then
    ./setup.py sdist bdist_wheel
elif [ "$1" = "install" ]; then
    ./setup.py install
fi
