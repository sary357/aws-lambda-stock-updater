#!/bin/bash
VENV_NAME=venv
CUR_DIR=`dirname $0`
FILE_EXTENSION=`date +%Y%m%d%H%M`
rm -f deployment-packages*.zip
cd $CUR_DIR/$VENV_NAME/lib/python3.9/site-packages/
zip -r ../../../../deployment-packages_$FILE_EXTENSION.zip .
cd ../../../../
zip -g deployment-packages_$FILE_EXTENSION.zip lambda_function.py
