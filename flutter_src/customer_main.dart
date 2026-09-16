import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

const navy = Color(0xFF062A52);
const navy2 = Color(0xFF0A3A70);
const cyan = Color(0xFF11D5D5);
const blue = Color(0xFF168BFF);
const bg = Color(0xFFF4F8FC);
const apiUrl = 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec';

const mizanLogoSvg = '''<svg width="360" height="360" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#18E0D0"/><stop offset="1" stop-color="#168BFF"/></linearGradient></defs><rect width="360" height="360" rx="72" fill="#062A52"/><circle cx="180" cy="52" r="22" fill="url(#g)"/><path d="M180 82v140" stroke="url(#g)" stroke-width="28" stroke-linecap="round"/><path d="M90 103c38-18 142-18 180 0" fill="none" stroke="url(#g)" stroke-width="15" stroke-linecap="round"/><path d="M82 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M278 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M91 157l-18 18 18 18" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M274 153l-14 44M282 157l18 18-18 18" fill="none" stroke="#18E0D0" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M115 235c34 28 96 28 130 0" fill="none" stroke="#168BFF" stroke-width="13" stroke-linecap="round"/></svg>''';

int toInt(dynamic v) {
  if (v is int) return v;
  if (v is num) return v.round();
  return num.tryParse('${v ?? ''}')?.round() ?? 0;
}

double toDouble(dynamic v) {
  if (v is num) return v.toDouble();
  return double.tryParse('${v ?? ''}') ?? 0;
}

String fmt(num n) {
  final s = n.round().abs().toString();
  final out = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) out.write(',');
    out.write(s[i]);
  }
  return '${n < 0 ? '-' : ''}${out.toString()}';
}

class Api {
  static Future<Map<String, dynamic>> get(Map<String, String> params) async {
    final uri = Uri.parse(apiUrl).replace(queryParameters: params);
    final r = await http.get(uri).timeout(const Duration(seconds: 20));
    if (r.statusCode < 200 || r.statusCode >= 400) throw Exception('HTTP ${r.statusCode}');
    return Map<String, dynamic>.from(jsonDecode(r.body));
  }

  static Future<Map<String, dynamic>> post(Map<String, dynamic> body) async {
    final client = http.Client();
    try {
      final req = http.Request('POST', Uri.parse(apiUrl));
      req.followRedirects = false;
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(body);
      final streamed = await client.send(req).timeout(const Duration(seconds: 25));
      if (streamed.statusCode >= 300 && streamed.statusCode < 400) {
        final location = streamed.headers['location'];
        if (location == null || location.isEmpty) throw Exception('redirect');
        final rr = await client.get(Uri.parse(location)).timeout(const Duration(seconds: 25));
        if (rr.statusCode < 200 || rr.statusCode >= 400) throw Exception('HTTP ${rr.statusCode}');
        return Map<String, dynamic>.from(jsonDecode(rr.body));
      }
      final rr = await http.Response.fromStream(streamed);
      if (rr.statusCode < 200 || rr.statusCode >= 400) throw Exception('HTTP ${rr.statusCode}');
      return Map<String, dynamic>.from(jsonDecode(rr.body));
    } finally {
      client.close();
    }
  }
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MizanCustomerApp());
}

class MizanCustomerApp extends StatelessWidget {
  const MizanCustomerApp({super.key});
  @override
  Widget build(BuildContext context) {
    final base = ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: bg,
      colorScheme: ColorScheme.fromSeed(seedColor: navy),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFFDDE8F2))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFFDDE8F2))),
      ),
    );
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'بطاقة ميزان كود',
      theme: base.copyWith(textTheme: GoogleFonts.tajawalTextTheme(base.textTheme), appBarTheme: const AppBarTheme(backgroundColor: navy, foregroundColor: Colors.white, centerTitle: true)),
      home: const GatePage(),
    );
  }
}

class GatePage extends StatefulWidget {
  const GatePage({super.key});
  @override
  State<GatePage> createState() => _GatePageState();
}

