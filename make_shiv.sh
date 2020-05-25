#!/bin/bash

PROJ=/home/jon/proj/aimslite
virtualenv venv
source venv/bin/activate
pip install $PROJ
deactivate
shiv -c aimsgui -o aims.pyw $PROJ
rm -r venv
