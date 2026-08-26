package com.romanticcenter.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.Window;

import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import java.util.concurrent.TimeUnit;

public class MainActivity extends Activity {
    private WebView webView;
    private WebView printWebView;
    private ValueCallback<Uri[]> fileCallback;
    private static final int FILE_CHOOSER_REQUEST = 1001;
    private static final int NOTIFICATION_PERMISSION_REQUEST = 1002;
    private static final String PREFS = "romantic_native";
    private static final String WORK_NAME = "romantic-background-notifications";
    private static final String CHANNEL = "romantic_updates";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window window = getWindow();
        window.setStatusBarColor(Color.WHITE);
        window.setNavigationBarColor(Color.WHITE);

        createNotificationChannel();
        requestNotificationPermission();

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);

        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        webView.addJavascriptInterface(new AppBridge(), "Android");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String url = uri.toString();
                if (url.startsWith("file:///android_asset/")) return false;
                if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("tel:")) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, uri));
                        return true;
                    } catch (Exception ignored) {
                        return false;
                    }
                }
                return false;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = filePathCallback;
                try {
                    Intent intent = fileChooserParams.createIntent();
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                    return true;
                } catch (Exception e) {
                    fileCallback = null;
                    return false;
                }
            }
        });

        if (savedInstanceState == null) webView.loadUrl("file:///android_asset/index.html");
        else webView.restoreState(savedInstanceState);

        String existing = getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("session", "");
        if (existing != null && !existing.isEmpty()) scheduleNotificationWork();
    }

    private class AppBridge {
        @JavascriptInterface
        public void printInvoice(final String html, final String jobName) {
            runOnUiThread(() -> {
                try {
                    printWebView = new WebView(MainActivity.this);
                    WebSettings ps = printWebView.getSettings();
                    ps.setJavaScriptEnabled(false);
                    ps.setDomStorageEnabled(false);
                    printWebView.setWebViewClient(new WebViewClient() {
                        private boolean printed = false;
                        @Override
                        public void onPageFinished(WebView view, String url) {
                            if (printed) return;
                            printed = true;
                            PrintManager printManager = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                            String safeJobName = (jobName == null || jobName.trim().isEmpty()) ? "Romantic-Center-Invoice" : jobName.trim();
                            PrintDocumentAdapter adapter = view.createPrintDocumentAdapter(safeJobName);
                            PrintAttributes attributes = new PrintAttributes.Builder()
                                    .setMediaSize(PrintAttributes.MediaSize.ISO_A4)
                                    .setMinMargins(PrintAttributes.Margins.NO_MARGINS)
                                    .build();
                            printManager.print(safeJobName, adapter, attributes);
                        }
                    });
                    printWebView.loadDataWithBaseURL("file:///android_asset/", html, "text/html", "UTF-8", null);
                } catch (Exception ignored) { }
            });
        }

        @JavascriptInterface
        public void storeSession(String json) {
            getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("session", json == null ? "" : json).apply();
            scheduleNotificationWork();
        }

        @JavascriptInterface
        public void clearSession() {
            getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply();
            WorkManager.getInstance(MainActivity.this).cancelUniqueWork(WORK_NAME);
        }

        @JavascriptInterface
        public void notifyNow(String title, String body) {
            showNotification(title == null ? "مركز رومانتك" : title, body == null ? "" : body);
        }
    }

    private void scheduleNotificationWork() {
        Constraints constraints = new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
        PeriodicWorkRequest periodic = new PeriodicWorkRequest.Builder(NotificationWorker.class, 15, TimeUnit.MINUTES)
                .setConstraints(constraints).build();
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, periodic);
        OneTimeWorkRequest immediate = new OneTimeWorkRequest.Builder(NotificationWorker.class).setConstraints(constraints).build();
        WorkManager.getInstance(this).enqueue(immediate);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            NotificationChannel ch = new NotificationChannel(CHANNEL, "إشعارات مركز رومانتك", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("الطلبات، الشحن، وحسابات الجملة");
            nm.createNotificationChannel(ch);
        }
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, NOTIFICATION_PERMISSION_REQUEST);
        }
    }

    private void showNotification(String title, String body) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(title).setContentText(body).setAutoCancel(true).setPriority(Notification.PRIORITY_HIGH);
        nm.notify((int) (System.currentTimeMillis() & 0x7fffffff), b.build());
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST) {
            if (fileCallback != null) {
                Uri[] result = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
                fileCallback.onReceiveValue(result);
                fileCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
