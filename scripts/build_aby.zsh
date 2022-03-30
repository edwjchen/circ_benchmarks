#!/usr/bin/env zsh
mkdir -p -- ./modules/ABY/build
cd ./modules/ABY/build
HYCC_DIR="../../HyCC"
cmake .. -DABY_BUILD_EXE=On
make