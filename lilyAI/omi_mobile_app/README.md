# Omnitide Mobile Interface (OMI)

This is the official, secure, cross-platform mobile app for the Super-Localized, Self-Evolving Omnitide Nexus (SLOEN).

## Features
- Secure mTLS client authentication with certificate pinning
- JWT session management
- Biometric authentication (Touch ID/Face ID/Fingerprint)
- Optimized chat UI with real-time speech-to-text and text-to-speech
- Dynamic content rendering (code blocks, charts, actionable buttons, file preview)
- Offline mode and secure sync
- Secure self-updating mechanism (OTA, cryptographically signed)
- Mobile OpSec hardening (root/jailbreak detection, code obfuscation, tamper detection, secure logging, minimized permissions, sensitive data masking, secure keyboard input)
- Seamless integration with LCSAF and OCKIFT-P for unified AI orchestration

## Getting Started
1. Place your client certificate and key in `assets/certs/` (see LCSAF setup).
2. Configure your LCSAF server address and certificate SHA256 in `lib/api/secure_init.dart`.
3. Run `flutter pub get` to install dependencies.
4. Build and run on your device:
   - Android: `flutter run --release`
   - iOS: `flutter run --release`

## OTA Updates
- The app will check for signed updates from your local Nexus and verify signatures before applying.

## Security Notes
- The app will not run on rooted/jailbroken devices.
- All sensitive data is stored in secure enclaves and never logged or cached.
- Only essential permissions are requested.

## License
Proprietary / Architect's Absolute Genesis Edict
