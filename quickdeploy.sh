#!/usr/bin/env bash

pip3.6 install -t lib -r requirements.txt
gcloud app deploy
