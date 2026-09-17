from pathlib import Path
import re, sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

# Fix one missing close-parenthesis in the v6 login screen.
login_bad = """    const SizedBox(height:12),const Text('أول تشغيل: admin / 1234 — غيّر الرمز من المستخدمين والصلاحيات.',textAlign:TextAlign.center,style:TextStyle(fontSize:11,color:Colors.black45))
  ]))))));"""
login_good = """    const SizedBox(height:12),const Text('أول تشغيل: admin / 1234 — غيّر الرمز من المستخدمين والصلاحيات.',textAlign:TextAlign.center,style:TextStyle(fontSize:11,color:Colors.black45))
  ])))))));"""
if login_bad not in s:
    raise SystemExit('login syntax anchor not found')
s = s.replace(login_bad, login_good, 1)

# Rewrite debt-history dialogs in readable Dart; the v6 one-line versions missed parentheses.
debt_hist_pat = re.compile(r"Future<void> showCustomerDebtHistory\(.*?\n\nFuture<void> showPaymentsReport", re.S)
if not debt_hist_pat.search(s):
    raise SystemExit('showCustomerDebtHistory anchor not found')

debt_hist = r'''Future<void> showCustomerDebtHistory(BuildContext context,Map<String,dynamic> d) async {
  final cid='${d['customer_id'] ?? ''}';
  final list=app.debtPayments.where((p)=>cid.isNotEmpty?'${p['customer_id']}'==cid:'${p['customer_name']}'=='${d['customer_name']}').toList();
  await showDialog(
    context:context,
    builder:(c)=>AlertDialog(
      title:Text('تقرير مدفوعات ${d['customer_name']}'),
      content:SizedBox(
        width:650,
        height:420,
        child:list.isEmpty
          ? const Center(child:Text('لا توجد دفعات مسجلة'))
          : ListView.separated(
              itemCount:list.length,
              separatorBuilder:(_,__)=>const Divider(),
              itemBuilder:(_,i){
                final p=list[i];
                return ListTile(
                  leading:const CircleAvatar(backgroundColor:Color(0xFFEAF8F8),child:Icon(Icons.payments,color:navy)),
                  title:Text('${money(asDouble(p['amount']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w900)),
                  subtitle:Text('${p['created_at']}  •  ${p['invoice']}'),
                  trailing:Text('المتبقي ${money(asDouble(p['remaining_after']))}')
                );
              }
            )
      ),
      actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]
    )
  );
}

Future<void> showPaymentsReport'''
s = debt_hist_pat.sub(debt_hist, s, count=1)

payments_pat = re.compile(r"Future<void> showPaymentsReport\(.*?\n\nclass ReturnsPage", re.S)
if not payments_pat.search(s):
    raise SystemExit('showPaymentsReport anchor not found')

payments = r'''Future<void> showPaymentsReport(BuildContext context) async {
  await showDialog(
    context:context,
    builder:(c)=>AlertDialog(
      title:const Text('سجل جميع مدفوعات الديون'),
      content:SizedBox(
        width:760,
        height:480,
        child:app.debtPayments.isEmpty
          ? const Center(child:Text('لا توجد مدفوعات بعد'))
          : ListView.builder(
              itemCount:app.debtPayments.length,
              itemBuilder:(_,i){
                final p=app.debtPayments[i];
                return ListTile(
                  leading:const Icon(Icons.receipt_long,color:navy),
                  title:Text('${p['customer_name']} — ${money(asDouble(p['amount']))} د.ع'),
                  subtitle:Text('${p['created_at']} • ${p['invoice']}'),
                  trailing:Text('متبقي ${money(asDouble(p['remaining_after']))}')
                );
              }
            )
      ),
      actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]
    )
  );
}

class ReturnsPage'''
s = payments_pat.sub(payments, s, count=1)

# Rewrite the user editor dialog. The original generated one-line dialog attached `actions`
# to the wrong widget because of a missing close-parenthesis.
user_pat = re.compile(r"Future<void> editUserDialogV6\(.*?\n\nclass SettingsPage", re.S)
if not user_pat.search(s):
    raise SystemExit('editUserDialogV6 anchor not found')

