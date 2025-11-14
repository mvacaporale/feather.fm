#!/usr/bin/env python3

import torch
import librosa
import numpy as np
from transformers import ClapModel, ClapProcessor
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

def get_clap_embeddings(audio_path: str, sample_rate: int = 48000):
    """Generate CLAP embeddings vector for an audio file.
    
    Args:
        audio_path: Path to the MP3 file
        sample_rate: Sample rate for audio processing (default: 48000)
        
    Returns:
        numpy.ndarray: CLAP embedding vector
    """
    # model = ClapModel.from_pretrained("laion/clap-htsat-unfused")
    # processor = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
    model = ClapModel.from_pretrained("laion/larger_clap_music_and_speech")
    processor = ClapProcessor.from_pretrained("laion/larger_clap_music_and_speech")
    
    audio, _ = librosa.load(audio_path, sr=sample_rate)
    inputs = processor(audios=audio, return_tensors="pt", sampling_rate=sample_rate)
    
    with torch.no_grad():
        audio_embeddings = model.get_audio_features(**inputs)
    
    return audio_embeddings.numpy().flatten()

def generate_clap_embeddings(audio_path: str, sample_rate: int = 48000):
    """Generate embeddings using CLAP model for audio files."""
    
    print("Loading CLAP model and processor...")
    print(f"Loading audio file: {audio_path}")
    
    embeddings_array = get_clap_embeddings(audio_path, sample_rate)
    
    print(f"Generated CLAP embeddings (dimension: {len(embeddings_array)})")
    print(f"First 10 values: {embeddings_array[:10]}")

    output_file = Path(audio_path).stem + "_clap_embeddings.txt"
    with open(output_file, 'w') as f:
        f.write("CLAP AUDIO EMBEDDINGS\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Audio file: {audio_path}\n")
        f.write(f"Embedding dimensions: {len(embeddings_array)}\n")
        f.write(f"Model: laion/larger_clap_music_and_speech\n\n")
        f.write("Embedding values:\n")
        f.write(f"{embeddings_array.tolist()}\n")
    
    print(f"CLAP embeddings saved to: {output_file}")
    
    return embeddings_array

if __name__ == "__main__":
    audio_file_path = "previews/Toll So Below -.mp3"
    
    try:
        embeddings = generate_clap_embeddings(audio_file_path)
        print(f"\nSuccessfully generated CLAP embeddings with shape: {embeddings.shape}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()