(function(){
  try{ if(window.PERM_LABELS) PERM_LABELS.update_orders='تحديث حالة الطلب + طباعة الفاتورة / PDF'; }catch(e){}

  window.invoiceHtml = function(o){
    const status=(STATUS[o.status]||STATUS.new)[0];
    const rows=(o.items||[]).map((i,idx)=>`<tr><td>${idx+1}</td><td><b>${esc(i.name)}</b><div class="sku">${esc(i.sku||'')}</div></td><td>${i.qty}</td><td>${money(i.unitPrice)}</td><td>${money(i.lineTotal)}</td></tr>`).join('');
    const pay=o.paymentMethod==='card'?'الدفع بالبطاقة':'الدفع عند الاستلام';
    const payStatus=o.paymentStatus==='paid'?'مدفوع':o.paymentStatus==='pending'?'بانتظار الدفع':'عند الاستلام';
    return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>فاتورة ${esc(o.orderNo)}</title><style>
      @page{size:A4;margin:12mm}*{box-sizing:border-box}body{font-family:Arial,"Noto Sans Arabic",sans-serif;color:#171820;margin:0;font-size:12px;direction:rtl}.head{display:flex;align-items:center;gap:14px;border-bottom:3px solid #d35d71;padding-bottom:12px;margin-bottom:14px}.mark{width:62px;height:62px;border-radius:17px;background:#171820;color:#f4c4cb;display:grid;place-items:center;font-size:23px;font-weight:900}.brand h1{margin:0;font-size:22px}.brand small{color:#777}.meta{margin-right:auto;text-align:left}.box{border:1px solid #e8e2de;border-radius:12px;padding:11px;margin:10px 0;page-break-inside:avoid}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 18px}.lab{color:#777;font-size:10px}.val{font-weight:700;margin-top:2px}.status{display:inline-block;padding:5px 10px;border-radius:999px;background:#f7e7ea;color:#9e3348;font-weight:800}table{width:100%;border-collapse:collapse;margin-top:12px}th,td{border-bottom:1px solid #e8e2de;padding:9px 7px;text-align:right}th{background:#faf7f5}.sku{font-size:9px;color:#777;margin-top:2px}.sum{width:310px;margin-right:auto;margin-top:12px}.sum div{display:flex;justify-content:space-between;padding:6px 0}.sum .total{border-top:2px solid #171820;font-size:16px;font-weight:900;margin-top:4px;padding-top:9px}.note{margin-top:16px;color:#666;border-top:1px dashed #bbb;padding-top:10px;line-height:1.7}.foot{text-align:center;color:#888;font-size:10px;margin-top:18px}.prep{margin-top:18px;border:1px dashed #999;border-radius:10px;padding:10px}.line{height:22px;border-bottom:1px solid #ddd;margin-bottom:7px}@media print{button{display:none!important}}
      </style></head><body><div class="head"><div class="mark">RC</div><div class="brand"><h1>مركز رومانتك</h1><small>Romantic Center — فاتورة وتجهيز طلب</small></div><div class="meta"><div><b>${esc(o.orderNo)}</b></div><div>${new Date(o.createdAt).toLocaleString('ar-IQ')}</div></div></div>
      <div class="box"><div class="grid"><div><div class="lab">العميل</div><div class="val">${esc(o.customerName)}</div></div><div><div class="lab">الهاتف</div><div class="val">${esc(o.phone)}</div></div><div><div class="lab">المدينة / المحافظة</div><div class="val">${esc(o.city||'-')}</div></div><div><div class="lab">حالة الطلب</div><div class="val"><span class="status">${esc(status)}</span></div></div><div><div class="lab">طريقة الدفع</div><div class="val">${esc(pay)}</div></div><div><div class="lab">حالة الدفع</div><div class="val">${esc(payStatus)}</div></div></div><div style="margin-top:9px"><div class="lab">العنوان</div><div class="val">${esc(o.address||'-')}</div></div>${o.note?`<div style="margin-top:9px"><div class="lab">ملاحظات العميل</div><div class="val">${esc(o.note)}</div></div>`:''}</div>
      <table><thead><tr><th>#</th><th>المنتج / SKU</th><th>الكمية</th><th>سعر الوحدة</th><th>الإجمالي</th></tr></thead><tbody>${rows}</tbody></table>
      <div class="sum"><div><span>مجموع المنتجات</span><b>${money(o.subtotal)}</b></div><div><span>التوصيل</span><b>${money(o.deliveryFee)}</b></div><div class="total"><span>الإجمالي</span><b>${money(o.total)}</b></div></div>
      <div class="prep"><b>قسم التجهيز</b><div class="line"></div><div class="grid"><div><span class="lab">اسم الموظف</span><div class="line"></div></div><div><span class="lab">تاريخ التجهيز</span><div class="line"></div></div><div><span class="lab">مراجعة الكميات</span> ☐ تم</div><div><span class="lab">مراجعة التغليف</span> ☐ تم</div></div></div>
      <div class="note">هذه الفاتورة مخصصة لتجهيز وشحن الطلب. يرجى مطابقة الأصناف والكميات قبل تغيير حالة الطلب إلى «تم التجهيز» ثم «تم الشحن».</div><div class="foot">مركز رومانتك — شكراً لتسوقكم معنا</div></body></html>`;
  };

  window.printInvoice = function(id){
    if(!has('update_orders')) return toast('لا تملك صلاحية طباعة الفواتير');
    const o=db.orders.find(x=>x.id===id); if(!o) return toast('الطلب غير موجود');
    const html=invoiceHtml(o), job=`Romantic-${o.orderNo}`;
    try{ if(window.Android && typeof Android.printInvoice==='function'){ Android.printInvoice(html,job); toast('اختر الطابعة أو حفظ كملف PDF'); return; } }catch(e){}
    const w=window.open('','_blank'); if(!w) return toast('تعذر فتح الطباعة');
    w.document.open(); w.document.write(html); w.document.close(); setTimeout(()=>{w.focus();w.print()},400);
  };

  const oldAdminOrderCard = window.adminOrderCard;
  window.adminOrderCard = function(o){
    let html = oldAdminOrderCard(o);
    if(has('update_orders')) html = html.replace('</div>', '</div>');
    const btn=`<button class="btn gold" onclick="printInvoice('${o.id}')">🖨 فاتورة / PDF</button>`;
    if(has('update_orders')) html=html.replace(/<\/div>$/, `<div class="actions" style="margin-top:10px">${btn}</div></div>`);
    return html;
  };

  const oldOpenOrderDetails = window.openOrderDetails;
  window.openOrderDetails = function(id){
    oldOpenOrderDetails(id);
    const o=db.orders.find(x=>x.id===id);
    if(o && has('update_orders')){
      modalBody.insertAdjacentHTML('beforeend',`<button class="btn gold" style="width:100%;margin-top:12px" onclick="printInvoice('${o.id}')">🖨 طباعة الفاتورة / حفظ PDF</button>`);
    }
  };
})();
