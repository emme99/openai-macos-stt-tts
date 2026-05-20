import Foundation
import Speech
import ArgumentParser

@main
struct Transcribe: AsyncParsableCommand {
    @Argument(help: "Path to the audio file.")
    var audioPath: String

    @Flag(help: "Output result as JSON array.")
    var json: Bool = false

    @Flag(help: "Output segments with timestamps (default: false = single string)")
    var segments: Bool = false

    @Option(help: "Locale identifier for recognition (e.g., en-US, it-IT).")
    var locale: String = "en-US"

    mutating func run() async throws {
        // 1. Check file existence
        let fileURL = URL(fileURLWithPath: audioPath)
        guard FileManager.default.fileExists(atPath: audioPath) else {
            print("Error: File not found at \(audioPath)")
            throw ExitCode.failure
        }

        // 2. Speech Recognizer
        let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale))
        
        guard let speechRecognizer = recognizer, speechRecognizer.isAvailable else {
            print("Error: Speech recognizer not available for \(locale)")
            throw ExitCode.failure
        }

        // Debug info (versione compatibile)
        printToStderr("Debug: On-device supported: \(speechRecognizer.supportsOnDeviceRecognition)")

        // 3. Perform Request
        do {
            let request = SFSpeechURLRecognitionRequest(url: fileURL)
            request.shouldReportPartialResults = false
            // Forza on-device → comportamento consistente su M3 e Intel
            request.requiresOnDeviceRecognition = true
            
            if #available(macOS 10.15, *) {
                request.addsPunctuation = true
            }

            let transcription = try await transcribe(request: request, recognizer: speechRecognizer)
            
            // 4. Output
            if json {
                if self.segments {
                    // Output con segmenti e timecode
                    let outputSegments = transcription.segments.map { segment in
                        Segment(
                            text: segment.substring,
                            start: segment.timestamp,
                            duration: segment.duration
                        )
                    }
                    let jsonData = try JSONEncoder().encode(outputSegments)
                    print(String(data: jsonData, encoding: .utf8)!)
                } else {
                    // Default: singola stringa (comportamento stabile)
                    let fullText = transcription.formattedString
                    let singleSegment = [Segment(
                        text: fullText,
                        start: 0,
                        duration: transcription.segments.last?.timestamp ?? 0 + (transcription.segments.last?.duration ?? 0)
                    )]
                    let jsonData = try JSONEncoder().encode(singleSegment)
                    print(String(data: jsonData, encoding: .utf8)!)
                }
            } else {
                print(transcription.formattedString)
            }
            
        } catch {
            print("Error during transcription: \(error)")
            throw ExitCode.failure
        }
    }
    
    // Funzione helper per stampare su stderr in modo compatibile
    private func printToStderr(_ message: String) {
        let output = message + "\n"
        FileHandle.standardError.write(output.data(using: .utf8)!)
    }
    
    private func transcribe(request: SFSpeechURLRecognitionRequest, recognizer: SFSpeechRecognizer) async throws -> SFTranscription {
        return try await withCheckedThrowingContinuation { continuation in
            recognizer.recognitionTask(with: request) { result, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                
                if let result = result, result.isFinal {
                    continuation.resume(returning: result.bestTranscription)
                }
            }
        }
    }
}

struct Segment: Codable {
    let text: String
    let start: TimeInterval
    let duration: TimeInterval
}