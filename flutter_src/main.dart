import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

const apiUrl = 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DclyS6JlQ1SaONV_2K3EPWo09Zg/exec';

const mizanLogoSvg = '''<svg width="360" height="360" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#18E0D0"/><stop offset="1" stop-color="#168BFF"/></linearGradient></defs><rect width="360" height="360" rx="72" fill="#062A52"/><circle cx="180" cy="52" r="22" fill="url(#g)"/><path d="M180 82v140" stroke="url(#g)" stroke-width="28" stroke-linecap="round"/><path d="M90 103c38-18 142-18 180 0" fill="none" stroke="url(#g)" stroke-width="15" stroke-linecap="round"/><path d="M82 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M278 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M91 157l-18 18 18 18" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M274 153l-14 44M282 157l18 18-18 18" fill="none" stroke="#18E0D0" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M115 235c34 28 96 28 130 0" fill="none" stroke="#168BFF" stroke-width="13" stroke-linecap="round"/></svg>''';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MizanCodeApp());
}

class Api {
  static Future<Map<String, dynamic>> get(Map<String, String> params) async {
    final uri = Uri.parse(apiUrl).replace(queryParameters: params);
    final r = await http.get(uri).timeout(const Duration(seconds: 20));
    if (r.statusCode < 200 || r.statusCode >= 400) {
      throw Exception('HTTP ${r.statusCode}');
    }
    return Map<String, dynamic>.from(jsonDecode(r.body));
  }

  static Future<Map<String, dynamic>> post(Map<String, dynamic> body) async {
    final r = await http
        .post(Uri.parse(apiUrl), headers: const {'Content-Type': 'application/json'}, body: jsonEncode(body))
        .timeout(const Duration(seconds: 25));
    if (r.statusCode < 200 || r.statusCode >= 400) {
      throw Exception('HTTP ${r.statusCode}');
    }
    return Map<String, dynamic>.from(jsonDecode(r.body));
  }

  static Future<Map<String, dynamic>> customer(String barcode) => get({'action': 'customer', 'barcode': barcode});
}

class MizanCodeApp extends StatelessWidget {
  const MizanCodeApp({super.key});

  @override
  Widget build(BuildContext context) {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: navy),
      scaffoldBackgroundColor: bg,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFFDCE8F3))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFFDCE8F3))),
      ),
    );
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'MizanCode | ميزان كود',
      theme: base.copyWith(
        textTheme: GoogleFonts.tajawalTextTheme(base.textTheme),
        appBarTheme: const AppBarTheme(backgroundColor: navy, foregroundColor: Colors.white, centerTitle: true),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool checking = true;
  bool online = false;

  @override
  void initState() {
    super.initState();
    _health();
  }

  Future<void> _health() async {
    try {
      final r = await Api.get({'action': 'health'});
      if (mounted) setState(() { online = r['ok'] == true; checking = false; });
    } catch (_) {
      if (mounted) setState(() { online = false; checking = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: SafeArea(
          child: RefreshIndicator(
            onRefresh: _health,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
              children: [
                const BrandHeader(),
                const SizedBox(height: 22),
                MainCard(
                  icon: Icons.point_of_sale_rounded,
                  title: 'نظام الأعمال والكاشير',
                  subtitle: 'مسح بطاقة الزبون • تسجيل المبيعات • إضافة الزبائن • استبدال النقاط',
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const BusinessHome())),
                ),
                const SizedBox(height: 14),
                MainCard(
                  icon: Icons.workspace_premium_rounded,
                  title: 'بطاقة الولاء والنقاط',
                  subtitle: 'بطاقة الزبون • رصيد النقاط • قيمتها بالدينار • QR الاستبدال',
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const LoyaltyPage())),
                ),
                const SizedBox(height: 18),
                CloudStatus(checking: checking, online: online, onRetry: _health),
                const SizedBox(height: 16),
                const Center(child: Text('MizanCode v4.5 • Google Cloud', style: TextStyle(color: Colors.black45, fontSize: 12))),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class BrandHeader extends StatelessWidget {
  const BrandHeader({super.key});
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [navy, navy2], begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(28),
        boxShadow: const [BoxShadow(color: Color(0x22062A52), blurRadius: 24, offset: Offset(0, 12))],
      ),
      child: Column(children: [
        SvgPicture.string(mizanLogoSvg, height: 128),
        const SizedBox(height: 8),
        Text('ميزان كود', style: GoogleFonts.tajawal(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800)),
        Text('MizanCode', style: GoogleFonts.poppins(color: cyan, fontSize: 20, fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        const Text('حلول برمجية وتطبيقات وأنظمة محاسبية', style: TextStyle(color: Colors.white70, fontSize: 14)),
      ]),
    );
  }
}

class MainCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const MainCard({super.key, required this.icon, required this.title, required this.subtitle, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(24),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), border: Border.all(color: const Color(0xFFE0EAF4))),
          child: Row(children: [
            Container(width: 62, height: 62, decoration: BoxDecoration(gradient: const LinearGradient(colors: [cyan, blue]), borderRadius: BorderRadius.circular(20)), child: Icon(icon, color: navy, size: 32)),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800, color: navy, fontSize: 18)),
              const SizedBox(height: 5),
              Text(subtitle, style: const TextStyle(color: Colors.black54, height: 1.5)),
            ])),
            const Icon(Icons.arrow_back_ios_new_rounded, color: blue, size: 18),
          ]),
        ),
      ),
    );
  }
}

