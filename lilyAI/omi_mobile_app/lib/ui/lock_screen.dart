import 'package:flutter/material.dart';
import 'package:omi_mobile_app/lib/api/biometric_manager.dart';
import 'package:provider/provider.dart';
import 'chat_screen.dart';

class LockScreen extends StatelessWidget {
  const LockScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final biometricManager = Provider.of<BiometricManager>(context);
    return Scaffold(
      body: Center(
        child: biometricManager.isAuthenticated
            ? const ChatScreen()
            : ElevatedButton.icon(
                icon: const Icon(Icons.fingerprint),
                label: const Text('Unlock with Biometrics'),
                onPressed: () async {
                  await biometricManager.authenticate();
                },
              ),
      ),
    );
  }
}
