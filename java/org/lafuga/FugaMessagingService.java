package org.lafuga;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

/**
 * Service qui reçoit les notifications push Firebase (FCM) et affiche une
 * notification Android locale. Il sert aussi à forcer l'inclusion des classes
 * Firebase dans l'APK (sinon elles seraient éliminées car non référencées).
 */
public class FugaMessagingService extends FirebaseMessagingService {

    private static final String CHANNEL_ID = "lafuga_default";

    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        String title = "La Fuga";
        String body = "";
        try {
            if (remoteMessage.getNotification() != null) {
                if (remoteMessage.getNotification().getTitle() != null) {
                    title = remoteMessage.getNotification().getTitle();
                }
                if (remoteMessage.getNotification().getBody() != null) {
                    body = remoteMessage.getNotification().getBody();
                }
            }
            if (remoteMessage.getData() != null) {
                if (remoteMessage.getData().containsKey("title")) {
                    title = remoteMessage.getData().get("title");
                }
                if (remoteMessage.getData().containsKey("body")) {
                    body = remoteMessage.getData().get("body");
                }
            }
        } catch (Exception e) {
            // valeurs par défaut
        }
        showNotification(title, body);
    }

    @Override
    public void onNewToken(String token) {
        super.onNewToken(token);
        // Le token peut changer ; l'appli le renverra au serveur à son prochain
        // démarrage (on lira le token courant côté Python).
    }

    private void showNotification(String title, String body) {
        try {
            NotificationManager nm =
                (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "La Fuga", NotificationManager.IMPORTANCE_HIGH);
                nm.createNotificationChannel(channel);
            }

            Intent intent = new Intent();
            intent.setClassName(getPackageName(),
                                "org.kivy.android.PythonActivity");
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP
                            | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= 23) {
                flags |= PendingIntent.FLAG_IMMUTABLE;
            }
            PendingIntent pi = PendingIntent.getActivity(this, 0, intent, flags);

            int iconRes = getApplicationInfo().icon;

            Notification.Builder nb;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                nb = new Notification.Builder(this, CHANNEL_ID);
            } else {
                nb = new Notification.Builder(this);
            }
            nb.setContentTitle(title)
              .setContentText(body)
              .setSmallIcon(iconRes)
              .setContentIntent(pi)
              .setAutoCancel(true);

            nm.notify((int) (System.currentTimeMillis() % 100000), nb.build());
        } catch (Exception e) {
            // ne jamais planter à cause d'une notification
        }
    }
}
