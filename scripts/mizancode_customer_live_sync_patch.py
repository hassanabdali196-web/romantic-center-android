from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'buildcustomer/lib/main.dart')
s = p.read_text(encoding='utf-8')

# Increase sync responsiveness while the loyalty card is open.
s = s.replace("Timer.periodic(const Duration(seconds: 5)", "Timer.periodic(const Duration(seconds: 3)", 1)

# Make successful sync time visible in the saved profile.
old = """        profile['last_sync'] = DateTime.now().toIso8601String();\n        offline = false;cloudOk=true;"""
new = """        final syncNow = DateTime.now();\n        profile['last_sync'] = syncNow.toIso8601String();\n        profile['last_sync_display'] = '${syncNow.hour.toString().padLeft(2,'0')}:${syncNow.minute.toString().padLeft(2,'0')}:${syncNow.second.toString().padLeft(2,'0')}';\n        offline = false;cloudOk=true;"""
if old in s:
    s = s.replace(old, new, 1)

# Clear message: no invoice scan is required for official points.
old = """Text(cloudOk ? 'المزامنة التلقائية فعالة' : 'بانتظار الإنترنت', style: const TextStyle(fontWeight: FontWeight.w900, color: navy)), const Text('النقاط والمشتريات تتحدث تلقائياً من النظام، ولا تحتاج لمسح الفاتورة.', style: TextStyle(fontSize: 12, color: Colors.black54))"""
new = """Text(cloudOk ? 'مزامنة مباشرة مع نظام الكاشير' : 'بانتظار الإنترنت', style: const TextStyle(fontWeight: FontWeight.w900, color: navy)), Text(cloudOk ? 'النقاط وإجمالي المشتريات تتحدث تلقائياً من سطح المكتب بدون مسح الفاتورة. آخر تحديث: ${profile['last_sync_display'] ?? 'الآن'}' : 'عند عودة الإنترنت سيجلب التطبيق آخر رصيد ومشتريات تلقائياً.', style: const TextStyle(fontSize: 12, color: Colors.black54))"""
if old in s:
    s = s.replace(old, new, 1)

s = s.replace('كل 5 ثوانٍ أثناء فتح التطبيق', 'كل 3 ثوانٍ أثناء فتح التطبيق', 1)

# Add a direct cloud refresh button beside the optional QR fallback.
old = """SizedBox(height: 48, child: OutlinedButton.icon(onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح فاتورة — خيار احتياطي'))),"""
new = """Row(children:[Expanded(child:SizedBox(height:48,child:OutlinedButton.icon(onPressed: syncing ? null : () => _refreshCloud(silent: false), icon: const Icon(Icons.sync_rounded), label: const Text('تحديث الرصيد الآن')))),const SizedBox(width:8),Expanded(child:SizedBox(height:48,child:OutlinedButton.icon(onPressed: _scanInvoice, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text('مسح فاتورة احتياطي'))))]),"""
if old in s:
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Stable loyalty live sync patch applied')
