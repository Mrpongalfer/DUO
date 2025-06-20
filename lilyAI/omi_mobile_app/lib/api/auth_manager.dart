import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AuthManager with ChangeNotifier {
  final _storage = const FlutterSecureStorage();
  String? _jwt;
  String? get jwt => _jwt;

  Future<bool> login(String username, String password, String clientCert, String clientKey) async {
    // mTLS handshake is handled at the native layer or via a custom channel
    final response = await http.post(
      Uri.parse('https://lcsaf.local:443/auth/token'),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'username': username,
        'password': password,
      },
    );
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      _jwt = data['access_token'];
      await _storage.write(key: 'jwt', value: _jwt);
      notifyListeners();
      return true;
    }
    return false;
  }

  Future<void> loadJwt() async {
    _jwt = await _storage.read(key: 'jwt');
    notifyListeners();
  }

  Future<void> logout() async {
    _jwt = null;
    await _storage.delete(key: 'jwt');
    notifyListeners();
  }
}
