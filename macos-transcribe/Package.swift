// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "macos-transcribe",
    platforms: [
        .macOS(.v14) // Using v14 (Sonoma) as baseline, assuming v13+ features are sufficient, but SFSpeechRecognizer is old.
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-argument-parser.git", from: "1.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "macos-transcribe",
            dependencies: [
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ]
        ),
    ]
)
