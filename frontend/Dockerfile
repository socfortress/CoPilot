# Use a node.js base image
FROM node:21 as builder

# Set the working directory
WORKDIR /

# Copy project files into the working directory
COPY . .

# Install project dependencies
RUN npm install

# Run the Vue.js project build
RUN npm run build-only

FROM nginx:1.24.0-alpine

# ADD docker/nginx.conf /etc/nginx/nginx.conf
# ADD dist /usr/share/nginx/html
# Copy custom Nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Copy built static files from the builder stage
COPY --from=builder dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
