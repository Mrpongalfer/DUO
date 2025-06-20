import 'package:flutter/material.dart';
import 'package:omi_mobile_app/lib/ui/chat_screen.dart';
import 'package:omi_mobile_app/lib/api/auth_manager.dart';
import 'package:omi_mobile_app/lib/api/secure_init.dart';
import 'package:provider/provider.dart';
import 'package:omi_mobile_app/lib/api/biometric_manager.dart';
import 'package:omi_mobile_app/lib/ui/lock_screen.dart';
import 'package:omi_mobile_app/lib/api/root_jailbreak_detector.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SecureInit.init();
  bool isCompromised = await RootJailbreakDetector.isDeviceCompromised();
  if (isCompromised) {
    runApp(const CompromisedApp());
    return;
  }
  runApp(const OMIApp());
}

class OMIApp extends StatelessWidget {
  const OMIApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthManager()),
        ChangeNotifierProvider(create: (_) => BiometricManager()),
      ],
      child: MaterialApp(
        title: 'Omnitide Mobile Interface',
        theme: ThemeData(
          primarySwatch: Colors.deepPurple,
          brightness: Brightness.dark,
        ),
        home: const LockScreen(),
      ),
    );
  }
}

class CompromisedApp extends StatelessWidget {
  const CompromisedApp({super.key});
  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      home: Scaffold(
        body: Center(
          child: Text(
            'Device security compromised. OMI cannot run on rooted/jailbroken devices.',
            style: TextStyle(color: Colors.red, fontSize: 18),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
