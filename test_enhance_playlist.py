#!/usr/bin/env python3
"""
Test script for playlist enhancement functionality
"""

import unittest
import numpy as np
import pandas as pd
import tempfile
import os
from unittest.mock import patch, MagicMock

# Import functions to test
from utils.embedding_manager import load_reference_embeddings, get_or_create_embedding
from utils.similarity_engine import calculate_similarity_scores, select_top_similar_songs


class TestPlaylistEnhancement(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Create sample embedding data
        self.sample_embeddings = pd.DataFrame({
            'song_name': ['Song A', 'Song B', 'Song C', 'Song D'],
            'artist': ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4'],
            'song_uri': [
                'spotify:track:1234567890abcdef1234567890abcdef12345678',
                'spotify:track:2345678901bcdefg2345678901bcdefg23456789',
                'spotify:track:3456789012cdefgh3456789012cdefgh34567890',
                'spotify:track:4567890123defghi4567890123defghi45678901'
            ],
            'embedding': [
                '[0.1, 0.2, 0.3, 0.4]',
                '[0.2, 0.3, 0.4, 0.5]', 
                '[0.8, 0.7, 0.6, 0.5]',
                '[0.9, 0.8, 0.7, 0.6]'
            ]
        })
        
        # Create temporary CSV file for testing
        self.temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        self.sample_embeddings.to_csv(self.temp_csv.name, index=False)
        self.temp_csv.close()
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.temp_csv.name):
            os.unlink(self.temp_csv.name)
    
    def test_load_reference_embeddings_success(self):
        """Test successful loading of reference embeddings"""
        df = load_reference_embeddings(self.temp_csv.name)
        
        self.assertEqual(len(df), 4)
        self.assertIn('embedding_vector', df.columns)
        
        # Check that embeddings are parsed correctly
        first_embedding = df.iloc[0]['embedding_vector']
        expected = np.array([0.1, 0.2, 0.3, 0.4])
        np.testing.assert_array_equal(first_embedding, expected)
    
    def test_load_reference_embeddings_file_not_found(self):
        """Test handling of missing embeddings file"""
        with self.assertRaises(FileNotFoundError):
            load_reference_embeddings("nonexistent_file.csv")
    
    def test_calculate_similarity_scores(self):
        """Test similarity score calculation"""
        # Load reference data
        reference_df = load_reference_embeddings(self.temp_csv.name)
        
        # Create playlist embeddings
        playlist_embeddings = [
            np.array([0.15, 0.25, 0.35, 0.45]),  # Similar to Song A and B
            np.array([0.1, 0.2, 0.3, 0.4])       # Identical to Song A
        ]
        
        # Calculate similarities
        result_df = calculate_similarity_scores(playlist_embeddings, reference_df)
        
        # Check results
        self.assertEqual(len(result_df), 4)
        self.assertIn('similarity_score', result_df.columns)
        
        # Songs A and B should have higher similarity scores
        top_song = result_df.iloc[0]
        self.assertIn(top_song['song_name'], ['Song A', 'Song B'])
        self.assertGreater(top_song['similarity_score'], 0.9)
    
    def test_select_top_similar_songs(self):
        """Test selection of top similar songs"""
        # Create mock similarity dataframe
        similarity_df = pd.DataFrame({
            'song_name': ['Song A', 'Song B', 'Song C', 'Song D'],
            'artist': ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4'],
            'song_uri': [
                'spotify:track:1111',
                'spotify:track:2222',
                'spotify:track:3333',
                'spotify:track:4444'
            ],
            'similarity_score': [0.95, 0.85, 0.75, 0.65]
        })
        
        # Existing playlist contains Song A
        existing_uris = {'spotify:track:1111'}
        
        # Select top 2 songs
        selected = select_top_similar_songs(similarity_df, existing_uris, 2)
        
        # Should get Song B and C (skipping A as it's already in playlist)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]['name'], 'Song B')
        self.assertEqual(selected[1]['name'], 'Song C')
        self.assertNotIn('spotify:track:1111', [s['uri'] for s in selected])
    
    def test_select_top_similar_songs_insufficient_candidates(self):
        """Test selection when there aren't enough unique candidates"""
        # Small similarity dataframe
        similarity_df = pd.DataFrame({
            'song_name': ['Song A', 'Song B'],
            'artist': ['Artist 1', 'Artist 2'],
            'song_uri': ['spotify:track:1111', 'spotify:track:2222'],
            'similarity_score': [0.95, 0.85]
        })
        
        # Existing playlist contains Song A
        existing_uris = {'spotify:track:1111'}
        
        # Request 5 songs but only 1 available
        selected = select_top_similar_songs(similarity_df, existing_uris, 5)
        
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['name'], 'Song B')
    
    @patch('utils.embedding_manager.os.path.exists')
    @patch('utils.embedding_manager.search_and_download')
    @patch('utils.embedding_manager.get_audio_embeddings')
    def test_get_or_create_embedding_success(self, mock_get_embeddings, mock_download, mock_exists):
        """Test successful embedding creation"""
        # Mock successful download and embedding generation
        mock_download.return_value = '/path/to/preview.mp3'
        mock_exists.return_value = True
        mock_get_embeddings.return_value = np.array([0.1, 0.2, 0.3, 0.4])
        
        # Test the function
        embedding = get_or_create_embedding('Test Song', 'Test Artist', 'spotify:track:test')
        
        # Verify calls and result
        mock_download.assert_called_once_with('Test Song', 'Test Artist')
        mock_exists.assert_called_once_with('/path/to/preview.mp3')
        mock_get_embeddings.assert_called_once_with('/path/to/preview.mp3', 'gemini')
        np.testing.assert_array_equal(embedding, np.array([0.1, 0.2, 0.3, 0.4]))
    
    @patch('utils.embedding_manager.search_and_download')
    def test_get_or_create_embedding_download_failure(self, mock_download):
        """Test handling of download failure"""
        # Mock failed download
        mock_download.return_value = None
        
        # Test the function
        embedding = get_or_create_embedding('Test Song', 'Test Artist', 'spotify:track:test')
        
        # Should return None on failure
        self.assertIsNone(embedding)
    
    @patch('utils.embedding_manager.search_and_download')
    @patch('utils.embedding_manager.get_audio_embeddings')  
    def test_get_or_create_embedding_analysis_failure(self, mock_get_embeddings, mock_download):
        """Test handling of embedding generation failure"""
        # Mock successful download but failed embedding
        mock_download.return_value = '/path/to/preview.mp3'
        mock_get_embeddings.side_effect = Exception("Embedding failed")
        
        # Test the function
        embedding = get_or_create_embedding('Test Song', 'Test Artist', 'spotify:track:test')
        
        # Should return None on embedding failure
        self.assertIsNone(embedding)


class TestSystemExitContext:
    """Context manager to test sys.exit calls"""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type == SystemExit:
            return True
        return False


# Add helper method to unittest.TestCase
def assertSystemExit(self):
    """Helper method to check for sys.exit"""
    return TestSystemExitContext()

unittest.TestCase.assertSystemExit = assertSystemExit


def run_tests():
    """Run all tests and display results"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPlaylistEnhancement)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)