class CloudStatus extends StatelessWidget {
  final bool checking;
  final bool online;
  final Future<void> Function() onRetry;
  const CloudStatus({super.key, required this.checking, required this.online, required this.onRetry});
  @override
  Widget build(BuildContext context) {
    final c = checking ? Colors.orange : (online ? const Color(0xFF0BAF9A) : Colors.redAccent);
    final text = checking ? 'جارٍ فحص Google Cloud...' : (online ? 'متصل بـ Google Sheets بنجاح' : 'تعذر الاتصال — اضغط لإعادة المحاولة');
    return InkWell(
      onTap: () => onRetry(),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE0EAF4))),
        child: Row(children: [
          checking ? const SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 3)) : Icon(online ? Icons.cloud_done_rounded : Icons.cloud_off_rounded, color: c, size: 30),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: TextStyle(fontWeight: FontWeight.w700, color: c))),
        ]),
      ),
    );
  }
}

class BusinessHome extends StatelessWidget {
  const BusinessHome({super.key});
  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(title: const Text('MizanCode Business')),
        body: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            MainCard(icon: Icons.point_of_sale_rounded, title: 'الكاشير', subtitle: 'مسح بطاقة الزبون وتسجيل قيمة الشراء وإضافة النقاط', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CashierPage()))),
            const SizedBox(height: 14),
            MainCard(icon: Icons.person_add_alt_1_rounded, title: 'الزبائن والبطاقات', subtitle: 'إضافة زبون وتوليد بطاقة QR فريدة له', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CustomersPage()))),
            const SizedBox(height: 14),
            MainCard(icon: Icons.qr_code_scanner_rounded, title: 'استبدال QR', subtitle: 'مسح رمز الاستبدال الظاهر في تطبيق الزبون', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const RedeemScannerPage()))),
          ],
        ),
      ),
    );
  }
}

class CashierPage extends StatefulWidget {
  const CashierPage({super.key});
  @override
  State<CashierPage> createState() => _CashierPageState();
}

class _CashierPageState extends State<CashierPage> {
  final barcodeCtrl = TextEditingController();
  final totalCtrl = TextEditingController();
  Map<String, dynamic>? customer;
  bool busy = false;
  int discount = 0;
  int redeemedPoints = 0;

