import 'dart:io';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

const navy = Color(0xFF062A52);
const navy2 = Color(0xFF0A3A70);
const cyan = Color(0xFF11D5D5);
const blue = Color(0xFF168BFF);
const bg = Color(0xFFF4F8FC);
const cloudServer = 'https://lean-enlightened-javabytecode--hassanabdali196.replit.app';

const mizanLogoSvg = '''<svg width="360" height="360" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#18E0D0"/><stop offset="1" stop-color="#168BFF"/></linearGradient></defs><rect width="360" height="360" rx="72" fill="#062A52"/><circle cx="180" cy="52" r="22" fill="url(#g)"/><path d="M180 82v140" stroke="url(#g)" stroke-width="28" stroke-linecap="round"/><path d="M90 103c38-18 142-18 180 0" fill="none" stroke="url(#g)" stroke-width="15" stroke-linecap="round"/><path d="M82 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M278 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M91 157l-18 18 18 18" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M274 153l-14 44M282 157l18 18-18 18" fill="none" stroke="#18E0D0" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M115 235c34 28 96 28 130 0" fill="none" stroke="#168BFF" stroke-width="13" stroke-linecap="round"/></svg>''';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MizanCodeApp());
}

class MizanCodeApp extends StatelessWidget {
  const MizanCodeApp({super.key});
  @override
  Widget build(BuildContext context) {
    final base = ThemeData(useMaterial3: true, colorScheme: ColorScheme.fromSeed(seedColor: navy), scaffoldBackgroundColor: bg);
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

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  void _open(BuildContext context, String path, String title) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => PortalPage(title: title, url: '$cloudServer$path')));
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
            children: [
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(colors: [navy, navy2], begin: Alignment.topRight, end: Alignment.bottomLeft),
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: const [BoxShadow(color: Color(0x22062A52), blurRadius: 24, offset: Offset(0, 12))],
                ),
                child: Column(children: [
                  SvgPicture.string(mizanLogoSvg, height: 132),
                  const SizedBox(height: 8),
                  Text('ميزان كود', style: GoogleFonts.tajawal(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800)),
                  Text('MizanCode', style: GoogleFonts.poppins(color: cyan, fontSize: 20, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  const Text('حلول برمجية وتطبيقات وأنظمة محاسبية', style: TextStyle(color: Colors.white70, fontSize: 14)),
                ]),
              ),
              const SizedBox(height: 22),
              _card(context, Icons.point_of_sale_rounded, 'نظام الأعمال والكاشير', 'المبيعات • المنتجات • الديون • المخزون • التقارير • الذكاء الاصطناعي', '/', 'MizanCode Business'),
              const SizedBox(height: 14),
              _card(context, Icons.workspace_premium_rounded, 'بطاقة الولاء والنقاط', 'رصيد النقاط • مسح الفاتورة • استبدال النقاط بخصم عبر QR', '/customer', 'MizanCode Loyalty'),
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(22), border: Border.all(color: const Color(0xFFE0EAF4))),
                child: const Row(children: [
                  Icon(Icons.cloud_done_rounded, color: Color(0xFF11BFAE), size: 28),
                  SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('الخادم السحابي', style: TextStyle(fontWeight: FontWeight.w800, color: navy)),
                    SizedBox(height: 4),
                    Text('متصل تلقائياً بـ MizanCode Cloud', style: TextStyle(color: Colors.black54, fontSize: 12)),
                  ])),
                ]),
              ),
              const SizedBox(height: 18),
              const Center(child: Text('MizanCode v4.2 • Cloud Connected', style: TextStyle(color: Colors.black45, fontSize: 12))),
            ],
          ),
        ),
      ),
    );
  }

  Widget _card(BuildContext context, IconData icon, String title, String subtitle, String path, String pageTitle) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(24),
      child: InkWell(
        onTap: () => _open(context, path, pageTitle),
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

class PortalPage extends StatefulWidget {
  final String title;
  final String url;
  const PortalPage({super.key, required this.title, required this.url});
  @override
  State<PortalPage> createState() => _PortalPageState();
}

class _PortalPageState extends State<PortalPage> {
  late final WebViewController controller;
  double progress = 0;

  @override
  void initState() {
    super.initState();
    controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.white)
      ..addJavaScriptChannel('MizanNative', onMessageReceived: (message) async {
        final value = await _scanCode();
        final safe = value.replaceAll('\\', '\\\\').replaceAll("'", "\\'").replaceAll('\n', '');
        final safeId = message.message.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
        await controller.runJavaScript("if(window.mizanScanResult){window.mizanScanResult('$safeId','$safe');}");
      })
      ..setNavigationDelegate(NavigationDelegate(
        onProgress: (p) => setState(() => progress = p / 100),
        onPageFinished: (_) => _injectBridge(),
      ))
      ..loadRequest(Uri.parse(widget.url));
  }

  Future<String> _scanCode() async {
    if (!(Platform.isAndroid || Platform.isIOS)) return '';
    return await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScannerPage())) ?? '';
  }

  Future<void> _injectBridge() async {
    await controller.runJavaScript('''
      window.MizanNativeBridge = window.MizanNativeBridge || {};
      window.MizanNativeBridge.scanCode = function(id) { MizanNative.postMessage(id); };
      window.MizanNative = window.MizanNativeBridge;
    ''');
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(title: Text(widget.title), actions: [IconButton(onPressed: controller.reload, icon: const Icon(Icons.refresh_rounded))]),
        body: Stack(children: [
          WebViewWidget(controller: controller),
          if (progress < 1) LinearProgressIndicator(value: progress, color: cyan, backgroundColor: const Color(0xFFE7EFF7)),
        ]),
      ),
    );
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});
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
      appBar: AppBar(title: const Text('قارئ الباركود / QR')),
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
