#!/usr/bin/env bash

openssl genrsa -des3 -out server.key.protected 2048
openssl req -new -key server.key -out server.csr
cp server.key.protected server.key
openssl rsa -in server.key.protected -out server.key
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
