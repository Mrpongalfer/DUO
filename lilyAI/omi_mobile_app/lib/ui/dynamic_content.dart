import 'package:flutter/material.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/github.dart';
import 'package:charts_flutter/flutter.dart' as charts;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:clipboard/clipboard.dart';

class DynamicContent extends StatelessWidget {
  final Map<String, String> msg;
  const DynamicContent({super.key, required this.msg});
  @override
  Widget build(BuildContext context) {
    final content = msg['content'] ?? '';
    if (content.startsWith('```')) {
      final code = content.replaceAll('```', '');
      return Card(
        child: Column(
          children: [
            HighlightView(
              code,
              language: 'python',
              theme: githubTheme,
              padding: const EdgeInsets.all(8),
            ),
            IconButton(
              icon: const Icon(Icons.copy),
              onPressed: () => FlutterClipboard.copy(code),
            ),
          ],
        ),
      );
    } else if (content.startsWith('chart:')) {
      // Example: chart:metric1,10;metric2,20
      final data = content.substring(6).split(';').map((e) {
        final parts = e.split(',');
        return ChartData(parts[0], int.parse(parts[1]));
      }).toList();
      return SizedBox(
        height: 150,
        child: charts.BarChart([
          charts.Series<ChartData, String>(
            id: 'Metrics',
            colorFn: (_, __) => charts.MaterialPalette.blue.shadeDefault,
            domainFn: (ChartData d, _) => d.label,
            measureFn: (ChartData d, _) => d.value,
            data: data,
          )
        ]),
      );
    } else if (content.startsWith('#') || content.contains('
')) {
      return MarkdownBody(data: content);
    } else {
      return ListTile(
        title: Text(content),
      );
    }
  }
}

class ChartData {
  final String label;
  final int value;
  ChartData(this.label, this.value);
}
