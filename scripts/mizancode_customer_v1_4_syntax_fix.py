from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'buildcustomer/lib/main.dart')
s = p.read_text(encoding='utf-8')

old = "color:Colors.black45))])]])\n      ]))))"
new = "color:Colors.black45))])]]))\n      ]))))"

if old not in s:
    raise SystemExit('offers syntax anchor not found')

s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('MizanCode Customer v1.4 offers syntax fixed')
