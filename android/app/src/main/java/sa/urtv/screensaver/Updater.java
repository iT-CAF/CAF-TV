package sa.urtv.screensaver;

import android.content.Context;
import android.content.SharedPreferences;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Pulls the latest page from GitHub so screen changes reach the TV without a new APK. */
final class Updater {
    static final String URL_PAGE =
        PhotoCache.REPO + "dist/tv.html";
    static final long INTERVAL_MS = 6L * 3600 * 1000;

    private static final String OFF = "التحديث التلقائي متوقف";
    private static final String RECENT = "تم الفحص مؤخراً";
    private static final String LATEST_URL = "https://github.com/iT-CAF/CAF-TV/releases/latest";
    private static final Pattern TAG = Pattern.compile("v(\\d+\\.\\d+)$");

    private Updater() {}

    static File pageFile(Context c) { return new File(c.getFilesDir(), "web/tv.html"); }

    /** Blocking; call off the main thread. Returns an Arabic status line for the settings screen. */
    static synchronized String check(Context c, boolean force) {
        String msg = checkPage(c, force);
        if (!OFF.equals(msg) && !RECENT.equals(msg)) checkLatest(c);
        return msg;
    }

    private static String checkPage(Context c, boolean force) {
        Prefs prefs = new Prefs(c);
        SharedPreferences sp = prefs.raw();
        if (!prefs.autoUpdate() && !force) return OFF;
        long now = System.currentTimeMillis();
        if (!force && now - sp.getLong("lastCheck", 0) < INTERVAL_MS) return RECENT;

        File out = pageFile(c);
        new File(out.getParentFile(), "caftv.html").delete();   // the old, heavier page
        HttpURLConnection con = null;
        try {
            con = (HttpURLConnection) new URL(URL_PAGE).openConnection();
            con.setConnectTimeout(15000);
            con.setReadTimeout(30000);
            String etag = sp.getString("etag", null);
            if (etag != null && out.isFile()) con.setRequestProperty("If-None-Match", etag);
            int code = con.getResponseCode();
            sp.edit().putLong("lastCheck", now).apply();
            if (code == HttpURLConnection.HTTP_NOT_MODIFIED) return "الصفحة محدثة";
            if (code != HttpURLConnection.HTTP_OK) return "تعذر التحديث (" + code + ")";

            byte[] body = readAll(con.getInputStream());
            String head = new String(body, 0, Math.min(body.length, 4096), "UTF-8");
            String tail = new String(body, Math.max(0, body.length - 4096), Math.min(body.length, 4096), "UTF-8");
            // never swap in a truncated or wrong file
            if (body.length < 30_000 || !head.contains("<html") || !tail.contains("</html>")) return "ملف التحديث غير صالح";

            File dir = out.getParentFile();
            if (!dir.isDirectory() && !dir.mkdirs()) return "تعذر الحفظ";
            File tmp = new File(dir, "page.tmp");
            FileOutputStream fo = new FileOutputStream(tmp);
            try { fo.write(body); } finally { fo.close(); }
            if (!tmp.renameTo(out)) return "تعذر الحفظ";
            sp.edit().putString("etag", con.getHeaderField("ETag")).apply();
            return "تم التحديث";
        } catch (Exception e) {
            return "لا يوجد اتصال";
        } finally {
            if (con != null) con.disconnect();
        }
    }

    /** Newest release tag, from the redirect of /releases/latest (no body read). Keeps the old value on any failure. */
    private static void checkLatest(Context c) {
        HttpURLConnection con = null;
        try {
            con = (HttpURLConnection) new URL(LATEST_URL).openConnection();
            con.setInstanceFollowRedirects(false);
            con.setConnectTimeout(10000);
            con.setReadTimeout(10000);
            con.getResponseCode();
            String loc = con.getHeaderField("Location");
            if (loc == null) return;
            Matcher m = TAG.matcher(loc.trim());
            if (!m.find()) return;
            new Prefs(c).raw().edit().putString("latestVersion", m.group(1))
                .putLong("latestCheck", System.currentTimeMillis()).apply();
        } catch (Exception e) {
            // keep the stored value
        } finally {
            if (con != null) con.disconnect();
        }
    }

    /** The minor number N of "3.N", or -1 when it does not parse. */
    private static int minor(String v) {
        try {
            return v == null ? -1 : Integer.parseInt(v.substring(v.indexOf('.') + 1));
        } catch (Exception e) {
            return -1;
        }
    }

    private static String arabic(String v) {
        StringBuilder b = new StringBuilder();
        for (char ch : v.toCharArray()) {
            if (ch >= '0' && ch <= '9') b.append((char) ('٠' + (ch - '0')));
            else if (ch == '.') b.append('٫');
            else b.append(ch);
        }
        return b.toString();
    }

    /** Arabic line for the settings row: this app's version and whether a newer release exists. */
    static String versionNote(Context c) {
        String mine = BuildConfig.VERSION_NAME;
        String latest = new Prefs(c).raw().getString("latestVersion", null);
        String head = "الإصدار " + arabic(mine);
        if (latest == null || minor(latest) < 0) return head + ".";
        if (minor(latest) <= minor(mine)) return head + "، وهو الأحدث.";
        return head + ". يوجد إصدار جديد " + arabic(latest)
            + ": اطلب من مساعدك «حدّث تلفزيوني»، وإعداداتك تبقى.";
    }

    private static byte[] readAll(InputStream in) throws java.io.IOException {
        try {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
            return b.toByteArray();
        } finally {
            in.close();
        }
    }
}
