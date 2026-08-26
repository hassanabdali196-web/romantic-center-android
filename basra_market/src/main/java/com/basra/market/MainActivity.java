package com.basra.market;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.Window;

public class MainActivity extends Activity {
    private WebView webView;
    private ValueCallback<Uri[]> fileCallback;
    private static final int FILE_CHOOSER_REQUEST = 2001;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w=getWindow();w.setStatusBarColor(Color.WHITE);w.setNavigationBarColor(Color.WHITE);
        webView=new WebView(this);setContentView(webView);
        WebSettings s=webView.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setDatabaseEnabled(true);s.setAllowFileAccess(true);s.setAllowContentAccess(true);s.setLoadWithOverviewMode(true);s.setUseWideViewPort(true);
        webView.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r){Uri u=r.getUrl();String x=u.toString();if(x.startsWith("file:///android_asset/"))return false;if(x.startsWith("http://")||x.startsWith("https://")||x.startsWith("tel:")){try{startActivity(new Intent(Intent.ACTION_VIEW,u));return true;}catch(Exception e){return false;}}return false;}});
        webView.setWebChromeClient(new WebChromeClient(){@Override public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> cb,FileChooserParams p){if(fileCallback!=null)fileCallback.onReceiveValue(null);fileCallback=cb;try{startActivityForResult(p.createIntent(),FILE_CHOOSER_REQUEST);return true;}catch(Exception e){fileCallback=null;return false;}}});
        if(savedInstanceState==null)webView.loadUrl("file:///android_asset/index.html");else webView.restoreState(savedInstanceState);
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){if(requestCode==FILE_CHOOSER_REQUEST){if(fileCallback!=null){fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode,data));fileCallback=null;}return;}super.onActivityResult(requestCode,resultCode,data);}
    @Override protected void onSaveInstanceState(Bundle out){webView.saveState(out);super.onSaveInstanceState(out);}
    @Override public void onBackPressed(){if(webView!=null&&webView.canGoBack())webView.goBack();else super.onBackPressed();}
}
