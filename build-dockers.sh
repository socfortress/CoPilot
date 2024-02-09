#!/bin/bash

currDir=$(pwd)
version="latest"
if [[ ! -z "$1" ]]; then
  version="$1"
fi

# Function to check if Docker is installed
function check_docker_installed() {
  if ! command -v docker &> /dev/null; then
    echo "Docker could not be found. Please install Docker and try again."
    exit 1
  fi
}

function build_backend() {
  echo ""
  echo "Build backend (version=${version})"
  cd $currDir/backend
  docker build . --no-cache -t socfortress/copilot-backend:${version}
}

function build_frontend() {
  echo ""
  echo "Build frontend (version=${version})"
  cd $currDir/frontend
  # Copy the .env.example to .env
  cp .env.example .env
  # Ask for the new Domain or IP address for the frontend URL
  echo "Please enter the new Domain or IP address for the frontend URL (e.g., yourfrontenddomain.com):"
  read frontendIp
  # Replace only the IP address part in the URL
  sed -i "s|0.0.0.0|${frontendIp}|g" .env
  docker build . --no-cache -t socfortress/copilot-frontend:${version}
}

echo "Copilot Docker"
echo "Version: ${version}"

# First, ensure Docker is installed
check_docker_installed

# Build processes
#build_backend # Function not needed as SOCFortress will provide the backend but leaving in case you want to build your own
build_frontend