class _GatePageState extends State<GatePage> {
  bool loading = true;
  Map<String, dynamic>? profile;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString('customer_profile');
    if (raw != null) {
      try { profile = Map<String, dynamic>.from(jsonDecode(raw)); } catch (_) {}
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> _registered(Map<String, dynamic> p) async {
    final sp = await SharedPreferences.getInstance();
    await sp.setString('customer_profile', jsonEncode(p));
    if (mounted) setState(() => profile = p);
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return profile == null
        ? RegistrationPage(onRegistered: _registered)
        : CustomerHome(initialProfile: profile!, onProfileChanged: _registered);
  }
}

class RegistrationPage extends StatefulWidget {
  final Future<void> Function(Map<String, dynamic>) onRegistered;
  const RegistrationPage({super.key, required this.onRegistered});
  @override
  State<RegistrationPage> createState() => _RegistrationPageState();
}

class _RegistrationPageState extends State<RegistrationPage> {
  final name = TextEditingController();
  final phone = TextEditingController();
  String category = 'family';
  bool busy = false;

  @override
  void dispose() {
    name.dispose();
    phone.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (name.text.trim().length < 2) { _msg('اكتب اسم الزبون'); return; }
    if (phone.text.trim().length < 7) { _msg('اكتب رقم الهاتف'); return; }
    setState(() => busy = true);
    try {
      final r = await Api.post({
        'action': 'create_customer',
        'name': name.text.trim(),
        'phone': phone.text.trim(),
        'card_type': category,
      });
      if (r['ok'] != true) { _msg('${r['error'] ?? 'تعذر التسجيل'}'); return; }
      final inner = r['customer'] is Map ? Map<String, dynamic>.from(r['customer']) : <String, dynamic>{};
      final barcode = '${inner['barcode'] ?? r['barcode'] ?? ''}';
      if (barcode.isEmpty) { _msg('تم التسجيل لكن لم يتم استلام الباركود'); return; }
      final p = <String, dynamic>{
        'customer_id': inner['customer_id'] ?? r['customer_id'] ?? '',
        'barcode': barcode,
        'name': inner['name'] ?? name.text.trim(),
        'phone': inner['phone'] ?? phone.text.trim(),
        'card_type': inner['card_type'] ?? category,
        'points': toInt(inner['points']),
        'points_value_iqd': toInt(inner['points_value_iqd']),
        'total_spent_iqd': toDouble(inner['total_spent_iqd']),
        'last_sync': DateTime.now().toIso8601String(),
      };
      await widget.onRegistered(p);
    } catch (_) {
      _msg('التسجيل يحتاج إنترنت. تأكد من الاتصال وحاول مرة ثانية.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void _msg(String s) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(gradient: const LinearGradient(colors: [navy, navy2]), borderRadius: BorderRadius.circular(28)),
                child: Column(children: [
                  SvgPicture.string(mizanLogoSvg, height: 112),
                  const SizedBox(height: 8),
                  const Text('بطاقة ميزان كود', style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900)),
                  Text('MizanCode Loyalty', style: GoogleFonts.poppins(color: cyan, fontSize: 18, fontWeight: FontWeight.w700)),
                ]),
              ),
              const SizedBox(height: 24),
              const Text('إنشاء بطاقة الولاء', textAlign: TextAlign.center, style: TextStyle(fontSize: 23, fontWeight: FontWeight.w900, color: navy)),
              const SizedBox(height: 6),
              const Text('سجّل مرة واحدة، وبعدها يبقى باركود بطاقتك ثابتاً داخل التطبيق.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black54, height: 1.5)),
              const SizedBox(height: 20),
              TextField(controller: name, decoration: const InputDecoration(labelText: 'الاسم الكامل', prefixIcon: Icon(Icons.person_outline_rounded))),
              const SizedBox(height: 12),
              TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'رقم الهاتف', prefixIcon: Icon(Icons.phone_outlined))),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: category,
                decoration: const InputDecoration(labelText: 'فئة البطاقة', prefixIcon: Icon(Icons.card_membership_rounded)),
                items: const [
                  DropdownMenuItem(value: 'family', child: Text('عائلة')),
                  DropdownMenuItem(value: 'children', child: Text('أطفال')),
                ],
                onChanged: (v) => setState(() => category = v ?? 'family'),
              ),
              const SizedBox(height: 18),
              SizedBox(height: 56, child: FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: navy), onPressed: busy ? null : _register, icon: const Icon(Icons.how_to_reg_rounded), label: Text(busy ? 'جارٍ التسجيل...' : 'تسجيل وإنشاء الباركود'))),
              if (busy) const Padding(padding: EdgeInsets.only(top: 14), child: LinearProgressIndicator()),
            ]),
          ),
        ),
      ),
    );
  }
}

