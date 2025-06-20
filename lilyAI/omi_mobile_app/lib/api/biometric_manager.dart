import 'package:local_auth/local_auth.dart';
import 'package:flutter/foundation.dart';

class BiometricManager with ChangeNotifier {
  final LocalAuthentication auth = LocalAuthentication();
  bool _isAuthenticated = false;
  bool get isAuthenticated => _isAuthenticated;

  Future<bool> authenticate() async {
    try {
      final bool didAuthenticate = await auth.authenticate(
        localizedReason: 'Please authenticate to unlock OMI',
        options: const AuthenticationOptions(biometricOnly: true, stickyAuth: true),
      );
      _isAuthenticated = didAuthenticate;
      notifyListeners();
      return didAuthenticate;
    } catch (e) {
      _isAuthenticated = false;
      notifyListeners();
      return false;
    }
  }
}
