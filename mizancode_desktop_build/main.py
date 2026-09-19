from __future__ import annotations
import json, math, sys, threading, uuid
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

from database import Database, new_id, now_iso
from cloud_api import CloudApi
from invoice import open_invoice

try:
    from PIL import Image, ImageTk
except Exception:
    Image=ImageTk=None

NAVY='#0F2747'; TEAL='#14B8A6'; BLUE='#3B82F6'; GREEN='#A7F3D0'; LIGHT='#F3F4F6'; WHITE='#FFFFFF'; RED='#C0392B'
FONT=('Tahoma',11); FONT_BOLD=('Tahoma',11,'bold'); FONT_TITLE=('Tahoma',17,'bold')

def resource_path(rel):
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    return root/rel

def money(v): return f"{float(v):,.0f} د.ع"
def fnum(v,default=0.0):
    try:return float(str(v).replace(',','').strip())
    except:return default

class MizanCodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db=Database(); self.api=CloudApi(self.db.setting('cloud_url'))
        self.title('MizanCode Desktop v6.1 Professional')
        self.geometry('1440x860'); self.minsize(1180,720); self.configure(bg=LIGHT)
        self.protocol('WM_DELETE_WINDOW',self.on_close)
        self.cart=[]; self.selected_customer=None; self.last_sale_id=None; self.redeemed_points=0; self.redeem_iqd=0
        self._setup_style(); self._set_icon(); self._build_shell(); self.show_pos(); self.after(900,self.sync_queue_async)

    def _setup_style(self):
        s=ttk.Style(self); s.theme_use('clam')
        s.configure('TFrame',background=LIGHT); s.configure('Card.TFrame',background=WHITE)
        s.configure('TLabel',background=LIGHT,foreground=NAVY,font=FONT)
        s.configure('Card.TLabel',background=WHITE,foreground=NAVY,font=FONT)
        s.configure('Title.TLabel',background=LIGHT,foreground=NAVY,font=FONT_TITLE)
        s.configure('Nav.TButton',font=FONT_BOLD,padding=(15,12),background=NAVY,foreground='white',borderwidth=0)
        s.map('Nav.TButton',background=[('active',BLUE)])
        s.configure('Primary.TButton',font=FONT_BOLD,padding=(14,11),background=NAVY,foreground='white',borderwidth=0)
        s.map('Primary.TButton',background=[('active',BLUE)])
        s.configure('Accent.TButton',font=FONT_BOLD,padding=(14,11),background=TEAL,foreground=NAVY,borderwidth=0)
        s.map('Accent.TButton',background=[('active',GREEN)])
        s.configure('Danger.TButton',font=FONT_BOLD,padding=(12,9),background=RED,foreground='white',borderwidth=0)
        s.configure('Treeview',font=FONT,rowheight=30,background=WHITE,fieldbackground=WHITE)
        s.configure('Treeview.Heading',font=FONT_BOLD,background=NAVY,foreground='white')
        s.configure('TEntry',font=FONT,padding=7); s.configure('TCombobox',font=FONT,padding=6)

    def _set_icon(self):
        try:
            p=resource_path('assets/icon.png')
            if Image and p.exists():
                im=Image.open(p); self._icon=ImageTk.PhotoImage(im.resize((64,64)))
                self.iconphoto(True,self._icon)
        except Exception: pass

    def _build_shell(self):
        top=tk.Frame(self,bg=NAVY,height=78); top.pack(fill='x'); top.pack_propagate(False)
        brand=tk.Frame(top,bg=NAVY); brand.pack(side='right',padx=22)
        try:
            if Image:
                im=Image.open(resource_path('assets/icon.png')).resize((58,58)); self.logo=ImageTk.PhotoImage(im); tk.Label(brand,image=self.logo,bg=NAVY).pack(side='right',padx=(10,0))
        except Exception: pass
        tk.Label(brand,text='ميزان كود  |  MizanCode',bg=NAVY,fg='white',font=('Tahoma',19,'bold')).pack(side='right')
        self.cloud_lbl=tk.Label(top,text='● جاهز',bg=NAVY,fg=GREEN,font=FONT_BOLD); self.cloud_lbl.pack(side='left',padx=24)
        body=tk.Frame(self,bg=LIGHT); body.pack(fill='both',expand=True)
        nav=tk.Frame(body,bg=NAVY,width=190); nav.pack(side='right',fill='y'); nav.pack_propagate(False)
        for txt,fn in [('الكاشير',self.show_pos),('المنتجات',self.show_products),('الزبائن',self.show_customers),('المزامنة',self.sync_now),('الإعدادات',self.show_settings)]:
            ttk.Button(nav,text=txt,style='Nav.TButton',command=fn).pack(fill='x',padx=8,pady=5)
        tk.Label(nav,text='v6.1 Professional',bg=NAVY,fg='#9fd7ff',font=('Tahoma',9)).pack(side='bottom',pady=20)
        self.content=tk.Frame(body,bg=LIGHT); self.content.pack(side='left',fill='both',expand=True,padx=18,pady=16)

    def clear_content(self):
        for w in self.content.winfo_children(): w.destroy()

    def card(self,parent,**pack):
        f=tk.Frame(parent,bg=WHITE,highlightbackground='#D9E4EE',highlightthickness=1); f.pack(**pack); return f

    def show_pos(self):
        self.clear_content()
        tk.Label(self.content,text='نقطة البيع',bg=LIGHT,fg=NAVY,font=FONT_TITLE).pack(anchor='e',pady=(0,10))
        upper=tk.Frame(self.content,bg=LIGHT); upper.pack(fill='both',expand=True)
        left=self.card(upper,side='left',fill='both',expand=True,padx=(0,10))
        right=self.card(upper,side='right',fill='y',padx=(10,0)); right.configure(width=420); right.pack_propagate(False)
        search=tk.Frame(left,bg=WHITE); search.pack(fill='x',padx=14,pady=12)
        tk.Label(search,text='بحث / باركود',bg=WHITE,fg=NAVY,font=FONT_BOLD).pack(side='right',padx=8)
        self.pos_search=ttk.Entry(search); self.pos_search.pack(side='right',fill='x',expand=True); self.pos_search.bind('<Return>',lambda e:self.add_by_search())
        ttk.Button(search,text='إضافة',style='Accent.TButton',command=self.add_by_search).pack(side='left')
        cols=('name','qty','price','total')
        self.cart_tree=ttk.Treeview(left,columns=cols,show='headings',selectmode='browse')
        for c,t,w in [('name','الصنف',300),('qty','الكمية',90),('price','السعر',120),('total','المجموع',140)]: self.cart_tree.heading(c,text=t); self.cart_tree.column(c,width=w,anchor='center')
        self.cart_tree.pack(fill='both',expand=True,padx=14,pady=5)
        actions=tk.Frame(left,bg=WHITE); actions.pack(fill='x',padx=14,pady=12)
        ttk.Button(actions,text='حذف الصنف',style='Danger.TButton',command=self.remove_cart).pack(side='left')
        ttk.Button(actions,text='+ كمية',command=lambda:self.adjust_qty(1)).pack(side='right',padx=4)
        ttk.Button(actions,text='- كمية',command=lambda:self.adjust_qty(-1)).pack(side='right',padx=4)
        self.customer_lbl=tk.Label(right,text='الزبون: زبون نقدي',bg=WHITE,fg=NAVY,font=FONT_BOLD,anchor='e'); self.customer_lbl.pack(fill='x',padx=16,pady=(18,5))
        cf=tk.Frame(right,bg=WHITE); cf.pack(fill='x',padx=14)
        self.customer_entry=ttk.Entry(cf); self.customer_entry.pack(side='right',fill='x',expand=True); self.customer_entry.bind('<Return>',lambda e:self.select_customer())
        ttk.Button(cf,text='اختيار',command=self.select_customer).pack(side='left',padx=5)
        self.summary=tk.Label(right,text='',bg=WHITE,fg=NAVY,font=('Tahoma',13),justify='right',anchor='e'); self.summary.pack(fill='x',padx=18,pady=12)
        disc=tk.Frame(right,bg=WHITE); disc.pack(fill='x',padx=14,pady=4); tk.Label(disc,text='خصم',bg=WHITE,font=FONT).pack(side='right'); self.discount=ttk.Entry(disc,width=14); self.discount.insert(0,'0'); self.discount.pack(side='left'); self.discount.bind('<KeyRelease>',lambda e:self.refresh_summary())
        red=tk.Frame(right,bg=WHITE); red.pack(fill='x',padx=14,pady=5)
        ttk.Button(red,text='استبدال النقاط',style='Accent.TButton',command=self.redeem_points).pack(fill='x')
        self.redeem_lbl=tk.Label(right,text='لم يتم استبدال نقاط',bg=WHITE,fg='#666',font=FONT); self.redeem_lbl.pack(fill='x',padx=14,pady=4)
        pay=tk.LabelFrame(right,text='الدفع',bg=WHITE,fg=NAVY,font=FONT_BOLD,padx=10,pady=10); pay.pack(fill='x',padx=14,pady=8)
        self.payment=tk.StringVar(value='نقدي'); self.pay_combo=ttk.Combobox(pay,textvariable=self.payment,values=['نقدي','بطاقة','مختلط','آجل'],state='readonly'); self.pay_combo.pack(fill='x'); self.pay_combo.bind('<<ComboboxSelected>>',lambda e:self.payment_changed())
        row=tk.Frame(pay,bg=WHITE); row.pack(fill='x',pady=6); tk.Label(row,text='النقد المستلم',bg=WHITE).pack(side='right'); self.cash_received=ttk.Entry(row,width=15); self.cash_received.insert(0,'0'); self.cash_received.pack(side='left')
        row2=tk.Frame(pay,bg=WHITE); row2.pack(fill='x',pady=6); tk.Label(row2,text='البطاقة',bg=WHITE).pack(side='right'); self.card_received=ttk.Entry(row2,width=15); self.card_received.insert(0,'0'); self.card_received.pack(side='left')
        ttk.Button(right,text='بيع سريع',style='Primary.TButton',command=lambda:self.checkout(False)).pack(fill='x',padx=14,pady=(14,6))
        self.invoice_btn=ttk.Button(right,text='إظهار الفاتورة',style='Accent.TButton',command=self.show_last_invoice,state='disabled'); self.invoice_btn.pack(fill='x',padx=14,pady=6)
        ttk.Button(right,text='تفريغ السلة',command=self.clear_cart).pack(fill='x',padx=14,pady=(6,15))
        self.refresh_cart()

    def add_by_search(self):
        q=self.pos_search.get().strip()
        if not q:return
        p=self.db.product_by_barcode(q)
        if not p:
            matches=self.db.products(q)
            if len(matches)==1:p=matches[0]
        if not p:
            messagebox.showinfo('المنتج','لم يتم العثور على المنتج. أضفه من صفحة المنتجات.'); return
        for it in self.cart:
            if it['product_id']==p['product_id']: it['qty']+=1; self.refresh_cart(); self.pos_search.delete(0,'end'); return
        self.cart.append({'product_id':p['product_id'],'barcode':p['barcode'] or '', 'name':p['name'],'qty':1.0,'price':float(p['sale_price'])})
        self.pos_search.delete(0,'end'); self.refresh_cart()

    def refresh_cart(self):
        if not hasattr(self,'cart_tree'):return
        for i in self.cart_tree.get_children():self.cart_tree.delete(i)
        for idx,it in enumerate(self.cart): self.cart_tree.insert('', 'end', iid=str(idx), values=(it['name'],f"{it['qty']:g}",money(it['price']),money(it['qty']*it['price'])))
        self.refresh_summary()

    def selected_cart_idx(self):
        s=self.cart_tree.selection(); return int(s[0]) if s else None
    def remove_cart(self):
        i=self.selected_cart_idx()
        if i is not None:self.cart.pop(i);self.refresh_cart()
    def adjust_qty(self,d):
        i=self.selected_cart_idx()
        if i is None:return
        self.cart[i]['qty']=max(1,self.cart[i]['qty']+d);self.refresh_cart()
    def clear_cart(self):
        self.cart.clear(); self.selected_customer=None; self.redeemed_points=0; self.redeem_iqd=0
        if hasattr(self,'customer_lbl'):self.customer_lbl.config(text='الزبون: زبون نقدي');self.redeem_lbl.config(text='لم يتم استبدال نقاط')
        self.refresh_cart()

    def select_customer(self):
        q=self.customer_entry.get().strip()
        if not q:return
        c=self.db.customer_by_barcode(q)
        if not c:
            m=self.db.customers(q)
            if len(m)==1:c=m[0]
        if not c: messagebox.showwarning('الزبون','لم يتم العثور على الزبون.');return
        self.selected_customer=c; self.customer_lbl.config(text=f"الزبون: {c['name']} | {c['card_type']} | {c['points']:g} نقطة"); self.refresh_summary()

    def totals(self):
        subtotal=sum(i['qty']*i['price'] for i in self.cart); discount=max(0,fnum(self.discount.get() if hasattr(self,'discount') else 0)); total=max(0,subtotal-discount-self.redeem_iqd)
        return subtotal,discount,total
    def refresh_summary(self):
        if not hasattr(self,'summary'):return
        subtotal,discount,total=self.totals(); self.summary.config(text=f"المجموع: {money(subtotal)}\nالخصم: {money(discount)}\nخصم النقاط: {money(self.redeem_iqd)}\n\nالإجمالي: {money(total)}")
    def redeem_points(self):
        if not self.selected_customer:messagebox.showwarning('النقاط','اختر زبوناً أولاً.');return
        pts=float(self.selected_customer['points']); block=fnum(self.db.setting('POINTS_REDEEM_BLOCK','5'),5); val=fnum(self.db.setting('POINTS_REDEEM_IQD','3000'),3000)
        usable=math.floor(pts/block)*block if block else 0
        if usable<block: messagebox.showinfo('النقاط','رصيد النقاط غير كافٍ للاستبدال.');return
        subtotal,discount,_=self.totals(); max_iqd=max(0,subtotal-discount); blocks=min(math.floor(usable/block), math.floor(max_iqd/val) if val else 0)
        if blocks<=0:messagebox.showinfo('النقاط','قيمة الفاتورة لا تسمح بخصم نقاط الآن.');return
        self.redeemed_points=blocks*block; self.redeem_iqd=blocks*val; self.redeem_lbl.config(text=f"تم استبدال {self.redeemed_points:g} نقطة = {money(self.redeem_iqd)}"); self.refresh_summary()

    def payment_changed(self):
        method=self.payment.get()
        if method=='نقدي': self.card_received.delete(0,'end');self.card_received.insert(0,'0')
        elif method=='بطاقة': self.cash_received.delete(0,'end');self.cash_received.insert(0,'0')

    def checkout(self, show_invoice=False):
        if not self.cart:messagebox.showwarning('البيع','السلة فارغة.');return
        subtotal,discount,total=self.totals(); method=self.payment.get(); cash=fnum(self.cash_received.get()); card=fnum(self.card_received.get()); debt=0
        if method=='نقدي':
            if cash<=0:cash=total
            if cash<total:messagebox.showwarning('الدفع','المبلغ النقدي المستلم أقل من الإجمالي.');return
        elif method=='بطاقة':
            if card<=0:card=total
            if card<total:messagebox.showwarning('الدفع','مبلغ البطاقة أقل من الإجمالي.');return
        elif method=='مختلط':
            if cash+card<total:messagebox.showwarning('الدفع المختلط','مجموع النقد والبطاقة أقل من الإجمالي.');return
        elif method=='آجل':
            debt=total; cash=card=0
            if not self.selected_customer:messagebox.showwarning('الآجل','البيع الآجل يحتاج اختيار زبون.');return
        spend=fnum(self.db.setting('POINTS_SPEND_IQD','200000'),200000); earn=fnum(self.db.setting('POINTS_EARN','5'),5); earned=math.floor(total/spend)*earn if spend else 0
        stamp=datetime.now().strftime('%Y%m%d%H%M%S'); sale_id=new_id('SALE'); invoice=f"INV-{stamp}-{uuid.uuid4().hex[:4].upper()}"
        sale={'sale_id':sale_id,'invoice_no':invoice,'customer_id':self.selected_customer['customer_id'] if self.selected_customer else None,'customer_name':self.selected_customer['name'] if self.selected_customer else 'زبون نقدي','subtotal':subtotal,'discount':discount,'points_redeemed':self.redeemed_points,'redeem_iqd':self.redeem_iqd,'total':total,'payment_method':method,'paid_cash':cash,'paid_card':card,'debt_added':debt,'earned_points':earned,'created_at':now_iso(),'sync_id':uuid.uuid4().hex}
        self.db.record_sale(sale,self.cart)
        payload={**sale,'customer_barcode':self.selected_customer['barcode'] if self.selected_customer else '', 'items':self.cart}
        self.db.queue('record_sale',payload)
        self.last_sale_id=sale_id; self.invoice_btn.config(state='normal')
        change=max(0,cash+card-total)
        messagebox.showinfo('تم البيع',f"تم حفظ البيع بنجاح\n{invoice}\nالباقي: {money(change)}\nالنقاط المكتسبة: {earned:g}")
        if show_invoice:self.show_last_invoice()
        self.cart=[]; self.redeemed_points=0; self.redeem_iqd=0; self.selected_customer=None; self.refresh_cart(); self.customer_lbl.config(text='الزبون: زبون نقدي'); self.redeem_lbl.config(text='لم يتم استبدال نقاط'); self.sync_queue_async()

    def show_last_invoice(self):
        if not self.last_sale_id:return
        s,items=self.db.sale(self.last_sale_id)
        if s:open_invoice(s,items,self.db.setting('business_name','MizanCode'))

    def show_products(self):
        self.clear_content(); tk.Label(self.content,text='المنتجات',bg=LIGHT,fg=NAVY,font=FONT_TITLE).pack(anchor='e',pady=(0,10))
        top=tk.Frame(self.content,bg=LIGHT); top.pack(fill='x'); self.prod_search=ttk.Entry(top);self.prod_search.pack(side='right',fill='x',expand=True,padx=5);self.prod_search.bind('<KeyRelease>',lambda e:self.load_products())
        ttk.Button(top,text='إضافة منتج',style='Accent.TButton',command=lambda:self.product_dialog()).pack(side='left')
        cols=('barcode','name','category','price','stock');self.prod_tree=ttk.Treeview(self.content,columns=cols,show='headings')
        for c,t,w in [('barcode','الباركود',180),('name','الاسم',300),('category','الفئة',180),('price','سعر البيع',150),('stock','المخزون',120)]:self.prod_tree.heading(c,text=t);self.prod_tree.column(c,width=w,anchor='center')
        self.prod_tree.pack(fill='both',expand=True,pady=10);self.prod_tree.bind('<Double-1>',lambda e:self.edit_selected_product());self.load_products()
    def load_products(self):
        q=self.prod_search.get() if hasattr(self,'prod_search') else ''
        for x in self.prod_tree.get_children():self.prod_tree.delete(x)
        for p in self.db.products(q):self.prod_tree.insert('', 'end',iid=p['product_id'],values=(p['barcode'] or '',p['name'],p['category'],money(p['sale_price']),f"{p['stock_qty']:g}"))
    def edit_selected_product(self):
        s=self.prod_tree.selection()
        if not s:return
        row=self.db.conn.execute('SELECT * FROM products WHERE product_id=?',(s[0],)).fetchone();self.product_dialog(row)
    def product_dialog(self,row=None):
        d=tk.Toplevel(self);d.title('المنتج');d.geometry('450x430');d.configure(bg=WHITE);d.transient(self);d.grab_set();fields={}
        specs=[('الباركود','barcode'),('الاسم','name'),('الفئة','category'),('سعر البيع','sale_price'),('سعر الكلفة','cost_price'),('المخزون','stock_qty'),('حد التنبيه','min_stock')]
        for i,(lab,key) in enumerate(specs):tk.Label(d,text=lab,bg=WHITE,font=FONT).grid(row=i,column=1,padx=12,pady=8,sticky='e');e=ttk.Entry(d);e.grid(row=i,column=0,padx=12,pady=8,sticky='ew');e.insert(0,str(row[key] if row else ''));fields[key]=e
        d.grid_columnconfigure(0,weight=1)
        def save():
            if not fields['name'].get().strip():messagebox.showwarning('المنتج','اكتب اسم المنتج.',parent=d);return
            data={k:v.get() for k,v in fields.items()};data['product_id']=row['product_id'] if row else None
            self.db.upsert_product(data);d.destroy();self.load_products()
        ttk.Button(d,text='حفظ',style='Primary.TButton',command=save).grid(row=len(specs),column=0,columnspan=2,pady=18)

    def show_customers(self):
        self.clear_content();tk.Label(self.content,text='الزبائن وبطاقات الولاء',bg=LIGHT,fg=NAVY,font=FONT_TITLE).pack(anchor='e',pady=(0,10))
        top=tk.Frame(self.content,bg=LIGHT);top.pack(fill='x');self.cust_search=ttk.Entry(top);self.cust_search.pack(side='right',fill='x',expand=True,padx=5);self.cust_search.bind('<KeyRelease>',lambda e:self.load_customers());ttk.Button(top,text='إضافة زبون',style='Accent.TButton',command=lambda:self.customer_dialog()).pack(side='left')
        cols=('barcode','name','phone','type','points','spent');self.cust_tree=ttk.Treeview(self.content,columns=cols,show='headings')
        for c,t,w in [('barcode','الباركود',190),('name','الاسم',240),('phone','الهاتف',150),('type','نوع البطاقة',120),('points','النقاط',90),('spent','إجمالي المشتريات',170)]:self.cust_tree.heading(c,text=t);self.cust_tree.column(c,width=w,anchor='center')
        self.cust_tree.pack(fill='both',expand=True,pady=10);self.cust_tree.bind('<Double-1>',lambda e:self.edit_selected_customer());self.load_customers()
    def load_customers(self):
        q=self.cust_search.get() if hasattr(self,'cust_search') else ''
        for x in self.cust_tree.get_children():self.cust_tree.delete(x)
        for c in self.db.customers(q):self.cust_tree.insert('', 'end',iid=c['customer_id'],values=(c['barcode'],c['name'],c['phone'],c['card_type'],f"{c['points']:g}",money(c['total_spent_iqd'])))
    def edit_selected_customer(self):
        s=self.cust_tree.selection()
        if s:self.customer_dialog(self.db.customer_by_id(s[0]))
    def customer_dialog(self,row=None):
        d=tk.Toplevel(self);d.title('بيانات الزبون');d.geometry('470x360');d.configure(bg=WHITE);d.transient(self);d.grab_set();fields={}
        specs=[('الاسم','name'),('رقم الهاتف','phone'),('الباركود','barcode')]
        for i,(lab,key) in enumerate(specs):tk.Label(d,text=lab,bg=WHITE,font=FONT).grid(row=i,column=1,padx=12,pady=10,sticky='e');e=ttk.Entry(d);e.grid(row=i,column=0,padx=12,pady=10,sticky='ew');e.insert(0,str(row[key] if row else ''));fields[key]=e
        tk.Label(d,text='نوع البطاقة',bg=WHITE,font=FONT).grid(row=3,column=1,padx=12,pady=10,sticky='e');ctype=tk.StringVar(value=row['card_type'] if row else 'عائلية');cb=ttk.Combobox(d,textvariable=ctype,values=['عائلية','أطفال','طالب'],state='readonly');cb.grid(row=3,column=0,padx=12,pady=10,sticky='ew');d.grid_columnconfigure(0,weight=1)
        def save():
            if not fields['name'].get().strip():messagebox.showwarning('الزبون','اكتب اسم الزبون.',parent=d);return
            data={k:v.get() for k,v in fields.items()};data['card_type']=ctype.get();data['customer_id']=row['customer_id'] if row else None
            cid,barcode=self.db.upsert_customer(data);payload={'customer_id':cid,'barcode':barcode,'name':data['name'],'phone':data['phone'],'card_type':data['card_type']};self.db.queue('update_customer' if row else 'create_customer',payload);d.destroy();self.load_customers();self.sync_queue_async()
        ttk.Button(d,text='حفظ',style='Primary.TButton',command=save).grid(row=5,column=0,columnspan=2,pady=18)

    def show_settings(self):
        self.clear_content();tk.Label(self.content,text='الإعدادات',bg=LIGHT,fg=NAVY,font=FONT_TITLE).pack(anchor='e',pady=(0,15));f=self.card(self.content,fill='x');vars={}
        specs=[('اسم المتجر','business_name'),('رابط السحابة','cloud_url'),('مبلغ اكتساب النقاط','POINTS_SPEND_IQD'),('النقاط المكتسبة','POINTS_EARN'),('حزمة الاستبدال','POINTS_REDEEM_BLOCK'),('قيمة الحزمة د.ع','POINTS_REDEEM_IQD')]
        for i,(lab,key) in enumerate(specs):tk.Label(f,text=lab,bg=WHITE,font=FONT).grid(row=i,column=1,padx=15,pady=10,sticky='e');e=ttk.Entry(f,width=70);e.grid(row=i,column=0,padx=15,pady=10,sticky='ew');e.insert(0,self.db.setting(key));vars[key]=e
        f.grid_columnconfigure(0,weight=1)
        def save():
            for k,e in vars.items():self.db.set_setting(k,e.get().strip())
            self.api=CloudApi(self.db.setting('cloud_url'));messagebox.showinfo('الإعدادات','تم الحفظ.')
        ttk.Button(f,text='حفظ الإعدادات',style='Primary.TButton',command=save).grid(row=len(specs),column=0,columnspan=2,pady=18)

    def sync_now(self):
        self.cloud_lbl.config(text='● جاري المزامنة...',fg='#FFD166');self.sync_queue_async(show_result=True)
    def sync_queue_async(self,show_result=False):
        def worker():
            ok=0;fail=0
            for row in self.db.pending_sync():
                try:
                    payload=json.loads(row['payload']);self.api.post(row['action'],payload);self.db.mark_sync_success(row['id']);ok+=1
                except Exception as e:self.db.mark_sync_failure(row['id'],str(e));fail+=1
            def done():
                self.cloud_lbl.config(text=('● متصل' if fail==0 else f'● معلّق {fail}'),fg=(GREEN if fail==0 else '#FFD166'))
                if show_result:messagebox.showinfo('المزامنة',f'تم رفع {ok} عملية. المتبقي {fail}.')
            self.after(0,done)
        threading.Thread(target=worker,daemon=True).start()

    def on_close(self):
        try:self.db.close()
        finally:self.destroy()

if __name__=='__main__':
    MizanCodeApp().mainloop()