class CustomerHome extends StatefulWidget {
  final Map<String, dynamic> initialProfile;
  final Future<void> Function(Map<String, dynamic>) onProfileChanged;
  const CustomerHome({super.key, required this.initialProfile, required this.onProfileChanged});
  @override
  State<CustomerHome> createState() => _CustomerHomeState();
}

class _CustomerHomeState extends State<CustomerHome> {
  late Map<String, dynamic> profile;
  bool syncing = false;
  bool offline = false;
  List<String> scannedInvoices = [];

  @override
  void initState() {
    super.initState();
    profile = Map<String, dynamic>.from(widget.initialProfile);
    _loadInvoices();
    _refreshCloud(silent: true);
  }

  Future<void> _loadInvoices() async {
    final p = await SharedPreferences.getInstance();
    scannedInvoices = p.getStringList('scanned_invoice_ids') ?? [];
    if (mounted) setState(() {});
  }

  Future<void> _persist() async {
    await widget.onProfileChanged(profile);
  }

  Future<void> _refreshCloud({bool silent = false}) async {
    final barcode = '${profile['barcode'] ?? ''}';
    if (barcode.isEmpty) return;
    if (!silent && mounted) setState(() => syncing = true);
    try {
      final r = await Api.get({'action': 'customer', 'barcode': barcode});
      if (r['ok'] == true && r['customer'] is Map) {
        final c = Map<String, dynamic>.from(r['customer']);
        profile['customer_id'] = c['customer_id'] ?? profile['customer_id'];
        profile['name'] = c['name'] ?? profile['name'];
        profile['phone'] = c['phone'] ?? profile['phone'];
        profile['card_type'] = c['card_type'] ?? profile['card_type'];
        profile['points'] = toInt(c['points']);
        profile['points_value_iqd'] = toInt(c['points_value_iqd']);
        profile['total_spent_iqd'] = toDouble(c['total_spent_iqd']);
        profile['last_sync'] = DateTime.now().toIso8601String();
        offline = false;
        await _persist();
      }
    } catch (_) {
      offline = true;
      if (!silent) _msg('لا يوجد إنترنت. البطاقة والرصيد المحفوظ يعملان بشكل طبيعي.');
    } finally {
      if (mounted) setState(() => syncing = false);
    }
  }

