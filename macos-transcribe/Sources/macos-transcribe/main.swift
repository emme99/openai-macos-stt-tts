import Foundation
import Speech
import ArgumentParser

@main
struct Transcribe: AsyncParsableCommand {
    @Argument(help: "Path to the audio file.")
    var audioPath: String

    @Flag(help: "Output result as JSON array.")
    var json: Bool = false

    @Option(help: "Locale identifier for recognition (e.g., en-US, it-IT).")
    var locale: String = "en-US"

    mutating func run() async throws {
        // 1. Check file existence
        let fileURL = URL(fileURLWithPath: audioPath)
        guard FileManager.default.fileExists(atPath: audioPath) else {
            print("Error: File not found at \(audioPath)")
            throw ExitCode.failure
        }

        // 2. Request permission (not strict for CLI usually but good practice/required by API)
        // With SFSpeechRecognizer, we need to ensure the locale is supported.
        // Assuming Italian 'it-IT' or English 'en-US' based on user need, but let's default to locale of the file or user arg?
        // For now, let's hardcode 'en-US' as source audio is likely English (yt-summary context), 
        // but the tool is now customizable via the --locale option.
        // NOTE: The user prompt says "sostituire la traccia audio in lingua inglese", so source is English.
        let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale))
        
        guard let speechRecognizer = recognizer, speechRecognizer.isAvailable else {
            print("Error: Speech recognizer not available for \(locale)")
            throw ExitCode.failure
        }

        // 3. Perform Request
        do {
            let request = SFSpeechURLRecognitionRequest(url: fileURL)
            request.shouldReportPartialResults = false
            request.requiresOnDeviceRecognition = false
            if #available(macOS 10.15, *) {
                request.addsPunctuation = true
            }
            
            // Debug info
            // print("Debug: OnDeviceRecognition support: \(speechRecognizer.supportsOnDeviceRecognition)")
            // print("Debug: Forcing OnDevice: false (allowing server fallback)")

            // We need to await the result using a continuation because the API is completion-handler based (mostly)
            // But verify if async/await API effectively exists or we wrap it.
            let transcription = try await transcribe(request: request, recognizer: speechRecognizer)
            
            // 4. Output
            // 4. Output
            if json {
                let segments = transcription.segments.map { segment in
                     Segment(
                        text: segment.substring,
                        start: segment.timestamp,
                        duration: segment.duration
                    )
                }
                let jsonData = try JSONEncoder().encode(segments)
                print(String(data: jsonData, encoding: .utf8)!)
            } else {
                print(transcription.formattedString)
            }
            
        } catch {
            print("Error during transcription: \(error)")
            throw ExitCode.failure
        }
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
