package com.nationalexam.iraq;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
import android.view.*;
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
    private boolean backRequestRunning = false;

    // Commercial release is ad-free until real production AdMob IDs are configured.
    private static final boolean ADS_ENABLED = false;
    private static final String BANNER_ID = "ca-app-pub-3940256099942544/6300978111";
    private static final String INTERSTITIAL_ID = "ca-app-pub-3940256099942544/1033173712";

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        createNotificationChannel();

        getWindow().setStatusBarColor(android.graphics.Color.rgb(11,45,91));
        getWindow().setNavigationBarColor(android.graphics.Color.WHITE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(android.graphics.Color.rgb(244,247,251));
        applySafeInsets(root);

        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(-1, 0, 1f));
        webView.setBackgroundColor(android.graphics.Color.rgb(244,247,251));
        webView.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS);
        webView.setVerticalScrollBarEnabled(true);
        webView.setScrollbarFadingEnabled(false);
        webView.setScrollBarStyle(View.SCROLLBARS_INSIDE_OVERLAY);
        webView.setNestedScrollingEnabled(true);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(true);
        ws.setTextZoom(100);
        ws.setLoadWithOverviewMode(false);
        ws.setUseWideViewPort(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                view.evaluateJavascript("document.documentElement.style.webkitTextSizeAdjust='100%';", null);
            }
        });
        webView.addJavascriptInterface(new Bridge(), "Android");
        root.addView(webView);

        banner = new AdView(this);
        banner.setAdSize(AdSize.BANNER);
        banner.setAdUnitId(BANNER_ID);
        banner.setLayoutParams(new LinearLayout.LayoutParams(-1, AdSize.BANNER.getHeightInPixels(this)));
        root.addView(banner);

        setContentView(root);

        if (ADS_ENABLED) {
            MobileAds.initialize(this, s -> {});
            banner.setVisibility(View.VISIBLE);
            banner.loadAd(new AdRequest.Builder().build());
            loadInterstitial();
        } else {
            banner.setVisibility(View.GONE);
        }

        webView.loadUrl("file:///android_asset/index.html");

        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                this::handleSystemBack
            );
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void applySafeInsets(View root) {
        final int extra = dp(4);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int left = 0, top = 0, right = 0, bottom = 0;
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
                left = bars.left; top = bars.top; right = bars.right; bottom = bars.bottom;
            } else {
                left = insets.getSystemWindowInsetLeft();
                top = insets.getSystemWindowInsetTop();
                right = insets.getSystemWindowInsetRight();
                bottom = insets.getSystemWindowInsetBottom();
            }
            v.setPadding(left + extra, top + extra, right + extra, bottom + extra);
            return insets;
        });
        root.requestApplyInsets();
    }

    private void loadInterstitial() {
        if (!ADS_ENABLED) return;
        InterstitialAd.load(this, INTERSTITIAL_ID, new AdRequest.Builder().build(),
            new InterstitialAdLoadCallback() {
                @Override public void onAdLoaded(@NonNull InterstitialAd ad) { interstitial = ad; }
                @Override public void onAdFailedToLoad(@NonNull LoadAdError error) { interstitial = null; }
            });
    }

    private void continueQuiz() {
        if (webView != null) webView.evaluateJavascript("window.afterAdStart && window.afterAdStart();", null);
    }

    public class Bridge {
        @JavascriptInterface public void showInterstitial() {
            runOnUiThread(() -> {
                if (!ADS_ENABLED) { continueQuiz(); return; }
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

            if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                runOnUiThread(() -> requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 7));
            }

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

    private void handleSystemBack() {
        if (backRequestRunning) return;
        if (webView == null) { finish(); return; }
        backRequestRunning = true;
        webView.evaluateJavascript("(window.handleNativeBack && window.handleNativeBack()) ? true : false;", result -> {
            backRequestRunning = false;
            if ("true".equals(result)) return;
            if (webView.canGoBack()) webView.goBack();
            else finish();
        });
    }

    @SuppressWarnings("deprecation")
    @Override public void onBackPressed() {
        handleSystemBack();
    }
}
