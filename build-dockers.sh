#!/bin/bash


currDir=$(pwd)
version="latest"
if [[ ! -z "$1" ]]; then
  version="$1"
fi

function build_backend() {
  echo ""
  echo "Build backend (version=${version})"
  cd $currDir/backend
  docker build . -t socfortress/copilot-backend:${version}
}

function build_frontend() {
  echo ""
  echo "Build frontend (version=${version})"
  cd $currDir/frontend
  docker build . -t socfortress/copilot-frontend:${version}
}

echo "Copilot Docker"
echo "Version: ${version}"

build_backend
build_frontend



