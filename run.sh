#!/usr/bin/env bash

poetry build
docker build -t lsp_image . -f Dockerfile
docker run -p 8000-8004:8000-8004 -P -it lsp_image

