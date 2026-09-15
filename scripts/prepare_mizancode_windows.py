from pathlib import Path
import re

main = Path('buildwin/lib/main.dart')
s = main.read_text(encoding='utf-8')

api = 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec'
s = re.sub(
    r"const apiUrl = 'https://script\.google\.com/macros/s/[^']+/exec';",
    f"const apiUrl = '{api}';",
    s,
)
s = re.sub(
    r'MizanCode(?: Desktop)? v4\.[0-9.]+ • Google Cloud',
    'MizanCode Desktop v4.8.1 • Google Cloud',
    s,
)

old = """  static Future<Map<String, dynamic>> post(Map<String, dynamic> body) async {
    final r = await http
        .post(Uri.parse(apiUrl), headers: const {'Content-Type': 'application/json'}, body: jsonEncode(body))
        .timeout(const Duration(seconds: 25));
    if (r.statusCode < 200 || r.statusCode >= 400) {
      throw Exception('HTTP ${r.statusCode}');
    }
    return Map<String, dynamic>.from(jsonDecode(r.body));
  }
"""

new = """  static Future<Map<String, dynamic>> post(Map<String, dynamic> body) async {
    final client = http.Client();
    try {
      final request = http.Request('POST', Uri.parse(apiUrl));
      request.followRedirects = false;
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
      final streamed = await client.send(request).timeout(const Duration(seconds: 25));

      if (streamed.statusCode >= 300 && streamed.statusCode < 400) {
        final location = streamed.headers['location'];
        if (location == null || location.isEmpty) {
          throw Exception('REDIRECT_WITHOUT_LOCATION');
        }
        final redirected = await client.get(Uri.parse(location)).timeout(const Duration(seconds: 25));
        if (redirected.statusCode < 200 || redirected.statusCode >= 400) {
          throw Exception('HTTP ${redirected.statusCode}');
        }
        return Map<String, dynamic>.from(jsonDecode(redirected.body));
      }

      final response = await http.Response.fromStream(streamed);
      if (response.statusCode < 200 || response.statusCode >= 400) {
        throw Exception('HTTP ${response.statusCode}');
      }
      return Map<String, dynamic>.from(jsonDecode(response.body));
    } finally {
      client.close();
    }
  }
"""

if old in s:
    s = s.replace(old, new)
elif 'request.followRedirects = false;' not in s:
    raise SystemExit('Expected Api.post block not found and redirect fix is absent')

main.write_text(s, encoding='utf-8')

pubspec = Path('buildwin/pubspec.yaml')
p = pubspec.read_text(encoding='utf-8')
p = re.sub(r'^version:\s*.*$', 'version: 4.8.1+49', p, flags=re.M)
pubspec.write_text(p, encoding='utf-8')

cmake = Path('buildwin/windows/CMakeLists.txt')
c = cmake.read_text(encoding='utf-8')
c = c.replace('set(BINARY_NAME "mizancode")', 'set(BINARY_NAME "MizanCode")')
cmake.write_text(c, encoding='utf-8')

runner = Path('buildwin/windows/runner/main.cpp')
if runner.exists():
    r = runner.read_text(encoding='utf-8')
    r = r.replace('L"mizancode"', 'L"MizanCode"')
    runner.write_text(r, encoding='utf-8')

print('Prepared MizanCode Desktop v4.8.1')
print('Using Google Apps Script:', api)
