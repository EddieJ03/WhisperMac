#!/bin/bash

git submodule update --init --recursive

cd ./whisper.cpp

bash ./models/download-ggml-model.sh large-v3-turbo
bash ./models/generate-coreml-model.sh large-v3-turbo
cmake -B build -DWHISPER_COREML=1
cmake --build build -j --config Release
