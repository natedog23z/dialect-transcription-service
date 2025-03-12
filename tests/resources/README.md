# Test Resources

This directory contains resources for testing the transcription service.

## Test Audio Files

For proper testing, you should add test audio files that match the format used by the Dialect Audio iOS app:

- Format: M4A container with AAC encoding
- Sample Rate: 44.1kHz
- Bit Rate: Variable, typically 64-128 kbps
- Channels: Mono (1 channel)
- Duration: 30 seconds to 10 minutes

You can place your test audio files in this directory with descriptive names, such as:
- `short_test.m4a` - A short audio clip (30 seconds)
- `medium_test.m4a` - A medium-length clip (2 minutes)
- `long_test.m4a` - A longer test clip (8 minutes)

These files are not included in the repository and should be added manually. 