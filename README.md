# WhisperMac

## Useful Commands

### Setting up conda environment

1. Run `conda env create -f transcription.yml`
2. Then activate using `conda activate whispermac`

### Running real-time transcription

Run `python main.py` 
- Can take 5-10 seconds to start up on first run, subsequent runs will be instant

### Running whisper-stream binary

1. `cd` into `whisper.cpp`
2. Build binary with `cmake --build build -j --config Release`
3. Run `./build/bin/whisper-stream -m ./models/ggml-large-v3-turbo.bin -t 6 --step 1000 --length 5000 --keep 500 -c 2`

### Updating transcription.yml with new packages

After `pip install`, run `conda env export > transcription.yml`

### Formatting python files

Run `black *.py`
