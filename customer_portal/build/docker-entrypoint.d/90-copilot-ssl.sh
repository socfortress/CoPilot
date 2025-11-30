#!/bin/sh
set -e

# This script can be used to configure SSL certificates at runtime
# Only runs if certificates are mounted/available

if [ -f "/etc/nginx/ssl/cert.pem" ] && [ -f "/etc/nginx/ssl/key.pem" ]; then
    echo "SSL certificates found, enabling HTTPS..."

    # Update nginx config to enable SSL
    # This is a placeholder - adjust based on your SSL needs
fi

exit 0