  @override
  void dispose() {
    barcodeCtrl.dispose();
    totalCtrl.dispose();
    super.dispose();
  }

  Future<void> _scanCustomer() async {
    final v = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScannerPage(title: 'مسح بطاقة الزبون')));
    if (v != null && v.isNotEmpty) {
      barcodeCtrl.text = v;
      await _loadCustomer();
    }
  }

  Future<void> _loadCustomer() async {
    final code = barcodeCtrl.text.trim();
    if (code.isEmpty) return;
    setState(() => busy = true);
    try {
      final r = await Api.customer(code);
      if (r['ok'] == true) {
        setState(() { customer = Map<String, dynamic>.from(r['customer']); discount = 0; redeemedPoints = 0; });
      } else {
        _msg('الزبون غير موجود');
      }
    } catch (e) {
      _msg('تعذر الاتصال بالسحابة');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _scanRedeem() async {
    final token = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScannerPage(title: 'مسح QR الاستبدال')));
    if (token == null || token.isEmpty) return;
    setState(() => busy = true);
    try {
      final r = await Api.post({'action': 'redeem_token', 'token': token});
      if (r['ok'] == true) {
        setState(() { discount = _int(r['discount_iqd']); redeemedPoints = _int(r['points_redeemed']); });
        _msg('تم قبول الاستبدال: خصم ${fmt(discount)} د.ع');
        await _loadCustomer();
      } else {
        _msg(errorText(r['error']));
      }
    } catch (_) {
      _msg('تعذر تنفيذ الاستبدال');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _directRedeem() async {
    if (customer == null) return;
    setState(() => busy = true);
    try {
      final r = await Api.post({'action': 'direct_redeem', 'customer_barcode': customer!['barcode']});
      if (r['ok'] == true) {
        setState(() { discount = _int(r['discount_iqd']); redeemedPoints = _int(r['points_redeemed']); });
        _msg('تم استبدال ${fmt(redeemedPoints)} نقطة = ${fmt(discount)} د.ع');
        await _loadCustomer();
      } else {
        _msg(errorText(r['error']));
      }
    } catch (_) {
      _msg('تعذر استبدال النقاط');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _finishSale() async {
    if (customer == null) { _msg('امسح بطاقة الزبون أولاً'); return; }
    final gross = double.tryParse(totalCtrl.text.replaceAll(',', '')) ?? 0;
    if (gross <= 0) { _msg('أدخل قيمة الشراء'); return; }
    final net = (gross - discount).clamp(0, double.infinity);
    setState(() => busy = true);
    try {
      final r = await Api.post({
        'action': 'record_sale',
        'customer_barcode': customer!['barcode'],
        'total': net,
        'discount': discount,
        'payment_method': 'cash',
        'items': <dynamic>[],
      });
      if (r['ok'] == true) {
        final earned = _int(r['earned_points']);
        final points = _int(r['total_points']);
        final value = _int(r['points_value_iqd']);
        if (!mounted) return;
        await showDialog(context: context, builder: (_) => AlertDialog(
          title: const Text('تمت عملية البيع بنجاح', textAlign: TextAlign.center),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.check_circle_rounded, color: Color(0xFF0BAF9A), size: 58),
            const SizedBox(height: 12),
            Text('النقاط المكتسبة: $earned', style: const TextStyle(fontWeight: FontWeight.w800)),
            Text('رصيد الزبون: $points نقطة'),
            Text('القيمة المتاحة: ${fmt(value)} د.ع'),
          ]),
          actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('تم'))],
        ));
        setState(() { customer = null; discount = 0; redeemedPoints = 0; barcodeCtrl.clear(); totalCtrl.clear(); });
      } else {
        _msg(errorText(r['error']));
      }
    } catch (_) {
      _msg('تعذر حفظ الفاتورة على Google Cloud');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void _msg(String s) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    final gross = double.tryParse(totalCtrl.text.replaceAll(',', '')) ?? 0;
    final net = (gross - discount).clamp(0, double.infinity);
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(title: const Text('الكاشير')),
        body: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextField(controller: barcodeCtrl, textDirection: TextDirection.ltr, decoration: InputDecoration(labelText: 'باركود الزبون', prefixIcon: const Icon(Icons.badge_outlined), suffixIcon: IconButton(onPressed: _scanCustomer, icon: const Icon(Icons.qr_code_scanner_rounded)))),
            const SizedBox(height: 10),
            FilledButton.icon(onPressed: busy ? null : _loadCustomer, icon: const Icon(Icons.person_search_rounded), label: const Text('إظهار الزبون')),
            if (busy) const Padding(padding: EdgeInsets.all(12), child: LinearProgressIndicator()),
            if (customer != null) ...[
              const SizedBox(height: 16),
              CustomerCard(data: customer!),
              const SizedBox(height: 16),
              TextField(controller: totalCtrl, keyboardType: const TextInputType.numberWithOptions(decimal: true), onChanged: (_) => setState(() {}), decoration: const InputDecoration(labelText: 'قيمة الشراء بالدينار', prefixIcon: Icon(Icons.payments_rounded))),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: OutlinedButton.icon(onPressed: busy ? null : _directRedeem, icon: const Icon(Icons.loyalty_rounded), label: const Text('استبدال نقاط الزبون'))),
                const SizedBox(width: 8),
                Expanded(child: OutlinedButton.icon(onPressed: busy ? null : _scanRedeem, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح QR استبدال'))),
              ]),
              if (discount > 0) ...[
                const SizedBox(height: 12),
                SummaryRow(label: 'خصم النقاط', value: '${fmt(discount)} د.ع', valueColor: const Color(0xFF0BAF9A)),
              ],
              SummaryRow(label: 'المبلغ بعد الخصم', value: '${fmt(net.round())} د.ع'),
              const SizedBox(height: 12),
              SizedBox(height: 54, child: FilledButton.icon(onPressed: busy ? null : _finishSale, icon: const Icon(Icons.check_circle_rounded), label: const Text('إتمام البيع وإضافة النقاط'))),
            ],
          ],
        ),
      ),
    );
  }
}

