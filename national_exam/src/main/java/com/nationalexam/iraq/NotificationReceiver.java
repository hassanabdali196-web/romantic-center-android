package com.nationalexam.iraq;

import android.app.*;
import android.content.*;
import android.os.Build;

public class NotificationReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String title = intent.getStringExtra("title");
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        PendingIntent pi = PendingIntent.getActivity(context, 0, launch, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
            ? new Notification.Builder(context, "exam_reminders")
            : new Notification.Builder(context);
        b.setContentTitle("الاختبار الوطني")
         .setContentText(title == null ? "لديك موعد قريب" : title)
         .setSmallIcon(android.R.drawable.ic_dialog_info)
         .setAutoCancel(true)
         .setContentIntent(pi);
        ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE)).notify((int)(System.currentTimeMillis()%100000), b.build());
    }
}
