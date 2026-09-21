from pathlib import Path
import sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'buildcustomer/lib/main.dart')
s=p.read_text(encoding='utf-8')

# Loyalty constants must match the cashier/backend rules.
anchor="const apiUrl = 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec';"
if anchor in s and 'const loyaltySpendBlock' not in s:
    s=s.replace(anchor,anchor+"\nconst loyaltySpendBlock = 200000;\nconst loyaltyEarnPoints = 5;\nconst loyaltyRedeemBlock = 5;\nconst loyaltyRedeemIqd = 3000;",1)

# Ensure the automatic refresh cadence is responsive while the app is open.
s=s.replace("Timer.periodic(const Duration(seconds: 5)","Timer.periodic(const Duration(seconds: 3)")
s=s.replace("Timer.periodic(const Duration(seconds: 4)","Timer.periodic(const Duration(seconds: 3)")

# Use the exact same points-value rule as the cashier when the API does not return a value.
old="profile['points_value_iqd'] = newValue>0 ? newValue : (newPoints ~/ 5) * 3000;"
new="profile['points_value_iqd'] = newValue>0 ? newValue : (newPoints ~/ loyaltyRedeemBlock) * loyaltyRedeemIqd;"
if old in s:s=s.replace(old,new,1)

# Add rule details and amount remaining to the next earning block to the synced profile.
old="""        profile['total_spent_iqd'] = newSpent;\n        if(c['last_redeem_at']!=null)profile['last_redeem_at']=c['last_redeem_at'];"""
new="""        profile['total_spent_iqd'] = newSpent;\n        profile['loyalty_spend_block_iqd'] = loyaltySpendBlock;\n        profile['loyalty_earn_points'] = loyaltyEarnPoints;\n        profile['loyalty_redeem_block'] = loyaltyRedeemBlock;\n        profile['loyalty_redeem_iqd'] = loyaltyRedeemIqd;\n        final rem = newSpent.round() % loyaltySpendBlock;\n        profile['next_points_after_iqd'] = rem == 0 ? loyaltySpendBlock : loyaltySpendBlock - rem;\n        if(c['last_redeem_at']!=null)profile['last_redeem_at']=c['last_redeem_at'];"""
if old in s:s=s.replace(old,new,1)

# Make the sync message explicitly tied to the cashier sale, with no QR requirement.
s=s.replace("'النقاط والمشتريات تتحدث تلقائياً من النظام، ولا تحتاج لمسح الفاتورة.'","'أي بيع مسجل من الكاشير يصل إلى بطاقتك تلقائياً: النقاط، قيمة النقاط، وإجمالي المشتريات — بدون مسح باركود الفاتورة.'")
s=s.replace("'النقاط وإجمالي المشتريات تتحدث تلقائياً من سطح المكتب بدون مسح الفاتورة. آخر تحديث: ${profile['last_sync_display'] ?? 'الآن'}'","'أي بيع من الكاشير يحدث النقاط والمشتريات تلقائياً بدون مسح باركود. آخر تحديث: ${profile['last_sync_display'] ?? 'الآن'}'")

# Change the QR control to a clearly optional emergency fallback only.
s=s.replace("label: const Text('مسح فاتورة احتياطي')","label: const Text('مسح احتياطي فقط')")
s=s.replace("label: const Text('مسح فاتورة — خيار احتياطي')","label: const Text('مسح احتياطي فقط')")

# Add a visible rule card before last sync if the expected UI anchor exists.
anchor_ui="""              const SizedBox(height: 16),\n              if (profile['last_redeem_at'] != null)"""
rule_ui="""              const SizedBox(height: 16),\n              Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFE0EAF4))), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [\n                const Text('قواعد الولاء', style: TextStyle(fontWeight: FontWeight.w900, color: navy)),\n                const SizedBox(height: 6),\n                const Text('كل 200,000 د.ع مشتريات = 5 نقاط، وكل 5 نقاط = خصم 3,000 د.ع.', style: TextStyle(color: Colors.black54, height: 1.5)),\n                const SizedBox(height: 5),\n                Text('المتبقي للحصول على الدفعة التالية من النقاط: ${fmt(toInt(profile['next_points_after_iqd'] ?? loyaltySpendBlock))} د.ع', style: const TextStyle(fontWeight: FontWeight.w800, color: navy)),\n              ])),\n              const SizedBox(height: 12),\n              if (profile['last_redeem_at'] != null)"""
if anchor_ui in s:s=s.replace(anchor_ui,rule_ui,1)

# Update the explanatory footer if present.
s=s.replace('كل 3 ثوانٍ أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.','كل 3 ثوانٍ أثناء فتح التطبيق، وفور فتحه أو الرجوع إليه. لا تحتاج لمسح باركود لإضافة النقاط.')

p.write_text(s,encoding='utf-8')
print('MizanCode Customer v1.3.3 Cashier Sync patch applied')
