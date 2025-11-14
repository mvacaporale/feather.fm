#!/usr/bin/env python3

import os
import shutil
import tempfile
import google.genai as genai
from openai import OpenAI
from pathlib import Path

ANALYSIS_PROMPT = """
You’re helping sort songs into playlists based on vibe and style. 
Describe this song in a natural way, but include enough musical and emotional detail 
that someone could confidently place it among 1000 other tracks.

Focus on: 
- Genre and style
- Energy level and rhythm
- Emotional mood or atmosphere
- Key sounds, vocals, and production touches that define its vibe

End with one sentence summarizing the overall feel (e.g., “A mellow late-night R&B groove with airy vocals and warm synths.”)
"""

# Edit this prompt more here:
# https://aistudio.google.com/prompts/1UXbMNkuhG1YFmKl0icxefowpYvkU8sJN
ANALYSIS_PROMPT_v1 = """
Analyze this audio track comprehensively and provide a detailed summary of its key musical characteristics for text embedding purposes. Focus on technical musical details alongside broader experiential elements:

1.  **Genre & Subgenre:** Identify the primary and secondary musical genres and any relevant subgenres.
2.  **Tempo & Rhythm:** Estimate the tempo in BPM. Describe the prominent rhythmic patterns, groove, and time signature.
3.  **Key & Tonality:** Identify the key signature, mode (e.g., major, minor, Dorian), and overall tonality.
4.  **Melody & Harmony:** Describe the melodic characteristics (e.g., lyrical, repetitive, instrumental hooks) and the nature of the harmonic progression (e.g., simple, complex, chord voicings).
5.  **Instrumentation & Arrangement:** List all discernible instruments and sound elements. Describe their roles, the overall arrangement density, and spatial characteristics.
6.  **Vocals (if present):** Describe the vocal style (e.g., lead, backing, harmonies), gender, vocal techniques used, and lyrical themes.
7.  **Emotional Characteristics & Mood:** Describe the dominant mood, energy level, and overall emotional impact of the track (e.g., uplifting, melancholic, intense, relaxed).
8.  **Production Style & Sound Design:** Comment on the recording quality, mix clarity, sound design choices (e.g., effects, synths), and overall production aesthetic.
9.  **Song Structure:** Outline the basic song structure (e.g., intro, verse, pre-chorus, chorus, bridge, solo, outro).
10. **Distinctive Features & Similarities:** Highlight any unique or distinctive musical elements. Suggest a few artists or songs that share significant stylistic or sonic similarities.

Please provide specific, objective, and detailed descriptions for each point, ensuring the language captures the unique musical identity of the track.
"""

def get_audio_embeddings(file_path: str, embedding_provider: str = 'gemini'):
    """Generate embeddings vector for an audio file using Gemini analysis and return analysis text.
    
    Args:
        file_path: Path to the MP3 file
        embedding_provider: 'gemini' or 'openai' for embedding generation
        
    Returns:
        tuple: (musical_analysis_text, embedding_vector)
    """
    gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    
    if embedding_provider == 'openai':
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    # Create temporary file with ASCII-safe name for Gemini API
    temp_path = None
    try:
        # Create temporary file with .mp3 extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.mp3')
        os.close(temp_fd)  # Close file descriptor
        
        # Copy original file to temp location
        shutil.copy2(file_path, temp_path)
        
        # Upload the temporary file
        audio_file = gemini_client.files.upload(file=temp_path)
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[audio_file, ANALYSIS_PROMPT]
        )
        
        # Ensure response text is properly encoded for embedding
        response_text = response.text
        if isinstance(response_text, str):
            response_text = response_text.encode('utf-8', errors='replace').decode('utf-8')
        
        # Generate embeddings using the specified provider
        if embedding_provider == 'openai':
            embedding_response = openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=response_text
            )
            embedding_vector = embedding_response.data[0].embedding
        else:  # gemini
            embedding_result = gemini_client.models.embed_content(
                model="text-embedding-004",
                contents=[response_text]
            )
            embedding_vector = embedding_result.embeddings[0].values
        
        return response.text, embedding_vector
        
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def analyze_audio_file(file_path: str):
    """Analyze an audio file and generate embeddings based on musical elements."""
    
    print(f"Uploading audio file: {file_path}")
    print("Generating musical analysis...")
    
    musical_analysis, embedding_vector = get_audio_embeddings(file_path)
    
    print("Musical Analysis:")
    print("=" * 50)
    print(musical_analysis)
    print("=" * 50)
    
    print(f"\nGenerated embedding vector (dimension: {len(embedding_vector)})")
    print(f"First 10 values: {embedding_vector[:10]}")
    
    output_file = Path(file_path).stem + "_analysis.txt"
    with open(output_file, 'w') as f:
        f.write("MUSICAL ANALYSIS\n")
        f.write("=" * 50 + "\n\n")
        f.write(musical_analysis)
        f.write("\n\n" + "=" * 50 + "\n")
        f.write("EMBEDDING VECTOR\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Dimensions: {len(embedding_vector)}\n")
        f.write(f"Values: {embedding_vector}\n")
    
    print(f"\nAnalysis and embeddings saved to: {output_file}")
    
    return musical_analysis, embedding_vector

if __name__ == "__main__":
    audio_file_path = "previews/Toll So Below -.mp3"
    
    try:
        analysis, embeddings = analyze_audio_file(audio_file_path)
    except Exception as e:
        print(f"Error: {e}")