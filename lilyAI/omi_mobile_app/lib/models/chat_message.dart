class ChatMessage {
  final String role;
  final String content;
  ChatMessage({required this.role, required this.content});
  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        role: json['role'],
        content: json['content'],
      );
  Map<String, dynamic> toJson() => {
        'role': role,
        'content': content,
      };
}
