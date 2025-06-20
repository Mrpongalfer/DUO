import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_certificate_manager/flutter_certificate_manager.dart';
import 'package:flutter_ssl_pinning/flutter_ssl_pinning.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class SecureInit {
  static Future<void> init() async {
    // Load client cert/key from secure storage or initial setup
    // Pin LCSAF server certificate
    await FlutterCertificateManager.addCertificateFromAsset('assets/certs/lcsaf_server.pem');
    await SslPinningPlugin.check(
      serverURL: 'https://lcsaf.local:443',
      headerHttp: {},
      sha: SHA.SHA256,
      allowedSHAFingerprints: [
        'YOUR_LCSAF_SERVER_CERT_SHA256',
      ],
      timeout: 60,
    );
  }
}
