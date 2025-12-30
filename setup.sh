#!/bin/bash
set -euo pipefail # fail this script if any command run fails

git submodule update --init --recursive

cd ./whisper.cpp

bash ./models/download-ggml-model.sh large-v3-turbo
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
bash ./models/generate-coreml-model.sh large-v3-turbo
brew install cmake sdl2
cmake -B build -DWHISPER_COREML=1 -DWHISPER_SDL2=ON
cmake --build build -j --config Release
