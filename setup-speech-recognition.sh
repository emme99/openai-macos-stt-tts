#!/bin/bash

# Setup script to enable macOS Speech Recognition for STT engines
# This script helps authorize Python/Terminal for Speech Recognition

echo "═══════════════════════════════════════════════════════════════"
echo "macOS Speech Recognition Setup for STT Engines"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "This script will help you enable Speech Recognition authorization."
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script only works on macOS"
    exit 1
fi

# Get macOS version
macos_version=$(sw_vers -ProductVersion)
echo "✓ macOS Version: $macos_version"
echo ""

# Provide authorization instructions
echo "📋 Manual Authorization Steps:"
echo ""
echo "1. Open System Settings (or System Preferences):"
echo "   • On macOS 13+: Open 'System Settings' app"
echo "   • On macOS 12 and earlier: Open 'System Preferences' app"
echo ""
echo "2. Navigate to Privacy & Security:"
echo "   • Look for 'Privacy & Security' in the sidebar"
echo "   • Scroll down to 'Speech Recognition'"
echo ""
echo "3. Grant authorization:"
echo "   • If not already there, add Terminal or your Python environment"
echo "   • Ensure the toggle is ON (green)"
echo ""
echo "4. Add language support (if needed):"
echo "   • Go to System Settings → General → Language & Region"
echo "   • Add your desired language (English, Italian, French, etc.)"
echo "   • Restart Terminal/IDE after changing languages"
echo ""

# Check if we can open System Settings
echo "🚀 Quick Start:"
echo ""
read -p "Would you like me to open System Settings? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Try to open the appropriate settings
    if [[ "$macos_version" == 13.* ]] || [[ "${macos_version%.*}" -ge 13 ]]; then
        # macOS 13+ uses System Settings
        echo "Opening System Settings..."
        open "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition"
    else
        # macOS 12 and earlier use System Preferences
        echo "Opening System Preferences..."
        open "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition"
    fi
    echo ""
    echo "If the Settings didn't open, go to:"
    echo "  Settings → Privacy & Security → Speech Recognition"
else
    echo "Skipping System Settings. You can open it manually anytime."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "After granting authorization:"
echo ""
echo "1. Restart your Terminal or IDE"
echo "2. Run the test script: ./test_transcription.sh"
echo "3. Or start the server: python app.py"
echo ""
echo "For more details, see README.md → macOS Speech Recognition Authorization"
echo "═══════════════════════════════════════════════════════════════"
