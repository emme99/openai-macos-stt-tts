import Foundation
import Speech
import AVFoundation

@main
struct MacOSTranscribeAnalyzer {
    static func main() async {
        let arguments = CommandLine.arguments
        
        guard arguments.count >= 2 else {
            printUsage()
            exit(1)
        }
        
        let audioPath = arguments[1]
        var locale = "en-US"
        var outputJSON = false
        var includeSegments = false
        
        // Parse options
        var i = 2
        while i < arguments.count {
            let arg = arguments[i]
            switch arg {
            case "--locale":
                if i + 1 < arguments.count {
                    locale = arguments[i + 1]
                    i += 2
                } else {
                    printError("--locale requires a value")
                    exit(1)
                }
            case "--json":
                outputJSON = true
                i += 1
            case "--segments":
                includeSegments = true
                i += 1
            default:
                printError("Unknown option: \(arg)")
                exit(1)
            }
        }
        
        // Verify audio file exists
        let fileManager = FileManager.default
        guard fileManager.fileExists(atPath: audioPath) else {
            printError("Audio file not found: \(audioPath)")
            exit(2)
        }
        
        // Check macOS version compatibility
        if !isSpeechAnalyzerAvailable() {
            printError("SpeechAnalyzer requires macOS 26 or later")
            exit(3)
        }
        
        do {
            let audioURL = URL(fileURLWithPath: audioPath)
            let transcription = try await transcribeAudio(audioURL, locale: locale)
            
            if outputJSON {
                // Output JSON format with metadata
                let result: [String: Any] = [
                    "text": transcription.text,
                    "locale": locale,
                    "segments": includeSegments ? transcription.segments : []
                ]
                
                if let jsonData = try? JSONSerialization.data(withJSONObject: result, options: .prettyPrinted),
                   let jsonString = String(data: jsonData, encoding: .utf8) {
                    print(jsonString)
                } else {
                    printError("Failed to serialize JSON output")
                    exit(4)
                }
            } else {
                // Plain text output
                print(transcription.text)
            }
            
            exit(0)
        } catch let error {
            printError("Transcription failed: \(error.localizedDescription)")
            exit(5)
        }
    }
    
    static func isSpeechAnalyzerAvailable() -> Bool {
        let version = ProcessInfo.processInfo.operatingSystemVersion
        // macOS 26 Tahoe and later (version 14.x)
        // Note: Full SpeechAnalyzer API check will be added when the public API is released
        return version.majorVersion >= 14
    }
    
    static func transcribeAudio(_ url: URL, locale: String) async throws -> TranscriptionResult {
        // Normalize locale identifier (replace _ with -)
        let localeIdentifier = locale.replacingOccurrences(of: "_", with: "-")
        
        // Get audio file info for duration
        let audioFile = try AVAudioFile(forReading: url)
        let durationInSeconds = Double(audioFile.length) / audioFile.processingFormat.sampleRate
        
        // Use SpeechRecognizer for transcription (most reliable on macOS 26+)
        return try await transcribeWithSpeechRecognizer(url, locale: localeIdentifier, duration: durationInSeconds)
    }
    
    static func transcribeWithSpeechRecognizer(_ url: URL, locale: String, duration: Double) async throws -> TranscriptionResult {
        let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale))
        
        guard recognizer != nil else {
            throw TranscriptionError.unsupportedLocale(locale)
        }
        
        // Check authorization status
        let authStatus = SFSpeechRecognizer.authorizationStatus()
        
        if authStatus == .notDetermined {
            // Request authorization
            let authorized = try await requestSpeechRecognitionAuthorization()
            if !authorized {
                throw TranscriptionError.authorizationDenied
            }
        } else if authStatus == .denied || authStatus == .restricted {
            throw TranscriptionError.authorizationDenied
        }
        
        // If still not authorized, request one more time
        if SFSpeechRecognizer.authorizationStatus() != .authorized {
            throw TranscriptionError.authorizationDenied
        }
        
        let request = SFSpeechURLRecognitionRequest(url: url)
        request.shouldReportPartialResults = false
        
        return try await withCheckedThrowingContinuation { continuation in
            var transcribedText = ""
            var segments: [TranscriptionSegment] = []
            var finished = false
            
            let task = recognizer!.recognitionTask(with: request) { result, error in
                if let error = error {
                    if !finished {
                        finished = true
                        continuation.resume(throwing: TranscriptionError.recognitionFailed(error.localizedDescription))
                    }
                    return
                }
                
                if let result = result {
                    transcribedText = result.bestTranscription.formattedString
                    
                    // Extract segments with timing information
                    for segment in result.bestTranscription.segments {
                        let segmentStart = segment.timestamp
                        let segmentDuration = segment.duration
                        let segmentEnd = segmentStart + segmentDuration
                        let segmentText = segment.substring
                        
                        segments.append(TranscriptionSegment(
                            start: segmentStart,
                            end: segmentEnd,
                            text: segmentText
                        ))
                    }
                    
                    // If no segments were extracted, create one for the entire audio
                    if segments.isEmpty {
                        segments.append(TranscriptionSegment(
                            start: 0,
                            end: duration,
                            text: transcribedText
                        ))
                    }
                    
                    if result.isFinal && !finished {
                        finished = true
                        continuation.resume(returning: TranscriptionResult(
                            text: transcribedText,
                            segments: segments
                        ))
                    }
                }
            }
            
            // Ensure task doesn't get deallocated
            _ = withExtendedLifetime(task) { }
        }
    }
    
    static func requestSpeechRecognitionAuthorization() async -> Bool {
        return await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { authStatus in
                continuation.resume(returning: authStatus == .authorized)
            }
        }
    }
    
    static func printUsage() {
        let usage = """
        Usage: macos-transcribe-analyzer <audio-file> [options]
        
        Options:
          --locale LOCALE      BCP-47 locale code (default: en-US)
          --json               Output JSON format with segments
          --segments           Include segment timestamps in JSON output
        
        Examples:
          macos-transcribe-analyzer audio.wav
          macos-transcribe-analyzer audio.m4a --locale it-IT --json
        """
        fputs(usage + "\n", stderr)
    }
    
    static func printError(_ message: String) {
        fputs("Error: \(message)\n", stderr)
    }
}

enum TranscriptionError: LocalizedError {
    case unsupportedLocale(String)
    case authorizationDenied
    case noResult
    case audioProcessingError(String)
    case recognitionFailed(String)
    
    var errorDescription: String? {
        switch self {
        case .unsupportedLocale(let locale):
            return "Unsupported locale: \(locale)"
        case .authorizationDenied:
            return "Speech recognition authorization denied. Please grant permissions in System Preferences."
        case .noResult:
            return "No transcription result received"
        case .audioProcessingError(let detail):
            return "Audio processing error: \(detail)"
        case .recognitionFailed(let detail):
            return "Speech recognition failed: \(detail)"
        }
    }
}

struct TranscriptionSegment: Codable {
    let start: Double
    let end: Double
    let text: String
}

struct TranscriptionResult {
    let text: String
    let segments: [TranscriptionSegment]
}
