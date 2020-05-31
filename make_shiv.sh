#!/bin/bash

PROJ=/home/jon/proj/aimslite
virtualenv venv
source venv/bin/activate
pip install $PROJ
shiv -c aimsgui -o aims.pyw $PROJ
deactivate
rm -r venv
