// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "macos-transcribe-analyzer",
    platforms: [
        .macOS(.v14)  // Will be checked at runtime for SpeechAnalyzer availability
    ],
    products: [
        .executable(name: "macos-transcribe-analyzer", targets: ["macos-transcribe-analyzer"])
    ],
    dependencies: [
        // No external dependencies - using only Apple frameworks
    ],
    targets: [
        .executableTarget(
            name: "macos-transcribe-analyzer",
            dependencies: [],
            swiftSettings: [
                .unsafeFlags(["-suppress-warnings"], .when(configuration: .release))
            ]
        )
    ]
)
