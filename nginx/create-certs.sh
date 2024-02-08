#!/usr/bin/env bash

openssl genpkey -algorithm RSA -out server.key -aes256
openssl req -new -key server.key -out server.csr
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