class CustomersPage extends StatefulWidget {
  const CustomersPage({super.key});
  @override
  State<CustomersPage> createState() => _CustomersPageState();
}

class _CustomersPageState extends State<CustomersPage> {
  final name = TextEditingController();
  final phone = TextEditingController();
  String type = 'family';
  bool busy = false;

  @override
  void dispose() { name.dispose(); phone.dispose(); super.dispose(); }

  Future<void> _create() async {
    if (name.text.trim().isEmpty) return;
    setState(() => busy = true);
    try {
      final r = await Api.post({'action': 'create_customer', 'name': name.text.trim(), 'phone': phone.text.trim(), 'card_type': type});
      if (r['ok'] == true && mounted) {
        final code = r['barcode'].toString();
        name.clear(); phone.clear();
        await showDialog(context: context, builder: (_) => Directionality(textDirection: TextDirection.rtl, child: AlertDialog(
          title: const Text('تم إنشاء بطاقة الزبون', textAlign: TextAlign.center),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            QrImageView(data: code, size: 190),
            const SizedBox(height: 10),
            SelectableText(code, textDirection: TextDirection.ltr, style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            const Text('هذا الرمز فريد لهذا الزبون. يمكن طباعته على بطاقة أو ربطه بتطبيق الزبون.', textAlign: TextAlign.center),
          ]),
          actions: [TextButton(onPressed: () { Clipboard.setData(ClipboardData(text: code)); ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تم نسخ الباركود'))); }, child: const Text('نسخ')), FilledButton(onPressed: () => Navigator.pop(context), child: const Text('تم'))],
        )));
      } else {
        _msg(errorText(r['error']));
      }
    } catch (_) { _msg('تعذر إنشاء الزبون'); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> _find() async {
    final code = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScannerPage(title: 'بحث ببطاقة الزبون')));
    if (code == null || code.isEmpty) return;
    try {
      final r = await Api.customer(code);
      if (r['ok'] == true && mounted) {
        showModalBottomSheet(context: context, showDragHandle: true, builder: (_) => Padding(padding: const EdgeInsets.all(20), child: CustomerCard(data: Map<String, dynamic>.from(r['customer']))));
      } else { _msg('الزبون غير موجود'); }
    } catch (_) { _msg('تعذر الاتصال'); }
  }

  void _msg(String s) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Directionality(textDirection: TextDirection.rtl, child: Scaffold(
      appBar: AppBar(title: const Text('الزبائن والبطاقات'), actions: [IconButton(onPressed: _find, icon: const Icon(Icons.qr_code_scanner_rounded))]),
      body: ListView(padding: const EdgeInsets.all(18), children: [
        const Text('إضافة زبون جديد', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: navy)),
        const SizedBox(height: 14),
        TextField(controller: name, decoration: const InputDecoration(labelText: 'اسم الزبون', prefixIcon: Icon(Icons.person_outline_rounded))),
        const SizedBox(height: 10),
        TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'رقم الهاتف', prefixIcon: Icon(Icons.phone_outlined))),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(value: type, decoration: const InputDecoration(labelText: 'فئة البطاقة'), items: const [DropdownMenuItem(value: 'family', child: Text('عائلة')), DropdownMenuItem(value: 'children', child: Text('أطفال'))], onChanged: (v) => setState(() => type = v ?? 'family')),
        const SizedBox(height: 14),
        SizedBox(height: 52, child: FilledButton.icon(onPressed: busy ? null : _create, icon: const Icon(Icons.add_card_rounded), label: const Text('إنشاء الزبون وتوليد الباركود'))),
        if (busy) const Padding(padding: EdgeInsets.all(12), child: LinearProgressIndicator()),
      ]),
    ));
  }
}