  Future<void> _scanInvoice() async {
    final raw = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const InvoiceScannerPage()));
    if (raw == null || raw.trim().isEmpty) return;
    try {
      final inv = _parseInvoice(raw.trim());
      final invoiceId = '${inv['invoice_no'] ?? inv['invoice'] ?? inv['sale_id'] ?? ''}'.trim();
      if (invoiceId.isEmpty) { _msg('باركود الفاتورة غير صالح'); return; }
      final mine = '${profile['barcode'] ?? ''}';
      final invoiceCustomer = '${inv['customer_barcode'] ?? inv['barcode'] ?? ''}';
      if (invoiceCustomer.isNotEmpty && invoiceCustomer != mine) {
        _msg('هذه الفاتورة مرتبطة ببطاقة زبون أخرى');
        return;
      }
      if (scannedInvoices.contains(invoiceId)) {
        _msg('هذه الفاتورة تم مسحها سابقاً');
        return;
      }

      final oldPoints = toInt(profile['points']);
      final oldSpent = toDouble(profile['total_spent_iqd']);
      final saleTotal = toDouble(inv['total'] ?? inv['sale_total'] ?? inv['amount']);
      var earned = toInt(inv['earned_points'] ?? inv['points_earned']);
      if (earned <= 0 && saleTotal > 0) {
        final oldBlocks = oldSpent ~/ 200000;
        final newBlocks = (oldSpent + saleTotal) ~/ 200000;
        earned = (newBlocks - oldBlocks) * 5;
      }
      final pointsAfter = inv.containsKey('points_after') ? toInt(inv['points_after']) : oldPoints + earned;
      final totalSpentAfter = inv.containsKey('total_spent_iqd') ? toDouble(inv['total_spent_iqd']) : oldSpent + saleTotal;
      profile['points'] = pointsAfter;
      profile['points_value_iqd'] = (pointsAfter ~/ 5) * 3000;
      profile['total_spent_iqd'] = totalSpentAfter;
      profile['last_invoice'] = invoiceId;
      profile['last_invoice_total'] = saleTotal;
      profile['last_invoice_earned'] = earned;
      profile['last_invoice_at'] = '${inv['created_at'] ?? DateTime.now().toIso8601String()}';
      scannedInvoices.add(invoiceId);

      final p = await SharedPreferences.getInstance();
      await p.setStringList('scanned_invoice_ids', scannedInvoices);
      await _persist();
      if (!mounted) return;
      setState(() {});
      await showDialog(context: context, builder: (_) => Directionality(textDirection: TextDirection.rtl, child: AlertDialog(
        title: const Text('تمت قراءة الفاتورة', textAlign: TextAlign.center),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.check_circle_rounded, color: Color(0xFF0BAF9A), size: 62),
          const SizedBox(height: 10),
          Text('رقم الفاتورة: $invoiceId'),
          if (saleTotal > 0) Text('قيمة المشتريات: ${fmt(saleTotal)} د.ع'),
          Text('النقاط المضافة: $earned'),
          Text('الرصيد الحالي: ${profile['points']} نقطة', style: const TextStyle(fontWeight: FontWeight.w900, color: navy)),
          Text('قيمتها: ${fmt(toInt(profile['points_value_iqd']))} د.ع'),
        ]),
        actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('تم'))],
      )));
    } catch (_) {
      _msg('هذا ليس باركود فاتورة ميزان كود');
    }
  }

  Map<String, dynamic> _parseInvoice(String raw) {
    String body = raw;
    if (raw.startsWith('MIZAN-INVOICE:')) {
      body = raw.substring('MIZAN-INVOICE:'.length);
      body = utf8.decode(base64Url.decode(base64Url.normalize(body)));
    }
    final obj = jsonDecode(body);
    if (obj is! Map) throw const FormatException();
    final m = Map<String, dynamic>.from(obj);
    final type = '${m['type'] ?? ''}';
    if (type.isNotEmpty && type != 'MIZAN_INVOICE' && type != 'MIZANCODE_INVOICE') throw const FormatException();
    return m;
  }

  void _msg(String s) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    final points = toInt(profile['points']);
    final value = toInt(profile['points_value_iqd']);
    final spent = toDouble(profile['total_spent_iqd']);
    final family = '${profile['card_type']}' != 'children';
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(title: const Text('بطاقة الولاء'), actions: [IconButton(tooltip: 'تحديث', onPressed: syncing ? null : _refreshCloud, icon: const Icon(Icons.refresh_rounded))]),
        body: RefreshIndicator(
          onRefresh: _refreshCloud,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(18),
            children: [
              if (offline) Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(14)), child: const Row(children: [Icon(Icons.offline_bolt_rounded, color: Colors.orange), SizedBox(width: 8), Expanded(child: Text('بدون إنترنت: الباركود ثابت ومسح فواتير ميزان كود يعمل محلياً.'))])),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(gradient: const LinearGradient(colors: [navy, navy2]), borderRadius: BorderRadius.circular(28), boxShadow: const [BoxShadow(color: Color(0x22062A52), blurRadius: 24, offset: Offset(0, 10))]),
                child: Column(children: [
                  Row(children: [SvgPicture.string(mizanLogoSvg, height: 58), const SizedBox(width: 10), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${profile['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 21)), Text(family ? 'بطاقة عائلة' : 'بطاقة أطفال', style: const TextStyle(color: cyan, fontWeight: FontWeight.w700))]))]),
                  const SizedBox(height: 18),
                  Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)), child: Column(children: [
                    const Text('باركود البطاقة', style: TextStyle(fontWeight: FontWeight.w900, color: navy)),
                    const SizedBox(height: 8),
                    QrImageView(data: '${profile['barcode']}', size: 205),
                    const SizedBox(height: 6),
                    SelectableText('${profile['barcode']}', textDirection: TextDirection.ltr, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
                  ])),
                  const SizedBox(height: 10),
                  const Text('اعرض هذا الباركود للكاشير عند الشراء', style: TextStyle(color: Colors.white70)),
                ]),
              ),
              const SizedBox(height: 16),
              Row(children: [
                Expanded(child: MetricBox(title: 'النقاط', value: '$points', icon: Icons.stars_rounded)),
                const SizedBox(width: 10),
                Expanded(child: MetricBox(title: 'قيمتها', value: '${fmt(value)} د.ع', icon: Icons.payments_rounded)),
              ]),
              const SizedBox(height: 10),
              MetricBox(title: 'إجمالي مشترياتي', value: '${fmt(spent)} د.ع', icon: Icons.shopping_bag_rounded, wide: true),
              const SizedBox(height: 16),
              SizedBox(height: 60, child: FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: navy), onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded, size: 28), label: const Text('مسح باركود الفاتورة', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17)))),
              const SizedBox(height: 8),
              const Text('يمكن مسح فاتورة ميزان كود حتى بدون إنترنت، وستظهر النقاط وقيمتها والمشتريات مباشرةً.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black54, height: 1.5)),
              if (profile['last_invoice'] != null) ...[
                const SizedBox(height: 16),
                Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18), border: Border.all(color: const Color(0xFFE0EAF4))), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Text('آخر فاتورة تم مسحها', style: TextStyle(fontWeight: FontWeight.w900, color: navy)),
                  const SizedBox(height: 8),
                  InfoRow('رقم الفاتورة', '${profile['last_invoice']}'),
                  InfoRow('قيمة الفاتورة', '${fmt(toDouble(profile['last_invoice_total']))} د.ع'),
                  InfoRow('النقاط المضافة', '${toInt(profile['last_invoice_earned'])}'),
                ])),
              ],
              const SizedBox(height: 16),
              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),
              if (syncing) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator()),
            ],
          ),
        ),
      ),
    );
  }
}

