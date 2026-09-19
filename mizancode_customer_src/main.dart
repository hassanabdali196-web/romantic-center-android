import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:qr_flutter/qr_flutter.dart';

const cloudUrl =
    'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec';

void main() => runApp(const CustomerApp());

Map<String, dynamic> object(dynamic value) => value is Map
    ? value.map((key, item) => MapEntry(key.toString(), item))
    : <String, dynamic>{};

num number(dynamic value) => value is num
    ? value
    : num.tryParse(value?.toString().replaceAll(',', '') ?? '') ?? 0;

String money(num value) => '${value.toStringAsFixed(0)} د.ع';

class Profile {
  final String name;
  final num points;
  final num pointsValue;
  final num totalSpent;
  final List<Map<String, dynamic>> invoices;
  final Map<String, dynamic> lastInvoice;
  final String? adTitle;
  final String? adBody;
  final String? adImage;
  final String? adUrl;

  const Profile(
      this.name,
      this.points,
      this.pointsValue,
      this.totalSpent,
      this.invoices,
      this.lastInvoice,
      this.adTitle,
      this.adBody,
      this.adImage,
      this.adUrl);

  factory Profile.fromJson(Map<String, dynamic> json) {
    final envelope = object(json['data'] ?? json);
    final data = object(envelope['customer'] ?? json['customer'] ?? envelope);
    final ad =
        object(json['advertisement'] ?? json['ad'] ?? data['advertisement']);
    final rawInvoices =
        envelope['invoices'] ?? json['invoices'] ?? data['invoices'];
    final last = object(envelope['last_invoice'] ?? data['last_invoice']);
    final summary = <String, dynamic>{...last};
    summary['invoice_no'] ??=
        envelope['last_invoice_no'] ?? data['last_invoice_no'];
    summary['invoice_no'] ??= envelope['last_invoice'] is String
        ? envelope['last_invoice']
        : data['last_invoice'] is String
            ? data['last_invoice']
            : null;
    summary['sale_total'] ??=
        envelope['last_invoice_total'] ?? data['last_invoice_total'];
    summary['earned_points'] ??=
        envelope['last_invoice_earned'] ?? data['last_invoice_earned'];
    summary['date'] ??= envelope['last_invoice_at'] ?? data['last_invoice_at'];
    return Profile(
      '${data['name'] ?? data['customer_name'] ?? 'الزبون'}',
      number(data['points'] ?? data['points_after']),
      number(data['points_value_iqd']),
      number(data['total_spent_iqd']),
      rawInvoices is List ? rawInvoices.map(object).toList() : [],
      summary,
      ad['title']?.toString(),
      ad['body']?.toString(),
      ad['image_url']?.toString(),
      ad['url']?.toString(),
    );
  }
}

class LoyaltyApi {
  final HttpClient client = HttpClient();

  Future<Map<String, dynamic>> request(String action, String barcode,
      [Map<String, String> extra = const {}]) async {
    final uri = Uri.parse(cloudUrl).replace(queryParameters: {
      'action': action,
      'customer_barcode': barcode,
      ...extra,
    });
    final request =
        await client.getUrl(uri).timeout(const Duration(seconds: 15));
    final response = await request.close().timeout(const Duration(seconds: 15));
    if (response.statusCode != 200)
      throw Exception('HTTP ${response.statusCode}');
    final decoded = jsonDecode(await utf8.decoder.bind(response).join());
    if (decoded is! Map) throw const FormatException('Expected JSON object');
    final result = object(decoded);
    if (result['ok'] == false ||
        result['success'] == false ||
        result['status'] == 'error') {
      throw Exception(result['message'] ?? 'تعذر تحميل البيانات');
    }
    return result;
  }

  Future<Profile> profile(String barcode) async =>
      Profile.fromJson(await request('customer_profile', barcode));

  void close() => client.close(force: true);
}

class CustomerApp extends StatelessWidget {
  const CustomerApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'MizanCode',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
            colorScheme:
                ColorScheme.fromSeed(seedColor: const Color(0xff087e9d)),
            useMaterial3: true),
        home: const Directionality(
            textDirection: TextDirection.rtl, child: CustomerHome()),
      );
}

class CustomerHome extends StatefulWidget {
  const CustomerHome({super.key});
  @override
  State<CustomerHome> createState() => _CustomerHomeState();
}

