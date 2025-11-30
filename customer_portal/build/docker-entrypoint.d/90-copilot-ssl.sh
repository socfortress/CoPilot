#!/bin/sh

if [[ -z "${SERVER_HOST}" ]]; then
    echo "No SERVER_HOST set!"
    echo "Please set the SERVER_HOST environment variable to use CoPilot"
    exit 1;
else
    echo "Host is now https://${SERVER_HOST}:${SERVER_PORT}"
fi

if [[ ! -f "${TLS_CERT_PATH}" || ! -f "${TLS_KEY_PATH}" ]]; then
    echo "No TLS certs found. Generating...."
    mkdir -p $(dirname "${TLS_CERT_PATH}")
    openssl req -x509 -subj "/CN=${SERVER_HOST}" -nodes -newkey rsa:4096 -keyout "${TLS_KEY_PATH}" -out "${TLS_CERT_PATH}" -days 365
else
    echo "TLS certificates found"
fi

if [[ ! -f /etc/nginx/certs/dhparams.pem ]]; then
    echo "Generating new DH parameters - this may take a while..."
    mkdir -p /etc/nginx/certs/
    openssl dhparam -out /etc/nginx/certs/dhparams.pem 2048
else
    echo "... DH parameters found"
fi