class MetricBox extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final bool wide;
  const MetricBox({super.key, required this.title, required this.value, required this.icon, this.wide = false});
  @override
  Widget build(BuildContext context) => Container(
    padding: EdgeInsets.symmetric(horizontal: 16, vertical: wide ? 18 : 16),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE0EAF4))),
    child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
      Icon(icon, color: blue, size: 30), const SizedBox(width: 10),
      Flexible(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(color: Colors.black54)), FittedBox(child: Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: navy))) ])),
    ]),
  );
}

class InfoRow extends StatelessWidget {
  final String label, value;
  const InfoRow(this.label, this.value, {super.key});
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(children: [Expanded(child: Text(label, style: const TextStyle(color: Colors.black54))), Text(value, style: const TextStyle(fontWeight: FontWeight.w800, color: navy))]));
}

class InvoiceScannerPage extends StatefulWidget {
  const InvoiceScannerPage({super.key});
  @override
  State<InvoiceScannerPage> createState() => _InvoiceScannerPageState();
}

class _InvoiceScannerPageState extends State<InvoiceScannerPage> {
  bool done = false;
  final controller = MobileScannerController(torchEnabled: false, formats: const [BarcodeFormat.qrCode, BarcodeFormat.code128]);

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(title: const Text('مسح باركود الفاتورة')),
        body: Stack(fit: StackFit.expand, children: [
          MobileScanner(controller: controller, onDetect: (capture) {
            if (done || capture.barcodes.isEmpty) return;
            final v = capture.barcodes.first.rawValue;
            if (v == null || v.isEmpty) return;
            done = true;
            Navigator.pop(context, v);
          }),
          Center(child: Container(width: 290, height: 220, decoration: BoxDecoration(border: Border.all(color: cyan, width: 3), borderRadius: BorderRadius.circular(24)))),
          const Positioned(top: 28, left: 20, right: 20, child: Text('وجّه الكاميرا نحو باركود/QR الموجود على فاتورة ميزان كود', textAlign: TextAlign.center, style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700))),
          Positioned(bottom: 32, left: 0, right: 0, child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            FloatingActionButton(heroTag: 'torch', backgroundColor: navy, foregroundColor: Colors.white, onPressed: controller.toggleTorch, child: const Icon(Icons.flashlight_on_rounded)),
            const SizedBox(width: 16),
            FloatingActionButton(heroTag: 'cam', backgroundColor: navy, foregroundColor: Colors.white, onPressed: controller.switchCamera, child: const Icon(Icons.cameraswitch_rounded)),
          ])),
        ]),
      ),
    );
  }
}
