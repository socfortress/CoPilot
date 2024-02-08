#!/bin/bash

#----------------------------
# Docker build script.
# usage:
# ./create-dockers.sh [version (version used to tag docker)]
#----------------------------

# Configuration
NODE_VERSION=20.11.0

# ------------------------

export NVM_DIR=$HOME/.nvm;
source $NVM_DIR/nvm.sh;

currDir=$(pwd)
version="develop"
if [[ ! -z "$1" ]]; then
  version="$1"
fi

function prepareNvm(){
  nvm install ${NODE_VERSION}
  nvm use ${NODE_VERSION}
}

function build_backend() {
  echo ""
  echo "Build backend (version=${version})"
  cd $currDir/backend
  docker build . -t copilot/copilot-backend:${version}
}

function build_frontend() {
  echo ""
  echo "Build frontend (version=${version})"
  cd $currDir/frontend
  docker build . -t copilot/copilot-frontend:${version}
}



echo "Copilot Docker"
echo "Version: ${version}"

#prepareNvm
build_backend
build_frontend