class LoyaltyPage extends StatefulWidget {
  const LoyaltyPage({super.key});
  @override
  State<LoyaltyPage> createState() => _LoyaltyPageState();
}

class _LoyaltyPageState extends State<LoyaltyPage> {
  String barcode = '';
  Map<String, dynamic>? customer;
  bool loading = true;
  bool offline = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    barcode = p.getString('loyalty_barcode') ?? '';
    final cache = p.getString('loyalty_cache');
    if (cache != null) {
      try { customer = Map<String, dynamic>.from(jsonDecode(cache)); } catch (_) {}
    }
    if (mounted) setState(() => loading = false);
    if (barcode.isNotEmpty) await _refresh(silent: true);
  }

  Future<void> _saveCustomer(Map<String, dynamic> c) async {
    final p = await SharedPreferences.getInstance();
    await p.setString('loyalty_barcode', c['barcode'].toString());
    await p.setString('loyalty_cache', jsonEncode(c));
    if (mounted) setState(() { barcode = c['barcode'].toString(); customer = c; offline = false; });
  }

  Future<void> _refresh({bool silent = false}) async {
    if (barcode.isEmpty) return;
    if (!silent && mounted) setState(() => loading = true);
    try {
      final r = await Api.customer(barcode);
      if (r['ok'] == true) await _saveCustomer(Map<String, dynamic>.from(r['customer']));
      else if (!silent) _msg('تعذر العثور على البطاقة');
    } catch (_) {
      if (mounted) setState(() => offline = true);
      if (!silent) _msg('لا يوجد اتصال. تم عرض آخر رصيد محفوظ.');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _linkScan() async {
    final v = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScannerPage(title: 'ربط بطاقة الولاء')));
    if (v != null && v.isNotEmpty) await _link(v);
  }

  Future<void> _manual() async {
    final c = TextEditingController();
    final v = await showDialog<String>(context: context, builder: (_) => Directionality(textDirection: TextDirection.rtl, child: AlertDialog(title: const Text('إدخال رمز البطاقة'), content: TextField(controller: c, textDirection: TextDirection.ltr), actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')), FilledButton(onPressed: () => Navigator.pop(context, c.text.trim()), child: const Text('ربط'))])));
    if (v != null && v.isNotEmpty) await _link(v);
  }

  Future<void> _link(String code) async {
    setState(() => loading = true);
    try {
      final r = await Api.customer(code);
      if (r['ok'] == true) await _saveCustomer(Map<String, dynamic>.from(r['customer']));
      else _msg('هذه البطاقة غير موجودة');
    } catch (_) { _msg('تعذر الاتصال بالسحابة'); }
    finally { if (mounted) setState(() => loading = false); }
  }

  Future<void> _redeem() async {
    if (barcode.isEmpty) return;
    setState(() => loading = true);
    try {
      final r = await Api.post({'action': 'create_redeem_token', 'customer_barcode': barcode});
      if (r['ok'] == true && mounted) {
        final token = r['token'].toString();
        final points = _int(r['points']);
        final value = _int(r['discount_iqd']);
        await showDialog(context: context, barrierDismissible: false, builder: (_) => Directionality(textDirection: TextDirection.rtl, child: AlertDialog(
          title: const Text('رمز استبدال النقاط', textAlign: TextAlign.center),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            QrImageView(data: token, size: 220),
            const SizedBox(height: 8),
            Text('$points نقطة = ${fmt(value)} د.ع', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: navy)),
            const SizedBox(height: 6),
            const Text('خلي الكاشير يمسح هذا الرمز. صالح لمدة دقيقتين ولمرة واحدة فقط.', textAlign: TextAlign.center),
          ]),
          actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('إغلاق'))],
        )));
        await _refresh(silent: true);
      } else { _msg(errorText(r['error'])); }
    } catch (_) { _msg('تعذر إنشاء رمز الاستبدال'); }
    finally { if (mounted) setState(() => loading = false); }
  }

  Future<void> _unlink() async {
    final p = await SharedPreferences.getInstance();
    await p.remove('loyalty_barcode'); await p.remove('loyalty_cache');
    if (mounted) setState(() { barcode = ''; customer = null; });
  }

  void _msg(String s) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Directionality(textDirection: TextDirection.rtl, child: Scaffold(
      appBar: AppBar(title: const Text('بطاقة الولاء والنقاط'), actions: [if (barcode.isNotEmpty) IconButton(onPressed: _unlink, icon: const Icon(Icons.logout_rounded))]),
      body: loading && customer == null ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.all(18), children: [
          if (barcode.isEmpty) ...[
            const BrandHeader(),
            const SizedBox(height: 22),
            const Text('اربط بطاقة الزبون مرة واحدة', textAlign: TextAlign.center, style: TextStyle(fontSize: 21, fontWeight: FontWeight.w900, color: navy)),
            const SizedBox(height: 10),
            const Text('امسح البطاقة التي يعطيك إياها المحل. بعد الربط يبقى الباركود محفوظاً داخل التطبيق حتى بدون إنترنت.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black54, height: 1.5)),
            const SizedBox(height: 18),
            SizedBox(height: 54, child: FilledButton.icon(onPressed: _linkScan, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح بطاقة الولاء'))),
            const SizedBox(height: 8),
            TextButton(onPressed: _manual, child: const Text('إدخال الرمز يدوياً')),
          ] else ...[
            if (offline) Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(14)), child: const Row(children: [Icon(Icons.offline_bolt_rounded, color: Colors.orange), SizedBox(width: 8), Expanded(child: Text('وضع بدون إنترنت: الرصيد المعروض هو آخر رصيد محفوظ.'))])),
            Card(color: Colors.white, elevation: 0, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26), side: const BorderSide(color: Color(0xFFE0EAF4))), child: Padding(padding: const EdgeInsets.all(20), child: Column(children: [
              const Text('بطاقتي', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: navy)),
              const SizedBox(height: 12),
              QrImageView(data: barcode, size: 210),
              const SizedBox(height: 8),
              SelectableText(barcode, textDirection: TextDirection.ltr, style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 16),
              Text(customer?['name']?.toString() ?? '', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            ]))),
            const SizedBox(height: 14),
            Row(children: [
              Expanded(child: MetricCard(title: 'رصيد النقاط', value: '${_int(customer?['points'])}', icon: Icons.stars_rounded)),
              const SizedBox(width: 10),
              Expanded(child: MetricCard(title: 'قيمتها بالدينار', value: '${fmt(_int(customer?['points_value_iqd']))} د.ع', icon: Icons.payments_rounded)),
            ]),
            const SizedBox(height: 14),
            SizedBox(height: 58, child: FilledButton.icon(onPressed: loading ? null : _redeem, icon: const Icon(Icons.qr_code_2_rounded), label: const Text('استبدال النقاط بالشراء'))),
            const SizedBox(height: 8),
            OutlinedButton.icon(onPressed: loading ? null : _refresh, icon: const Icon(Icons.refresh_rounded), label: const Text('تحديث الرصيد')),
          ],
        ]),
      ),
    ));
  }
}

