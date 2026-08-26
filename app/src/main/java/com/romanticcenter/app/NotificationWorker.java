package com.romanticcenter.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class NotificationWorker extends Worker {
    private static final String API_KEY = "AIzaSyCW_SgTQAjmvZtUm7NjP0aZ8AM-sjwo8Sw";
    private static final String PROJECT = "romantic-center";
    private static final String FS_BASE = "https://firestore.googleapis.com/v1/projects/" + PROJECT + "/databases/(default)/documents";
    private static final String PREFS = "romantic_native";
    private static final String CHANNEL = "romantic_updates";

    public NotificationWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        try {
            SharedPreferences prefs = getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            String raw = prefs.getString("session", "");
            if (raw == null || raw.isEmpty()) return Result.success();
            JSONObject s = new JSONObject(raw);
            String refreshToken = s.optString("refreshToken", "");
            String localId = s.optString("localId", "");
            String role = s.optString("role", "");
            JSONArray permissions = s.optJSONArray("permissions");
            if (refreshToken.isEmpty() || localId.isEmpty()) return Result.success();

            JSONObject token = refreshToken(refreshToken);
            String idToken = token.optString("id_token", "");
            if (idToken.isEmpty()) return Result.retry();

            boolean admin = "admin".equals(role);
            boolean viewOrders = admin || hasPermission(permissions, "view_orders");
            boolean manageUsers = admin || hasPermission(permissions, "manage_users");

            if (viewOrders) checkManagementOrders(idToken, prefs);
            else checkCustomerOrders(idToken, localId, prefs);
            if (manageUsers) checkPendingWholesale(idToken, prefs);
            checkPromotions(idToken, prefs);
            return Result.success();
        } catch (Exception e) {
            return Result.retry();
        }
    }

    private boolean hasPermission(JSONArray a, String p) {
        if (a == null) return false;
        for (int i = 0; i < a.length(); i++) if (p.equals(a.optString(i))) return true;
        return false;
    }

    private JSONObject refreshToken(String refreshToken) throws Exception {
        String body = "grant_type=refresh_token&refresh_token=" + URLEncoder.encode(refreshToken, "UTF-8");
        return requestJson("https://securetoken.googleapis.com/v1/token?key=" + API_KEY, "POST", null, body, "application/x-www-form-urlencoded");
    }

    private void checkManagementOrders(String token, SharedPreferences prefs) throws Exception {
        JSONObject j = requestJson(FS_BASE + "/orders?pageSize=300", "GET", token, null, null);
        JSONArray docs = j.optJSONArray("documents");
        Set<String> current = new HashSet<>();
        if (docs != null) {
            for (int i = 0; i < docs.length(); i++) {
                JSONObject d = docs.optJSONObject(i); if (d == null) continue;
                current.add(docId(d));
            }
        }
        Set<String> previous = new HashSet<>(prefs.getStringSet("seen_orders", new HashSet<>()));
        boolean initialized = prefs.getBoolean("orders_initialized", false);
        if (initialized && docs != null) {
            int shown = 0;
            for (int i = 0; i < docs.length() && shown < 4; i++) {
                JSONObject d = docs.optJSONObject(i); if (d == null) continue;
                String id = docId(d); if (previous.contains(id)) continue;
                String no = field(d, "orderNo");
                String customer = field(d, "customerName");
                notifyUser("طلب جديد", (no.isEmpty()?"طلب جديد":no) + (customer.isEmpty()?"":" — " + customer), id.hashCode(), "adminOrders", id);
                shown++;
            }
        }
        prefs.edit().putStringSet("seen_orders", current).putBoolean("orders_initialized", true).apply();
    }

    private void checkPendingWholesale(String token, SharedPreferences prefs) throws Exception {
        JSONObject j = requestJson(FS_BASE + "/users?pageSize=300", "GET", token, null, null);
        JSONArray docs = j.optJSONArray("documents");
        Set<String> current = new HashSet<>();
        if (docs != null) {
            for (int i = 0; i < docs.length(); i++) {
                JSONObject d = docs.optJSONObject(i); if (d == null) continue;
                if ("wholesale".equals(field(d,"role")) && "pending".equals(field(d,"status"))) current.add(docId(d));
            }
        }
        Set<String> previous = new HashSet<>(prefs.getStringSet("seen_pending_wholesale", new HashSet<>()));
        boolean initialized = prefs.getBoolean("wholesale_initialized", false);
        if (initialized && docs != null) {
            int shown=0;
            for (int i=0;i<docs.length()&&shown<4;i++){
                JSONObject d=docs.optJSONObject(i);if(d==null)continue;
                String id=docId(d);
                if(!current.contains(id)||previous.contains(id))continue;
                String name=field(d,"fullName"), username=field(d,"username");
                notifyUser("طلب حساب جملة", (name.isEmpty()?username:name) + " بانتظار موافقتك", ("w"+id).hashCode(), "adminUsers", id);
                shown++;
            }
        }
        prefs.edit().putStringSet("seen_pending_wholesale", current).putBoolean("wholesale_initialized", true).apply();
    }

    private void checkCustomerOrders(String token, String localId, SharedPreferences prefs) throws Exception {
        JSONObject where = new JSONObject()
                .put("fieldFilter", new JSONObject()
                        .put("field", new JSONObject().put("fieldPath", "userId"))
                        .put("op", "EQUAL")
                        .put("value", new JSONObject().put("stringValue", localId)));
        JSONObject q = new JSONObject()
                .put("structuredQuery", new JSONObject()
                        .put("from", new JSONArray().put(new JSONObject().put("collectionId", "orders")))
                        .put("where", where)
                        .put("limit", 300));
        JSONArray rows = requestArray(FS_BASE + ":runQuery", "POST", token, q.toString(), "application/json");
        Map<String,String> current = new HashMap<>();
        Map<String,String> orderNo = new HashMap<>();
        for(int i=0;i<rows.length();i++){
            JSONObject d=rows.optJSONObject(i);if(d==null)d=new JSONObject();
            d=d.optJSONObject("document");if(d==null)continue;
            String id=docId(d);current.put(id,field(d,"status"));orderNo.put(id,field(d,"orderNo"));
        }
        JSONObject previous = new JSONObject(prefs.getString("customer_statuses","{}"));
        boolean initialized=prefs.getBoolean("customer_initialized",false);
        if(initialized){
            for(Map.Entry<String,String> e:current.entrySet()){
                String old=previous.optString(e.getKey(),"");
                String now=e.getValue();
                if(!old.isEmpty()&&!old.equals(now)){
                    notifyUser("تحديث حالة الطلب", (orderNo.get(e.getKey())==null?"طلبك":orderNo.get(e.getKey())) + " — " + statusAr(now), ("s"+e.getKey()+now).hashCode(), "order", e.getKey());
                }
            }
        }
        JSONObject next=new JSONObject();for(Map.Entry<String,String> e:current.entrySet())next.put(e.getKey(),e.getValue());
        prefs.edit().putString("customer_statuses",next.toString()).putBoolean("customer_initialized",true).apply();
    }

    private void checkPromotions(String token, SharedPreferences prefs) throws Exception {
        JSONObject d = requestJson(FS_BASE + "/settings/store", "GET", token, null, null);
        JSONObject fields = d.optJSONObject("fields");
        Set<String> current = new HashSet<>();
        Map<String,String> titles = new HashMap<>();
        if (fields != null) {
            JSONObject p = fields.optJSONObject("promotions");
            JSONObject av = p == null ? null : p.optJSONObject("arrayValue");
            JSONArray values = av == null ? null : av.optJSONArray("values");
            if (values != null) {
                for (int i=0;i<values.length();i++) {
                    JSONObject v=values.optJSONObject(i); if(v==null)continue;
                    JSONObject mv=v.optJSONObject("mapValue"); if(mv==null)continue;
                    JSONObject pf=mv.optJSONObject("fields"); if(pf==null)continue;
                    String id=stringField(pf,"id");
                    String title=stringField(pf,"title");
                    boolean active=booleanField(pf,"active",true);
                    if(active && !id.isEmpty()){current.add(id);titles.put(id,title);}
                }
            }
        }
        Set<String> previous = new HashSet<>(prefs.getStringSet("seen_promotions", new HashSet<>()));
        boolean initialized = prefs.getBoolean("promotions_initialized", false);
        if(initialized){
            int shown=0;
            for(String id:current){
                if(previous.contains(id))continue;
                String title=titles.get(id);
                notifyUser("عرض جديد من مركز رومانتك", title==null||title.isEmpty()?"شاهد أحدث الخصومات والعروض":title, ("p"+id).hashCode(), "promotions", id);
                if(++shown>=3)break;
            }
        }
        prefs.edit().putStringSet("seen_promotions",current).putBoolean("promotions_initialized",true).apply();
    }

    private String stringField(JSONObject fields,String name){JSONObject v=fields.optJSONObject(name);return v==null?"":v.optString("stringValue","");}
    private boolean booleanField(JSONObject fields,String name,boolean fallback){JSONObject v=fields.optJSONObject(name);return v==null?fallback:v.optBoolean("booleanValue",fallback);}

    private String statusAr(String s){
        if("new".equals(s))return "طلب جديد";
        if("preparing".equals(s))return "قيد التجهيز";
        if("ready".equals(s))return "تم التجهيز";
        if("shipped".equals(s))return "تم الشحن";
        if("completed".equals(s))return "مكتمل";
        if("cancelled".equals(s))return "ملغي";
        return s;
    }

    private String docId(JSONObject d){String n=d.optString("name","");int x=n.lastIndexOf('/');return x>=0?n.substring(x+1):n;}
    private String field(JSONObject d,String name){
        JSONObject f=d.optJSONObject("fields");if(f==null)return "";JSONObject v=f.optJSONObject(name);if(v==null)return "";
        if(v.has("stringValue"))return v.optString("stringValue","");
        if(v.has("integerValue"))return v.optString("integerValue","");
        if(v.has("booleanValue"))return String.valueOf(v.optBoolean("booleanValue"));
        return "";
    }

    private JSONObject requestJson(String url,String method,String token,String body,String contentType)throws Exception{String text=request(url,method,token,body,contentType);return text.isEmpty()?new JSONObject():new JSONObject(text);}
    private JSONArray requestArray(String url,String method,String token,String body,String contentType)throws Exception{String text=request(url,method,token,body,contentType);return text.isEmpty()?new JSONArray():new JSONArray(text);}
    private String request(String url,String method,String token,String body,String contentType)throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();c.setConnectTimeout(12000);c.setReadTimeout(15000);c.setRequestMethod(method);c.setRequestProperty("Accept","application/json");
        if(token!=null&&!token.isEmpty())c.setRequestProperty("Authorization","Bearer "+token);
        if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type",contentType==null?"application/json":contentType);try(OutputStream os=c.getOutputStream()){os.write(body.getBytes(StandardCharsets.UTF_8));}}
        int code=c.getResponseCode();BufferedReader br=new BufferedReader(new InputStreamReader(code>=200&&code<300?c.getInputStream():c.getErrorStream(),StandardCharsets.UTF_8));StringBuilder sb=new StringBuilder();String line;while((line=br.readLine())!=null)sb.append(line);br.close();if(code<200||code>=300)throw new Exception("HTTP "+code+" "+sb);return sb.toString();
    }

    private void notifyUser(String title,String text,int id,String route,String itemId){
        Context ctx=getApplicationContext();
        NotificationManager nm=(NotificationManager)ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O){NotificationChannel ch=new NotificationChannel(CHANNEL,"إشعارات مركز رومانتك",NotificationManager.IMPORTANCE_HIGH);ch.setDescription("الطلبات، الشحن، الخصومات، وحسابات الجملة");nm.createNotificationChannel(ch);}

        Intent intent=new Intent(ctx,MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
        intent.putExtra("notification_route",route==null?"":route);
        intent.putExtra("notification_item_id",itemId==null?"":itemId);
        int requestCode=Math.abs((id+":"+route+":"+itemId).hashCode());
        PendingIntent pendingIntent=PendingIntent.getActivity(ctx,requestCode,intent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder b=Build.VERSION.SDK_INT>=Build.VERSION_CODES.O?new Notification.Builder(ctx,CHANNEL):new Notification.Builder(ctx);
        b.setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setContentIntent(pendingIntent)
                .setAutoCancel(true)
                .setPriority(Notification.PRIORITY_HIGH);
        nm.notify(Math.abs(id),b.build());
    }
}
