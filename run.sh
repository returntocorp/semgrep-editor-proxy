#!/usr/bin/env bash

poetry build
docker build -t lsp_image . -f Dockerfile

