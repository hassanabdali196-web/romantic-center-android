from pathlib import Path
import re,sys
p=Path(sys.argv[1] if len(sys.argv)>1 else 'buildcustomer/lib/main.dart')
s=p.read_text(encoding='utf-8')

s=s.replace("import 'dart:convert';", "import 'dart:convert';\nimport 'dart:async';",1)
s=s.replace("class _CustomerHomeState extends State<CustomerHome> {", "class _CustomerHomeState extends State<CustomerHome> with WidgetsBindingObserver {",1)
s=s.replace("  List<String> scannedInvoices = [];", "  List<String> scannedInvoices = [];\n  Timer? _autoSyncTimer;\n  bool cloudOk = true;",1)

old="""  void initState() {\n    super.initState();\n    profile = Map<String, dynamic>.from(widget.initialProfile);\n    _loadInvoices();\n    _refreshCloud(silent: true);\n  }"""
new="""  void initState() {\n    super.initState();\n    WidgetsBinding.instance.addObserver(this);\n    profile = Map<String, dynamic>.from(widget.initialProfile);\n    _loadInvoices();\n    Future.microtask(() => _refreshCloud(silent: true));\n    _autoSyncTimer = Timer.periodic(const Duration(seconds: 5), (_) => _refreshCloud(silent: true));\n  }\n\n  @override\n  void didChangeAppLifecycleState(AppLifecycleState state) {\n    if (state == AppLifecycleState.resumed) {\n      _refreshCloud(silent: true);\n    }\n  }\n\n  @override\n  void dispose() {\n    WidgetsBinding.instance.removeObserver(this);\n    _autoSyncTimer?.cancel();\n    super.dispose();\n  }"""
if old not in s: raise SystemExit('init anchor not found')
s=s.replace(old,new,1)

pat=re.compile(r"  Future<void> _refreshCloud\(\{bool silent = false\}\) async \{.*?\n  \}\n\n  Future<void> _scanInvoice",re.S)
if not pat.search(s): raise SystemExit('refresh method anchor not found')
refresh=r'''  Future<void> _refreshCloud({bool silent = false}) async {
    final barcode = '${profile['barcode'] ?? ''}'.trim();
    if (barcode.isEmpty || syncing) return;
    if (mounted) setState(() => syncing = true);
    final oldPoints=toInt(profile['points']);
    final oldSpent=toDouble(profile['total_spent_iqd']);
    try {
      final r = await Api.get({'action': 'customer', 'barcode': barcode});
      if (r['ok'] == true && r['customer'] is Map) {
        final c = Map<String, dynamic>.from(r['customer']);
        final newPoints=toInt(c['points'] ?? c['point_balance']);
        final newSpent=toDouble(c['total_spent_iqd'] ?? c['total_spent'] ?? c['purchases_total']);
        final newValue=toInt(c['points_value_iqd']);
        profile['customer_id'] = c['customer_id'] ?? profile['customer_id'];
        profile['name'] = c['name'] ?? profile['name'];
        profile['phone'] = c['phone'] ?? profile['phone'];
        profile['card_type'] = c['card_type'] ?? profile['card_type'];
        profile['points'] = newPoints;
        profile['points_value_iqd'] = newValue>0 ? newValue : (newPoints ~/ 5) * 3000;
        profile['total_spent_iqd'] = newSpent;
        if(c['last_redeem_at']!=null)profile['last_redeem_at']=c['last_redeem_at'];
        if(c['last_redeem_points']!=null)profile['last_redeem_points']=c['last_redeem_points'];
        if(c['last_redeem_iqd']!=null)profile['last_redeem_iqd']=c['last_redeem_iqd'];
        profile['last_sync'] = DateTime.now().toIso8601String();
        offline = false;cloudOk=true;
        await _persist();
        if(!silent && mounted && (oldPoints!=newPoints || (oldSpent-newSpent).abs()>0.5)){
          _msg('تم تحديث الرصيد تلقائياً: $newPoints نقطة • ${fmt(newSpent)} د.ع مشتريات');
        }
      } else {
        cloudOk=false;
      }
    } catch (_) {
      offline = true;cloudOk=false;
      if (!silent) _msg('لا يوجد إنترنت حالياً. سيتم التحديث تلقائياً عند عودة الاتصال.');
    } finally {
      if (mounted) setState(() => syncing = false);
    }
  }

  Future<void> _scanInvoice'''
s=pat.sub(refresh,s,count=1)

# Replace prominent scan section with auto-sync status and optional scan fallback.
old_ui="""              const SizedBox(height: 16),\n              SizedBox(height: 60, child: FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: navy), onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded, size: 28), label: const Text('مسح باركود الفاتورة', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17)))),\n              const SizedBox(height: 8),\n              const Text('يمكن مسح فاتورة ميزان كود حتى بدون إنترنت، وستظهر النقاط وقيمتها والمشتريات مباشرةً.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black54, height: 1.5)),"""
new_ui="""              const SizedBox(height: 16),\n              Container(padding: const EdgeInsets.all(15), decoration: BoxDecoration(color: cloudOk ? const Color(0xFFEAF8F3) : Colors.orange.shade50, borderRadius: BorderRadius.circular(18), border: Border.all(color: cloudOk ? const Color(0xFFBCE8DC) : Colors.orange.shade200)), child: Row(children: [Icon(cloudOk ? Icons.cloud_done_rounded : Icons.cloud_sync_rounded, color: cloudOk ? const Color(0xFF0B8F72) : Colors.orange), const SizedBox(width: 10), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(cloudOk ? 'المزامنة التلقائية فعالة' : 'بانتظار الإنترنت', style: const TextStyle(fontWeight: FontWeight.w900, color: navy)), const Text('النقاط والمشتريات تتحدث تلقائياً من النظام، ولا تحتاج لمسح الفاتورة.', style: TextStyle(fontSize: 12, color: Colors.black54))])), if(syncing) const SizedBox(width:20,height:20,child:CircularProgressIndicator(strokeWidth:2))])),\n              const SizedBox(height: 10),\n              SizedBox(height: 48, child: OutlinedButton.icon(onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح فاتورة — خيار احتياطي'))),\n              const SizedBox(height: 8),\n              const Text('يتم فحص الرصيد تلقائياً كل 5 ثوانٍ أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black45, fontSize: 11, height: 1.4)),"""
if old_ui not in s: raise SystemExit('scan UI anchor not found')
s=s.replace(old_ui,new_ui,1)

# Add last redemption status before last sync when backend provides it.
anchor="""              const SizedBox(height: 16),\n              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),"""
replace="""              const SizedBox(height: 16),\n              if (profile['last_redeem_at'] != null) Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFE0EAF4))), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [const Text('آخر استبدال نقاط', style: TextStyle(fontWeight: FontWeight.w900, color: navy)), const SizedBox(height: 6), InfoRow('التاريخ', '${profile['last_redeem_at']}'), InfoRow('النقاط المستبدلة', '${toInt(profile['last_redeem_points'])}'), InfoRow('قيمة الخصم', '${fmt(toInt(profile['last_redeem_iqd']))} د.ع')])),\n              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),"""
if anchor in s:s=s.replace(anchor,replace,1)

p.write_text(s,encoding='utf-8')
print('MizanCode customer v1.2 AutoSync patch applied')
