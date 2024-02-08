#!/usr/bin/env bash

openssl genpkey -algorithm RSA -out server.key -aes256
openssl req -new -key server.key -out server.csr
cp server.key no-passphrase.key
openssl rsa -in no-passphrase.key -out server.key
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