class RedeemScannerPage extends StatefulWidget {
  const RedeemScannerPage({super.key});
  @override
  State<RedeemScannerPage> createState() => _RedeemScannerPageState();
}

class _RedeemScannerPageState extends State<RedeemScannerPage> {
  bool busy = false;
  Future<void> _scan() async {
    final token = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScannerPage(title: 'مسح QR الاستبدال')));
    if (token == null || token.isEmpty) return;
    setState(() => busy = true);
    try {
      final r = await Api.post({'action': 'redeem_token', 'token': token});
      if (!mounted) return;
      if (r['ok'] == true) {
        showDialog(context: context, builder: (_) => AlertDialog(title: const Text('تم الاستبدال', textAlign: TextAlign.center), content: Column(mainAxisSize: MainAxisSize.min, children: [const Icon(Icons.check_circle_rounded, color: Color(0xFF0BAF9A), size: 58), Text(r['customer_name']?.toString() ?? ''), Text('الخصم: ${fmt(_int(r['discount_iqd']))} د.ع', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18)), Text('النقاط المستخدمة: ${_int(r['points_redeemed'])}')]), actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('تم'))]));
      } else { _msg(errorText(r['error'])); }
    } catch (_) { _msg('تعذر تنفيذ الاستبدال'); }
    finally { if (mounted) setState(() => busy = false); }
  }
  void _msg(String s) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));
  @override
  Widget build(BuildContext context) => Directionality(textDirection: TextDirection.rtl, child: Scaffold(appBar: AppBar(title: const Text('استبدال نقاط الزبون')), body: Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [const Icon(Icons.qr_code_scanner_rounded, size: 100, color: navy), const SizedBox(height: 16), const Text('افتح تطبيق الزبون وخليه يضغط «استبدال النقاط»، ثم امسح QR الظاهر عنده.', textAlign: TextAlign.center, style: TextStyle(height: 1.6, fontSize: 16)), const SizedBox(height: 20), SizedBox(width: double.infinity, height: 54, child: FilledButton.icon(onPressed: busy ? null : _scan, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح رمز الاستبدال'))), if (busy) const Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator())])))));
}

class ScannerPage extends StatefulWidget {
  final String title;
  const ScannerPage({super.key, required this.title});
  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  bool done = false;
  final controller = MobileScannerController(torchEnabled: false, formats: const [BarcodeFormat.qrCode, BarcodeFormat.code128, BarcodeFormat.ean13, BarcodeFormat.ean8]);
  @override
  void dispose() { controller.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text(widget.title)),
      body: Stack(fit: StackFit.expand, children: [
        MobileScanner(controller: controller, onDetect: (capture) {
          if (done || capture.barcodes.isEmpty) return;
          final value = capture.barcodes.first.rawValue;
          if (value == null || value.isEmpty) return;
          done = true;
          Navigator.pop(context, value);
        }),
        Center(child: Container(width: 270, height: 210, decoration: BoxDecoration(border: Border.all(color: cyan, width: 3), borderRadius: BorderRadius.circular(22)))),
        Positioned(bottom: 34, left: 24, right: 24, child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          FloatingActionButton(heroTag: 'torch', backgroundColor: navy, foregroundColor: Colors.white, onPressed: controller.toggleTorch, child: const Icon(Icons.flashlight_on_rounded)),
          const SizedBox(width: 18),
          FloatingActionButton(heroTag: 'cam', backgroundColor: navy, foregroundColor: Colors.white, onPressed: controller.switchCamera, child: const Icon(Icons.cameraswitch_rounded)),
        ])),
      ]),
    );
  }
}

class CustomerCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const CustomerCard({super.key, required this.data});
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE0EAF4))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [const CircleAvatar(backgroundColor: Color(0xFFE7F4FF), child: Icon(Icons.person_rounded, color: navy)), const SizedBox(width: 10), Expanded(child: Text(data['name']?.toString() ?? '', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: navy)))]),
        const Divider(height: 24),
        SummaryRow(label: 'النقاط', value: '${_int(data['points'])}'),
        SummaryRow(label: 'قيمتها', value: '${fmt(_int(data['points_value_iqd']))} د.ع'),
        SummaryRow(label: 'إجمالي المشتريات', value: '${fmt(_int(data['total_spent_iqd']))} د.ع'),
        SummaryRow(label: 'الفئة', value: data['card_type']?.toString() == 'children' ? 'أطفال' : 'عائلة'),
      ]),
    );
  }
}

class MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  const MetricCard({super.key, required this.title, required this.value, required this.icon});
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFE0EAF4))), child: Column(children: [Icon(icon, color: blue, size: 30), const SizedBox(height: 7), Text(title, textAlign: TextAlign.center, style: const TextStyle(color: Colors.black54)), const SizedBox(height: 5), FittedBox(child: Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: navy))) ]));
}

class SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;
  const SummaryRow({super.key, required this.label, required this.value, this.valueColor});
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Row(children: [Expanded(child: Text(label, style: const TextStyle(color: Colors.black54))), Text(value, style: TextStyle(fontWeight: FontWeight.w900, color: valueColor ?? navy))]));
}

