#!/usr/bin/env node

const spotifyPreviewFinder = require('spotify-preview-finder');

async function testPreviewFinder() {
    try {
        console.log('Testing spotify-preview-finder...');
        
        // Test with a popular song
        const result = await spotifyPreviewFinder('Shape of You', 'Ed Sheeran');
        console.log('Result:', result);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

async function findPreview(songName, artistName) {
    try {
        const result = await spotifyPreviewFinder(songName, artistName);
        return result;
    } catch (error) {
        console.error(`Error finding preview for "${songName}" by "${artistName}":`, error.message);
        return null;
    }
}

async function main() {
    if (process.argv.length < 4) {
        console.log('Usage: node preview_finder.js "Song Name" "Artist Name"');
        console.log('Example: node preview_finder.js "Shape of You" "Ed Sheeran"');
        return;
    }
    
    const songName = process.argv[2];
    const artistName = process.argv[3];
    
    console.log(`Searching for: "${songName}" by "${artistName}"`);
    
    const result = await findPreview(songName, artistName);
    
    if (result) {
        console.log('✓ Preview found!');
        console.log('JSON_RESULT_START');
        console.log(JSON.stringify(result, null, 2));
        console.log('JSON_RESULT_END');
    } else {
        console.log('✗ No preview found');
        console.log('JSON_RESULT_START');
        console.log('null');
        console.log('JSON_RESULT_END');
    }
}

if (require.main === module) {
    main();
}

module.exports = { findPreview };