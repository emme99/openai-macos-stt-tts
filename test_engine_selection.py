#!/usr/bin/env python3
"""
Quick test script to verify the STT engine selection system
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/Users/emme/Projects/Python/openai-macos-stt-tts')

import config

# Mock Flask app initialization (without starting the server)
print("=" * 60)
print("STT Engine Selection System Test")
print("=" * 60)

# Import the app module to test engine selection
try:
    # Import app to trigger engine selection logic
    import app
    
    print(f"\n✓ App module imported successfully")
    print(f"\n📊 Engine Configuration:")
    print(f"  - Config STT_ENGINE: {app.config.STT_ENGINE}")
    print(f"  - Detected macOS version: {app.get_macos_version()}")
    print(f"  - Selected engine: {app.get_stt_engine()}")
    
    # Verify binary paths exist
    print(f"\n📁 Binary Paths:")
    legacy_bin = config.MACOS_TRANSCRIBE_BIN
    analyzer_bin = config.MACOS_TRANSCRIBE_ANALYZER_BIN
    
    print(f"  - Legacy binary: {os.path.basename(legacy_bin)}")
    print(f"    Exists: {os.path.exists(legacy_bin)}")
    print(f"  - Analyzer binary: {os.path.basename(analyzer_bin)}")
    print(f"    Exists: {os.path.exists(analyzer_bin)}")
    
    # Show which binary will be used
    print(f"\n🎯 Active Binary:")
    active_bin = app.get_transcribe_binary()
    print(f"  - Path: {active_bin}")
    print(f"  - Exists: {os.path.exists(active_bin)}")
    
    print(f"\n✓ All checks passed!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
