package com.mizancode.mizancode_customer_rebuild

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity: FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "mizancode.customer/preferences")
            .setMethodCallHandler { call, result ->
                val prefs = getSharedPreferences("customer", MODE_PRIVATE)
                when (call.method) {
                    "getBarcode" -> result.success(prefs.getString("barcode", ""))
                    "setBarcode" -> {
                        prefs.edit().putString("barcode", call.arguments as? String ?: "").apply()
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
