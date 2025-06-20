import 'package:flutter_jailbreak_detection/flutter_jailbreak_detection.dart';

class RootJailbreakDetector {
  static Future<bool> isDeviceCompromised() async {
    return await FlutterJailbreakDetection.jailbroken || await FlutterJailbreakDetection.developerMode;
  }
}