user_dialog = r'''Future<void> editUserDialogV6(BuildContext context,[Map<String,dynamic>? old]) async {
  final name=TextEditingController(text:old==null?'':'${old['name'] ?? ''}');
  final username=TextEditingController(text:old==null?'':'${old['username'] ?? ''}');
  final password=TextEditingController();
  String role=old==null?'كاشير':'${old['role'] ?? 'كاشير'}';
  final initialPerms=old==null
      ? <String>['sale']
      : List<String>.from((old['permissions'] as List?) ?? const []);
  final perms=<String>{...initialPerms};

  await showDialog(
    context:context,
    builder:(c)=>StatefulBuilder(
      builder:(c,setS)=>AlertDialog(
        title:Text(old==null?'إضافة مستخدم':'تعديل بيانات المستخدم'),
        content:SizedBox(
          width:590,
          child:SingleChildScrollView(
            child:Column(
              mainAxisSize:MainAxisSize.min,
              children:[
                TextField(controller:name,decoration:const InputDecoration(labelText:'الاسم الكامل')),
                const SizedBox(height:10),
                TextField(controller:username,decoration:const InputDecoration(labelText:'اسم المستخدم')),
                const SizedBox(height:10),
                TextField(controller:password,obscureText:true,decoration:InputDecoration(labelText:old==null?'الرمز السري':'رمز سري جديد (اتركه فارغاً لعدم التغيير)')),
                const SizedBox(height:10),
                DropdownButtonFormField<String>(
                  value:role,
                  items:['كاشير','موظف','مدير'].map((e)=>DropdownMenuItem(value:e,child:Text(e))).toList(),
                  onChanged:(v)=>setS((){
                    role=v!;
                    if(role=='مدير'){
                      perms..clear()..add('all');
                    }else{
                      perms.remove('all');
                    }
                  }),
                  decoration:const InputDecoration(labelText:'الدور')
                ),
                const SizedBox(height:14),
                Align(alignment:Alignment.centerRight,child:Text('الصلاحيات',style:Theme.of(c).textTheme.titleMedium?.copyWith(fontWeight:FontWeight.w900,color:navy))),
                const SizedBox(height:8),
                Wrap(
                  spacing:8,
                  runSpacing:8,
                  children:permissionLabelsV6.entries.where((e)=>e.key!='all').map((e)=>FilterChip(
                    label:Text(e.value),
                    selected:perms.contains('all')||perms.contains(e.key),
                    onSelected:role=='مدير'?null:(v)=>setS(()=>v?perms.add(e.key):perms.remove(e.key))
                  )).toList()
                )
              ]
            )
          )
        ),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),
          FilledButton.icon(
            style:FilledButton.styleFrom(backgroundColor:navy),
            onPressed:() async {
              if(name.text.trim().isEmpty||username.text.trim().isEmpty||(old==null&&password.text.isEmpty))return;
              final duplicate=app.users.any((u)=>u!=old&&'${u['username']}'.toLowerCase()==username.text.trim().toLowerCase());
              if(duplicate){
                ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('اسم المستخدم مستخدم مسبقاً')));
                return;
              }
              final data=old??<String,dynamic>{'id':uid('USR'),'active':true};
              data['name']=name.text.trim();
              data['username']=username.text.trim();
              data['role']=role;
              data['permissions']=role=='مدير'?['all']:perms.toList();
              if(password.text.isNotEmpty)data['password_hash']=passwordHash(password.text);
              if(old==null)app.users.add(data);
              await app.saveAll();
              if(c.mounted)Navigator.pop(c);
            },
            icon:const Icon(Icons.save),
            label:const Text('حفظ')
          )
        ]
      )
    )
  );
  name.dispose();
  username.dispose();
  password.dispose();
}

class SettingsPage'''
s = user_pat.sub(user_dialog, s, count=1)

p.write_text(s, encoding='utf-8')
print('Fixed legacy v6 generated Dart syntax')
