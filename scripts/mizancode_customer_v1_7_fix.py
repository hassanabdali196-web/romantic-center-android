from pathlib import Path
import re, sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'buildcustomer/lib/main.dart')
s=p.read_text(encoding='utf-8')

# Robust GET for Google Apps Script redirects on Android.
pat=re.compile(r"  static Future<Map<String, dynamic>> get\(Map<String, String> params\) async \{.*?\n  \}\n\n  static Future<Map<String, dynamic>> post",re.S)
if not pat.search(s):
    raise SystemExit('Api.get anchor not found')
new_get=r'''  static Future<Map<String, dynamic>> get(Map<String, String> params) async {
    final client=http.Client();
    try{
      final uri=Uri.parse(apiUrl).replace(queryParameters:params);
      final req=http.Request('GET',uri);
      req.followRedirects=false;
      req.headers['Accept']='application/json';
      final streamed=await client.send(req).timeout(const Duration(seconds:15));
      if(streamed.statusCode>=300 && streamed.statusCode<400){
        final loc=streamed.headers['location'];
        if(loc==null||loc.isEmpty) throw Exception('redirect_without_location');
        final rr=await client.get(Uri.parse(loc),headers:{'Accept':'application/json'}).timeout(const Duration(seconds:15));
        if(rr.statusCode<200||rr.statusCode>=400) throw Exception('HTTP ${rr.statusCode}');
        return Map<String,dynamic>.from(jsonDecode(rr.body));
      }
      final rr=await http.Response.fromStream(streamed);
      if(rr.statusCode<200||rr.statusCode>=400) throw Exception('HTTP ${rr.statusCode}');
      return Map<String,dynamic>.from(jsonDecode(rr.body));
    }finally{client.close();}
  }

  static Future<Map<String, dynamic>> post'''
s=pat.sub(new_get,s,count=1)

# Current loyalty defaults. Cloud may override these if loyalty_settings exists.
s=s.replace("  int loyaltySpend = 200000;", "  int loyaltySpend = 100000;",1)
s=s.replace("  int loyaltyEarn = 5;", "  int loyaltyEarn = 1;",1)
s=s.replace("  int loyaltyBlock = 5;", "  int loyaltyBlock = 1;",1)
s=s.replace("  int loyaltyValue = 3000;", "  int loyaltyValue = 1000;",1)

old_init="""    loyaltySpend = toInt(profile['points_spend_iqd']) > 0 ? toInt(profile['points_spend_iqd']) : 200000;\n    loyaltyEarn = toInt(profile['points_earn']) > 0 ? toInt(profile['points_earn']) : 5;\n    loyaltyBlock = toInt(profile['redeem_block']) > 0 ? toInt(profile['redeem_block']) : 5;\n    loyaltyValue = toInt(profile['redeem_iqd']) > 0 ? toInt(profile['redeem_iqd']) : 3000;"""
new_init="""    loyaltySpend = 100000;\n    loyaltyEarn = 1;\n    loyaltyBlock = 1;\n    loyaltyValue = 1000;\n    profile['points_spend_iqd']=loyaltySpend;\n    profile['points_earn']=loyaltyEarn;\n    profile['redeem_block']=loyaltyBlock;\n    profile['redeem_iqd']=loyaltyValue;"""
if old_init in s:
    s=s.replace(old_init,new_init,1)

# Fallback customer recovery through the already deployed list_customers endpoint.
pat=re.compile(r"  Future<Map<String,dynamic>\?> _recoverCustomerByPhone\(\)async\{.*?\n  \}\n",re.S)
if not pat.search(s):
    raise SystemExit('recover customer anchor not found')
recover=r'''  Future<Map<String,dynamic>?> _recoverCustomerByPhone()async{
    final phone='${profile['phone']??''}'.trim();
    final barcode='${profile['barcode']??''}'.trim();
    try{
      final r=await Api.get({'action':'list_customers'});
      if(r['ok']==true&&r['customers'] is List){
        for(final raw in (r['customers'] as List)){
          if(raw is! Map)continue;
          final c=Map<String,dynamic>.from(raw);
          if(barcode.isNotEmpty&&'${c['barcode']??''}'.trim()==barcode)return c;
          if(phone.isNotEmpty&&'${c['phone']??''}'.trim()==phone)return c;
        }
      }
    }catch(_){}
    return null;
  }
'''
s=pat.sub(recover,s,count=1)

# When customer GET returns any non-ok response, try list fallback rather than assuming no Internet.
old="""      if(r['ok']==true&&r['customer'] is Map){\n        customer=Map<String,dynamic>.from(r['customer']);\n      }else if('${r['error']}'=='customer_not_found'){\n        customer=await _recoverCustomerByPhone();\n      }"""
new="""      if(r['ok']==true&&r['customer'] is Map){\n        customer=Map<String,dynamic>.from(r['customer']);\n      }else{\n        customer=await _recoverCustomerByPhone();\n      }"""
if old in s:
    s=s.replace(old,new,1)

# Current point value rule: each point = 1000 IQD.
s=s.replace("final block=loyaltyBlock>0?loyaltyBlock:5;", "final block=loyaltyBlock>0?loyaltyBlock:1;",1)

p.write_text(s,encoding='utf-8')
print('MizanCode Customer v1.7 final sync fix applied')
