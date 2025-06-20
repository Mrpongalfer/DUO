import 'package:flutter/material.dart';
import 'package:omi_mobile_app/lib/api/auth_manager.dart';
import 'package:omi_mobile_app/lib/ui/dynamic_content.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:provider/provider.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Map<String, String>> _messages = [];
  final TextEditingController _controller = TextEditingController();
  late stt.SpeechToText _speech;
  bool _isListening = false;
  String _voiceInput = '';
  final FlutterTts _tts = FlutterTts();

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
  }

  void _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    setState(() {
      _messages.add({'role': 'user', 'content': text});
    });
    final authManager = Provider.of<AuthManager>(context, listen: false);
    // Secure API call to /chat with JWT
    // ...
    // For demonstration, echo response
    final response = 'Echo: $text';
    setState(() {
      _messages.add({'role': 'lily', 'content': response});
    });
    await _tts.speak(response);
  }

  void _startListening() async {
    bool available = await _speech.initialize();
    if (available) {
      setState(() => _isListening = true);
      _speech.listen(onResult: (val) {
        setState(() {
          _voiceInput = val.recognizedWords;
          _controller.text = _voiceInput;
        });
      });
    }
  }

  void _stopListening() async {
    await _speech.stop();
    setState(() => _isListening = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lily Core Nexus')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, idx) {
                final msg = _messages[idx];
                return DynamicContent(msg: msg);
              },
            ),
          ),
          Row(
            children: [
              IconButton(
                icon: Icon(_isListening ? Icons.mic : Icons.mic_none),
                onPressed: _isListening ? _stopListening : _startListening,
              ),
              Expanded(
                child: TextField(
                  controller: _controller,
                  obscureText: false,
                  enableSuggestions: false,
                  autocorrect: false,
                  decoration: const InputDecoration(hintText: 'Type a message...'),
                  onSubmitted: _sendMessage,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.send),
                onPressed: () => _sendMessage(_controller.text),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
