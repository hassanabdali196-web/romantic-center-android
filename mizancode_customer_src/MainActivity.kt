package com.mizancode.mizancode_customer_rebuild

import android.app.AlertDialog
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("customer", MODE_PRIVATE)
        if (!prefs.getBoolean("registered", false)) {
            window.decorView.post {
                if (!isFinishing) showRegistrationDialog()
            }
        }
    }

    private fun showRegistrationDialog() {
        val density = resources.displayMetrics.density
        val padding = (20 * density).toInt()
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, (8 * density).toInt(), padding, 0)
        }

        val nameInput = EditText(this).apply {
            hint = "الاسم الكامل"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        }

        val phoneInput = EditText(this).apply {
            hint = "رقم الهاتف - مثال: 07XXXXXXXXX"
            inputType = InputType.TYPE_CLASS_PHONE
            textDirection = View.TEXT_DIRECTION_LTR
        }

        val cardLabel = TextView(this).apply {
            text = "نوع البطاقة"
            textSize = 16f
            setPadding(0, (14 * density).toInt(), 0, (6 * density).toInt())
        }

        val cardTypes = listOf("عائلية", "أطفال", "طالب")
        val cardSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_dropdown_item,
                cardTypes
            )
        }

        container.addView(nameInput)
        container.addView(phoneInput)
        container.addView(cardLabel)
        container.addView(cardSpinner)

        val dialog = AlertDialog.Builder(this)
            .setTitle("تسجيل حساب الزبون")
            .setMessage("أدخل معلوماتك حتى يتم إنشاء حساب بطاقة الولاء.")
            .setView(container)
            .setCancelable(false)
            .setPositiveButton("إنشاء الحساب والدخول", null)
            .create()

        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val name = nameInput.text.toString().trim()
                val phone = phoneInput.text.toString().trim()
                val digitsCount = phone.count { it.isDigit() }

                var valid = true
                if (name.length < 2) {
                    nameInput.error = "أدخل الاسم الكامل"
                    valid = false
                }
                if (digitsCount < 10 || digitsCount > 15) {
                    phoneInput.error = "أدخل رقم هاتف صحيح"
                    valid = false
                }
                if (!valid) return@setOnClickListener

                val cleanPhone = phone.filter { it.isDigit() || it == '+' }
                val cardType = cardSpinner.selectedItem?.toString() ?: "عائلية"
                getSharedPreferences("customer", MODE_PRIVATE)
                    .edit()
                    .putString("customer_name", name)
                    .putString("customer_phone", cleanPhone)
                    .putString("card_type", cardType)
                    .putString("barcode", cleanPhone)
                    .putBoolean("registered", true)
                    .apply()

                dialog.dismiss()
                recreate()
            }
        }
        dialog.show()
    }

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
                    "getCustomerName" -> result.success(prefs.getString("customer_name", ""))
                    "getCustomerPhone" -> result.success(prefs.getString("customer_phone", ""))
                    "getCardType" -> result.success(prefs.getString("card_type", "عائلية"))
                    else -> result.notImplemented()
                }
            }
    }
}
