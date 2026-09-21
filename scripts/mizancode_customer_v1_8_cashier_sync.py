from pathlib import Path
import re, sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'buildcustomer/lib/main.dart')
s=p.read_text(encoding='utf-8')

# Keep loyalty rules identical to the cashier/cloud rules.
s=s.replace("  int loyaltySpend = 100000;", "  int loyaltySpend = 200000;", 1)
s=s.replace("  int loyaltyEarn = 1;", "  int loyaltyEarn = 5;", 1)
s=s.replace("  int loyaltyBlock = 1;", "  int loyaltyBlock = 5;", 1)
s=s.replace("  int loyaltyValue = 1000;", "  int loyaltyValue = 3000;", 1)

s=s.replace(
"""    loyaltySpend = 100000;\n    loyaltyEarn = 1;\n    loyaltyBlock = 1;\n    loyaltyValue = 1000;""",
"""    loyaltySpend = 200000;\n    loyaltyEarn = 5;\n    loyaltyBlock = 5;\n    loyaltyValue = 3000;""",
1)

# Value fallback must follow the cashier's redemption block.
s=s.replace("final block=loyaltyBlock>0?loyaltyBlock:1;", "final block=loyaltyBlock>0?loyaltyBlock:5;", 1)

# Poll frequently while open, but never start a second request while one is active.
s=s.replace(
"_autoSyncTimer = Timer.periodic(const Duration(seconds: 2), (_) => _refreshCloud(silent: true));",
"_autoSyncTimer = Timer.periodic(const Duration(seconds: 2), (_) => _refreshCloud(silent: true));",
1)

# The cashier/cloud is the only source of truth for points. Disable local invoice-based point awarding.
pat=re.compile(r"  Future<void> _scanInvoice\(\) async \{.*?\n  \}\n\n  Map<String, dynamic> _parseInvoice", re.S)
if not pat.search(s):
    raise SystemExit('invoice scan method anchor not found')
replacement=r'''  Future<void> _scanInvoice() async {
    await _refreshCloud(silent: false);
    if(mounted){
      _msg('النقاط والمشتريات تُحدَّث تلقائياً من برنامج الكاشير. لا تحتاج إلى مسح الفاتورة.');
    }
  }

  Map<String, dynamic> _parseInvoice'''
s=pat.sub(replacement,s,count=1)

# Replace the old scan-fallback control with a clear cashier-sync status block.
old="""              SizedBox(height: 48, child: OutlinedButton.icon(onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح فاتورة — خيار احتياطي'))),\n              const SizedBox(height: 8),\n              const Text('يتم فحص الرصيد تلقائياً كل ثانيتين أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black45, fontSize: 11, height: 1.4)),"""
new="""              Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: const Color(0xFFEAF4FF), borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFC9DDF6))), child: const Row(children:[Icon(Icons.sync_rounded,color:blue),SizedBox(width:9),Expanded(child:Text('لا حاجة لمسح باركود الفاتورة. بعد إتمام البيع من الكاشير، تصل قيمة المشتريات والنقاط إلى البطاقة تلقائياً من السحابة.',style:TextStyle(fontSize:12.5,fontWeight:FontWeight.w700,color:navy,height:1.45)))])),\n              const SizedBox(height: 8),\n              const Text('تتم المزامنة تلقائياً كل ثانيتين أثناء فتح التطبيق، وكذلك فور فتحه أو الرجوع إليه.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black45, fontSize: 11, height: 1.4)),"""
if old in s:
    s=s.replace(old,new,1)
else:
    # v1.2 wording fallback
    old2="""              SizedBox(height: 60, child: FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: navy), onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded, size: 28), label: const Text('مسح باركود الفاتورة', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17)))),\n              const SizedBox(height: 8),\n              const Text('يمكن مسح فاتورة ميزان كود حتى بدون إنترنت، وستظهر النقاط وقيمتها والمشتريات مباشرةً.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black54, height: 1.5)),"""
    if old2 in s:
        s=s.replace(old2,new,1)

# Offline copy: keep card usable, but never claim local invoice scans award points.
s=s.replace(
"بدون إنترنت: الباركود ثابت ومسح فواتير ميزان كود يعمل محلياً.",
"بدون إنترنت: الباركود ثابت، وسيتم تحديث النقاط والمشتريات تلقائياً عند عودة الاتصال.",
1)

# Remove the old scanned-invoice summary from the visible UI if present.
s=re.sub(r"\s*if \(profile\['last_invoice'\] != null\) \.\.\.\[.*?\n\s*\],", "", s, count=1, flags=re.S)

# Make the server response authoritative for all displayed balances.
old_apply="""    profile['points']=toInt(c['points']??profile['points']);\n    if(c.containsKey('total_spent_iqd'))profile['total_spent_iqd']=toDouble(c['total_spent_iqd']);"""
new_apply="""    profile['points']=toInt(c['points']??profile['points']);\n    if(c.containsKey('points_value_iqd'))profile['points_value_iqd']=toInt(c['points_value_iqd']);\n    if(c.containsKey('total_spent_iqd'))profile['total_spent_iqd']=toDouble(c['total_spent_iqd']);"""
if old_apply in s:
    s=s.replace(old_apply,new_apply,1)

# If the backend does not send points_value_iqd, calculate it only from current cashier rules.
old_value="""        final pts=toInt(profile['points']);\n        final block=loyaltyBlock>0?loyaltyBlock:5;\n        profile['points_value_iqd']=(pts~/block)*loyaltyValue;"""
new_value="""        final pts=toInt(profile['points']);\n        final block=loyaltyBlock>0?loyaltyBlock:5;\n        if(toInt(profile['points_value_iqd'])<=0 && pts>0){profile['points_value_iqd']=(pts~/block)*loyaltyValue;}\n        if(pts==0){profile['points_value_iqd']=0;}"""
if old_value in s:
    s=s.replace(old_value,new_value,1)

# Clear obsolete local scanned-invoice cache on launch. It is no longer used to award points.
anchor="""    _loadInvoices();\n    Future.microtask(() => _refreshCloud(silent: true));"""
replace="""    scannedInvoices.clear();\n    Future.microtask(() async {\n      final sp=await SharedPreferences.getInstance();\n      await sp.remove('scanned_invoice_ids');\n      await _refreshCloud(silent: true);\n    });"""
if anchor in s:
    s=s.replace(anchor,replace,1)

p.write_text(s,encoding='utf-8')
print('MizanCode Customer v1.8 cashier-authoritative AutoSync patch applied')
