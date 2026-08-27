package com.nationalexam.iraq;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
import android.webkit.*;
import android.widget.*;
import androidx.annotation.NonNull;
import com.google.android.gms.ads.*;
import com.google.android.gms.ads.interstitial.InterstitialAd;
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback;

public class MainActivity extends Activity {
    private WebView webView;
    private AdView banner;
    private InterstitialAd interstitial;
    private static final String BANNER_ID = "ca-app-pub-3940256099942544/6300978111";
    private static final String INTERSTITIAL_ID = "ca-app-pub-3940256099942544/1033173712";

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 7);
        }
        createNotificationChannel();
        MobileAds.initialize(this, s -> {});
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(-1,0,1f));
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(true);
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new Bridge(), "Android");
        root.addView(webView);
        banner = new AdView(this);
        banner.setAdSize(AdSize.BANNER);
        banner.setAdUnitId(BANNER_ID);
        banner.setLayoutParams(new LinearLayout.LayoutParams(-1, AdSize.BANNER.getHeightInPixels(this)));
        root.addView(banner);
        setContentView(root);
        banner.loadAd(new AdRequest.Builder().build());
        loadInterstitial();
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void loadInterstitial() {
        InterstitialAd.load(this, INTERSTITIAL_ID, new AdRequest.Builder().build(),
            new InterstitialAdLoadCallback() {
                @Override public void onAdLoaded(@NonNull InterstitialAd ad) { interstitial = ad; }
                @Override public void onAdFailedToLoad(@NonNull LoadAdError error) { interstitial = null; }
            });
    }

    private void continueQuiz() {
        webView.evaluateJavascript("window.afterAdStart && window.afterAdStart();", null);
    }

    public class Bridge {
        @JavascriptInterface public void showInterstitial() {
            runOnUiThread(() -> {
                if (interstitial == null) { continueQuiz(); loadInterstitial(); return; }
                interstitial.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override public void onAdDismissedFullScreenContent() { interstitial = null; continueQuiz(); loadInterstitial(); }
                    @Override public void onAdFailedToShowFullScreenContent(@NonNull AdError e) { interstitial = null; continueQuiz(); loadInterstitial(); }
                });
                interstitial.show(MainActivity.this);
            });
        }

        @JavascriptInterface public void openUrl(String url) {
            runOnUiThread(() -> {
                try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
                catch(Exception e) { Toast.makeText(MainActivity.this,"تعذر فتح الرابط",Toast.LENGTH_SHORT).show(); }
            });
        }

        @JavascriptInterface public void scheduleReminder(String title, long whenMs) {
            if (whenMs <= System.currentTimeMillis()) return;
            Intent intent = new Intent(MainActivity.this, NotificationReceiver.class);
            intent.putExtra("title", title);
            int id = (int)(whenMs % Integer.MAX_VALUE);
            PendingIntent pi = PendingIntent.getBroadcast(MainActivity.this, id, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            AlarmManager am = (AlarmManager)getSystemService(ALARM_SERVICE);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, whenMs, pi);
            else am.set(AlarmManager.RTC_WAKEUP, whenMs, pi);
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel("exam_reminders","تذكيرات الامتحان",NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("تذكير بموعد الحجز أو الامتحان الوطني");
            getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }
}