int _int(dynamic v) {
  if (v == null) return 0;
  if (v is num) return v.round();
  return num.tryParse(v.toString())?.round() ?? 0;
}

String fmt(num n) {
  final s = n.round().abs().toString();
  final b = StringBuffer();
  for (int i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write(',');
    b.write(s[i]);
  }
  return n < 0 ? '-${b.toString()}' : b.toString();
}

String errorText(dynamic code) {
  switch (code?.toString()) {
    case 'CUSTOMER_NOT_FOUND': return 'الزبون غير موجود';
    case 'BARCODE_ALREADY_EXISTS': return 'الباركود مستخدم مسبقاً';
    case 'NOT_ENOUGH_POINTS': return 'رصيد النقاط غير كافٍ للاستبدال';
    case 'TOKEN_NOT_FOUND': return 'رمز الاستبدال غير صحيح';
    case 'TOKEN_ALREADY_USED': return 'رمز الاستبدال مستخدم مسبقاً';
    case 'TOKEN_EXPIRED': return 'انتهت صلاحية رمز الاستبدال';
    case 'INSUFFICIENT_POINTS': return 'رصيد النقاط غير كافٍ';
    case 'INVALID_TOTAL': return 'قيمة الشراء غير صحيحة';
    default: return 'تعذر تنفيذ العملية';
  }
}
