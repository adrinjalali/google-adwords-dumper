#!/bin/bash

cd ~/Projects/googleads
source ../venv/bin/activate
python sqlalchemy_test.py &> /tmp/gads.log
cat /tmp/gads.log | mail -s "adwords-dump `date`" DWH_DEV@misterspex.de