class _CustomerHomeState extends State<CustomerHome>
    with WidgetsBindingObserver {
  static const preferences = MethodChannel('mizancode.customer/preferences');
  final api = LoyaltyApi();
  final barcodeInput = TextEditingController();
  Timer? timer;
  String barcode = '';
  Profile? profile;
  DateTime? updatedAt;
  String? error;
  bool loading = false;
  String? lastScannedInvoice;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _restore();
    timer = Timer.periodic(const Duration(seconds: 30), (_) => refresh());
  }

  Future<void> _restore() async {
    final saved = await preferences.invokeMethod<String>('getBarcode');
    if (!mounted) return;
    setState(() {
      barcode = saved ?? '';
      barcodeInput.text = barcode;
    });
    await refresh();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) refresh();
  }

  Future<void> saveBarcode(String value) async {
    final clean = value.trim();
    if (clean.isEmpty) return;
    await preferences.invokeMethod<void>('setBarcode', clean);
    if (!mounted) return;
    setState(() {
      barcode = clean;
      profile = null;
      error = null;
    });
    await refresh();
  }

  Future<void> refresh() async {
    if (barcode.isEmpty || loading) return;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final raw = await api.request('customer_profile', barcode);
      final fresh = Profile.fromJson(raw);
      if (mounted)
        setState(() {
          profile = fresh;
          updatedAt = DateTime.now();
        });
    } catch (_) {
      if (mounted)
        setState(() {
          error = 'تعذر التحديث. تأكد من الإنترنت؛ البيانات المعروضة قديمة.';
        });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    api.close();
    barcodeInput.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> scan() async {
    final value = await Navigator.push<String>(
        context,
        MaterialPageRoute(
            builder: (_) => const ScanPage(title: 'امسح باركود الزبون')));
    if (value != null && mounted) {
      barcodeInput.text = value;
      await saveBarcode(value);
    }
  }

  Future<void> scanInvoice() async {
    final value = await Navigator.push<String>(
        context,
        MaterialPageRoute(
            builder: (_) => const ScanPage(title: 'امسح باركود الفاتورة')));
    if (value == null || !mounted) return;
    setState(() => lastScannedInvoice = value);
    await refresh();
    if (mounted)
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content:
            Text('تمت قراءة الفاتورة. راجع آخر فاتورة في حسابك بعد التحديث.'),
      ));
  }

  static const navy = Color(0xff102f53);
  static const blue = Color(0xff2088ed);
  Widget panel(Widget child) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(25),
            border: Border.all(color: const Color(0xffdbe6f2))),
        child: child,
      );

  @override
  Widget build(BuildContext context) {
    final current = profile;
    final invoice = current == null
        ? null
        : current.lastInvoice['invoice_no'] != null
            ? current.lastInvoice
            : current.invoices.isNotEmpty
                ? current.invoices.first
                : null;
    return Scaffold(
      backgroundColor: const Color(0xfff5f9ff),
      appBar: AppBar(
          backgroundColor: navy,
          foregroundColor: Colors.white,
          title: const Text('بطاقة الولاء'),
          centerTitle: true,
          actions: [
            IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: loading ? null : refresh)
          ]),
      body: RefreshIndicator(
          onRefresh: refresh,
          child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 36),
              children: [
                if (loading) const LinearProgressIndicator(),
                if (barcode.isEmpty) ...[
                  panel(Column(children: [
                    const Text('أدخل باركود بطاقة الزبون أو امسحه بالكامرة'),
                    const SizedBox(height: 10),
                    TextField(
                        controller: barcodeInput,
                        onSubmitted: saveBarcode,
                        decoration: InputDecoration(
                            labelText: 'باركود الزبون',
                            suffixIcon: IconButton(
                                onPressed: scan,
                                icon: const Icon(Icons.qr_code_scanner)))),
                    FilledButton(
                        onPressed: () => saveBarcode(barcodeInput.text),
                        child: const Text('فتح بطاقتي')),
                  ])),
                ] else ...[
                  Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                          color: navy, borderRadius: BorderRadius.circular(28)),
                      child: Column(children: [
                        Row(children: [
                          const CircleAvatar(
                              radius: 27,
                              backgroundColor: blue,
                              child: Icon(Icons.code, color: Colors.white)),
                          const SizedBox(width: 12),
                          Expanded(
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                Text(current?.name ?? 'بطاقة الزبون',
                                    style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 22,
                                        fontWeight: FontWeight.bold)),
                                const Text('بطاقة عائلة',
                                    style: TextStyle(color: Color(0xff5fe1e2))),
                              ]))
                        ]),
                        const SizedBox(height: 18),
                        Container(
                            padding: const EdgeInsets.all(15),
                            decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(25)),
                            child: Column(children: [
                              const Text('باركود البطاقة',
                                  style: TextStyle(
                                      color: navy,
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold)),
                              const SizedBox(height: 12),
                              QrImageView(
                                  data: barcode,
                                  size: 210,
                                  backgroundColor: Colors.white),
                              Text(barcode,
                                  textDirection: TextDirection.ltr,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold)),
                            ])),
                        const SizedBox(height: 13),
                        const Text('اعرض هذا الباركود للكاشير عند الشراء',
                            style: TextStyle(color: Color(0xffc7d5e7))),
                      ])),
                  const SizedBox(height: 16),
                  Row(children: [
                    Expanded(
                        child: panel(Column(children: [
                      const Text('النقاط',
                          style: TextStyle(color: Colors.grey)),
                      const Icon(Icons.stars, color: blue, size: 32),
                      Text('${current?.points ?? '—'}',
                          style: const TextStyle(fontSize: 23, color: navy)),
                    ]))),
                    const SizedBox(width: 10),
                    Expanded(
                        child: panel(Column(children: [
                      const Text('قيمتها',
                          style: TextStyle(color: Colors.grey)),
                      const Icon(Icons.account_balance_wallet,
                          color: blue, size: 32),
                      Text(current == null ? '—' : money(current.pointsValue),
                          style: const TextStyle(fontSize: 20, color: navy)),
                    ]))),
                  ]),
                  const SizedBox(height: 12),
                  panel(Column(children: [
                    const Text('إجمالي مشترياتي',
                        style: TextStyle(color: Colors.grey, fontSize: 18)),
                    const Icon(Icons.shopping_bag, color: blue, size: 32),
                    Text(current == null ? '—' : money(current.totalSpent),
                        style: const TextStyle(
                            color: navy,
                            fontSize: 25,
                            fontWeight: FontWeight.bold)),
                  ])),
                  const SizedBox(height: 16),
                  SizedBox(
                      height: 62,
                      child: FilledButton.icon(
                          style: FilledButton.styleFrom(backgroundColor: navy),
                          onPressed: scanInvoice,
                          icon: const Icon(Icons.qr_code_scanner),
                          label: const Text('مسح باركود الفاتورة',
                              style: TextStyle(fontSize: 20)))),
                  const Padding(
                      padding: EdgeInsets.all(14),
                      child: Text(
                          'الرصيد يتحدث تلقائياً من السحابة عند توفر الإنترنت.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.grey))),
                  panel(Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text('آخر فاتورة تم مسحها',
                            style: TextStyle(
                                color: navy,
                                fontSize: 18,
                                fontWeight: FontWeight.bold)),
                        const SizedBox(height: 12),
                        Text(
                            'رقم الفاتورة: ${invoice?['invoice_no'] ?? lastScannedInvoice ?? '—'}'),
                        Text(
                            'قيمة الفاتورة: ${invoice == null ? '—' : money(number(invoice['sale_total'] ?? invoice['total']))}'),
                        Text(
                            'النقاط المضافة: ${invoice?['earned_points'] ?? invoice?['points_earned'] ?? '—'}'),
                      ])),
                  const SizedBox(height: 14),
                  panel(Column(children: [
                    Text(current?.adTitle ?? 'مساحة الإعلانات والعروض',
                        style: const TextStyle(
                            color: navy, fontWeight: FontWeight.bold)),
                    if (current?.adBody != null) Text(current!.adBody!),
                    if (current?.adImage != null)
                      Image.network(current!.adImage!,
                          height: 110,
                          errorBuilder: (_, __, ___) =>
                              const Icon(Icons.campaign)),
                  ])),
                ],
                if (error != null)
                  Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(error!,
                          style: const TextStyle(color: Colors.red))),
                if (updatedAt != null)
                  Text('آخر مزامنة: $updatedAt',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey)),
              ])),
    );
  }
}

class ScanPage extends StatefulWidget {
  const ScanPage({super.key, required this.title});
  final String title;
  @override
  State<ScanPage> createState() => _ScanPageState();
}

class _ScanPageState extends State<ScanPage> {
  bool done = false;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title)),
        body: MobileScanner(onDetect: (capture) {
          if (done || capture.barcodes.isEmpty) return;
          final value = capture.barcodes.first.rawValue;
          if (value == null || value.isEmpty) return;
          done = true;
          Navigator.pop(context, value);
        }),
      );
}
