from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'buildcustomer/lib/main.dart')
s = p.read_text(encoding='utf-8')

old = "_autoSyncTimer = Timer.periodic(const Duration(seconds: 5), (_) => _refreshCloud(silent: true));"
new = "_autoSyncTimer = Timer.periodic(const Duration(seconds: 3), (_) => _refreshCloud(silent: true));"
if old not in s:
    raise SystemExit('auto sync timer anchor not found')
s = s.replace(old, new, 1)

s = s.replace(
    "يتم فحص الرصيد تلقائياً كل 5 ثوانٍ أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.",
    "يتم تحديث النقاط والمشتريات تلقائياً كل 3 ثوانٍ أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.",
    1,
)

p.write_text(s, encoding='utf-8')
print('MizanCode Customer v1.3 Instant Sync patch applied')
