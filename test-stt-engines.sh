#!/bin/bash

# Test script for STT engines
# Verifies that speech recognition works and helps debug language availability

echo "═══════════════════════════════════════════════════════════════"
echo "STT Engines Test Script"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script only works on macOS"
    exit 1
fi

# Get paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LEGACY_BIN="$SCRIPT_DIR/macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe"
ANALYZER_BIN="$SCRIPT_DIR/macos-transcribe-analyzer/.build/arm64-apple-macosx/release/macos-transcribe-analyzer"
TEST_AUDIO="$SCRIPT_DIR/temp/test_audio.wav"

# Check binaries exist
echo "✓ Checking binaries..."
if [[ ! -f "$LEGACY_BIN" ]]; then
    echo "  ❌ Legacy binary not found: $LEGACY_BIN"
    echo "  Please compile with: cd macos-transcribe && swift build -c release"
    exit 1
else
    echo "  ✓ Legacy binary found"
fi

if [[ ! -f "$ANALYZER_BIN" ]]; then
    echo "  ⚠️  Analyzer binary not found: $ANALYZER_BIN"
    echo "  Please compile with: cd macos-transcribe-analyzer && swift build -c release"
else
    echo "  ✓ Analyzer binary found"
fi

# Check test audio
if [[ ! -f "$TEST_AUDIO" ]]; then
    echo "  ⚠️  Test audio file not found: $TEST_AUDIO"
    echo "  Creating silence test audio..."
    ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 1 -q:a 9 "$TEST_AUDIO" 2>/dev/null
    if [[ $? -eq 0 ]]; then
        echo "  ✓ Created test audio"
    else
        echo "  ❌ Failed to create test audio. Ensure ffmpeg is installed."
        exit 1
    fi
else
    echo "  ✓ Test audio file found"
fi

echo ""

# Test available languages
echo "📋 Testing Language Availability:"
echo ""

LANGUAGES=("en-US" "en-GB" "es-ES" "fr-FR" "it-IT" "de-DE" "ja-JP" "zh-Hans_CN")

for lang in "${LANGUAGES[@]}"; do
    echo -n "  Testing $lang... "
    output=$("$LEGACY_BIN" "$TEST_AUDIO" --locale "$lang" --json 2>&1)
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        echo "✓ Available"
    elif echo "$output" | grep -q "not available"; then
        echo "❌ Not available"
    elif echo "$output" | grep -q "not supported"; then
        echo "❌ Not supported"
    elif echo "$output" | grep -q "authorization"; then
        echo "⚠️  Authorization denied"
    else
        echo "❌ Error: $output"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Tips:"
echo ""
echo "1. If all languages show 'Not available':"
echo "   • Go to System Settings → Privacy & Security → Speech Recognition"
echo "   • Add Terminal/Python to the allowed apps"
echo ""
echo "2. If you see 'Authorization denied':"
echo "   • Open: System Settings → Privacy & Security → Speech Recognition"
echo "   • Toggle the app to ON"
echo ""
echo "3. To add new languages:"
echo "   • Go to System Settings → General → Language & Region"
echo "   • Add your desired language"
echo "   • Restart Terminal/IDE"
echo ""
echo "4. For more details, see README.md"
echo "═══════════════════════════════════════════════════════════════"
