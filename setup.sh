#!/bin/bash
set -euo pipefail # fail this script if any command run fails

git submodule update --init --recursive
brew install cmake sdl2 wget autoconf automake libtool

git clone https://github.com/xiph/rnnoise.git
cd ./rnnoise
bash autogen.sh
./configure
make
sudo make install

cd ../whisper.cpp

bash ./models/download-ggml-model.sh large-v3-turbo
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
bash ./models/generate-coreml-model.sh large-v3-turbo
bash ./models/download-vad-model.sh silero-v6.2.0

cmake -B build -DWHISPER_COREML=1 -DWHISPER_SDL2=ON
cmake --build build -j --config Release

cd ../
rm -rf rnnoise
