#!/bin/bash
VENV_NAME=venv
CUR_DIR=`dirname $0`
cd $CUR_DIR/$VENV_NAME/lib/python3.9/site-packages/
zip -r ../../../../deployment-packages.zip .
cd ../../../../
zip -g deployment-packages.zip lambda_function.py
