# Use a node.js base image
FROM node:21 as builder

# Install pnpm globally
RUN npm install -g pnpm

# Drop root
USER node

# Set the working directory
WORKDIR /app

# Copy the package.json and pnpm-lock.yaml files into the working directory
COPY package.json pnpm-lock.yaml ./

# Install project dependencies using pnpm
RUN pnpm install

# Copy project files into the working directory
COPY --chown=node . .

# Run the Vue.js project build using pnpm
RUN pnpm run build:only

FROM node:21 as dev

RUN apt-get update && apt-get install -y openssl

RUN mkdir -p /certs &  \
        openssl req -x509 -subj "/CN=localhost" -nodes -newkey rsa:4096 -keyout /certs/key.pem -out /certs/cert.pem -days 365 && \
        chown -R node:node /certs

# Drop root
USER node

# Set the working directory
WORKDIR /app

CMD pnpm install && pnpm run start-frontend

FROM nginx:1.24.0-alpine

# Added to create self-signed cert on run time if needed
RUN apk add openssl

# Set environment variables
ENV SERVER_HOST=localhost
ENV TLS_CERT_PATH=/etc/nginx/certs.d/server.crt
ENV TLS_KEY_PATH=/etc/nginx/certs.d/server.key

# Copy entrypoint
COPY build/docker-entrypoint.d/90-copilot-ssl.sh /docker-entrypoint.d/90-copilot-ssl.sh
RUN chmod +x /docker-entrypoint.d/90-copilot-ssl.sh

# Setup template
RUN mkdir /etc/nginx/templates
COPY build/etc/nginx/sites-enabled/default.conf /etc/nginx/templates/default.conf.template

# Copy built static files from the builder stage
COPY --from=builder /app/dist /var/www/copilot

CMD ["nginx", "-g", "daemon off;"]
