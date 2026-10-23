package sa.urtv.screensaver;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Settings;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * The screensaver's settings from ADB, for agents (people use SettingsActivity). Only the shell can send
 * these: the manifest requires android.permission.DUMP. optimize/saver.sh wraps them.
 *
 *   am broadcast -n sa.urtv.screensaver/.SaverReceiver -a sa.urtv.screensaver.GET
 *   am broadcast -n sa.urtv.screensaver/.SaverReceiver -a sa.urtv.screensaver.CITIES
 *   am broadcast -n sa.urtv.screensaver/.SaverReceiver -a sa.urtv.screensaver.SET
 *       [--es city 'الرس'] [--es lat 25.86 --es lon 43.49] [--es teams '136013:Al-Hilal,150643:Al-Zulfi']
 *       [--es panel prayers] [--es home_panel none] [--es minrating 7] [--es genres Drama,Comedy] [--es langs English]
 *       [--es photos 30] [--es idle 10]
 *   am broadcast -n sa.urtv.screensaver/.SaverReceiver -a sa.urtv.screensaver.UPDATE
 *
 * photos = minutes between background photos (Prefs.PHOTO_MINUTES). idle = minutes before the TV starts the
 * screensaver (Prefs.IDLE_MINUTES): this is the system's screen_off_timeout, which a receiver (it runs as this
 * app, not as the shell) may write only when the app holds WRITE_SETTINGS; otherwise it says so and
 * optimize/saver.sh sets it from the shell instead. Nothing changes unless the extra is given.
 *
 * The answer is in the "data" of am's output. Unknown values are refused with a message, nothing half-saved.
 */
public class SaverReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent i) {
        Prefs p = new Prefs(c);
        String action = String.valueOf(i.getAction());
        switch (action) {
            case "sa.urtv.screensaver.GET":
                setResultData(describe(c, p));
                return;
            case "sa.urtv.screensaver.CITIES": {
                StringBuilder b = new StringBuilder();
                for (Cities.Region r : Cities.REGIONS) {
                    b.append(r.name).append(": ");
                    for (String[] city : r.cities) b.append(city[0]).append("، ");
                    b.setLength(b.length() - 2);
                    b.append('\n');
                }
                setResultData(b.toString().trim());
                return;
            }
            case "sa.urtv.screensaver.UPDATE": {
                final PendingResult pending = goAsync();   // a download: off the main thread
                final Context app = c.getApplicationContext();
                new Thread(() -> {
                    pending.setResultData("update: " + Updater.check(app, true));
                    pending.finish();
                }).start();
                return;
            }
            case "sa.urtv.screensaver.SET":
                setResultData(set(c, p, i));
                return;
            default:
                setResultData("error: unknown action " + action);
        }
    }

    private static String set(Context c, Prefs p, Intent i) {
        // check everything first, then save: a typo never leaves half the settings changed
        String[] city = null;
        String name = i.getStringExtra("city"), lat = i.getStringExtra("lat"), lon = i.getStringExtra("lon");
        if (name != null) {
            if (lat != null && lon != null) {
                if (!lat.matches("-?\\d{1,2}(\\.\\d+)?") || !lon.matches("-?\\d{1,3}(\\.\\d+)?"))
                    return "error: lat/lon must be numbers like 25.86 / 43.49";
                city = new String[] {name, lat, lon};
            } else {
                for (Cities.Region r : Cities.REGIONS) for (String[] x : r.cities) if (x[0].equals(name)) city = x;
                if (city == null) return "error: city not in the built-in list; give --es lat and --es lon too (CITIES lists them)";
            }
        }
        List<String> teams = null;
        String t = i.getStringExtra("teams");
        if (t != null) {
            teams = new ArrayList<>();
            for (String part : t.split(",")) {
                part = part.trim();
                if (part.isEmpty()) continue;
                String[] kv = part.split(":", 2);
                if (!kv[0].matches("\\d+")) return "error: teams are id:EnglishName, e.g. 136013:Al-Hilal";
                String en = kv.length > 1 ? kv[1].trim() : "";
                // the bundled list knows the club by id (its Arabic name as the screen shows it); a club outside
                // the list gets the name made from its English one
                TeamSearch.Team known = Teams.byId(c, kv[0]);
                String ar = known != null && !known.ar.isEmpty() ? known.ar
                    : en.isEmpty() ? "#" + kv[0] : Arabic.team(c, en);
                teams.add(kv[0] + "|" + ar.replace("|", " ").replace(";", " "));
            }
            if (teams.size() > Prefs.MAX_TEAMS) return "error: at most " + Prefs.MAX_TEAMS + " teams";
        }
        String panel = i.getStringExtra("panel"), home = i.getStringExtra("home_panel");
        if (panel != null && !isPanel(panel)) return "error: panel is one of " + panels();
        if (home != null && !isPanel(home)) return "error: home_panel is one of " + panels();
        String rating = i.getStringExtra("minrating");
        if (rating != null && !Arrays.asList(Prefs.MIN_RATINGS).contains(rating))
            return "error: minrating is one of " + Prefs.join(Arrays.asList(Prefs.MIN_RATINGS), " ");
        String photos = i.getStringExtra("photos");
        if (photos != null && !Arrays.asList(Prefs.PHOTO_MINUTES).contains(photos))
            return "error: photos is one of " + Prefs.join(Arrays.asList(Prefs.PHOTO_MINUTES), " ");
        String idle = i.getStringExtra("idle");
        if (idle != null) {
            if (!Arrays.asList(Prefs.IDLE_MINUTES).contains(idle))
                return "error: idle is one of " + Prefs.join(Arrays.asList(Prefs.IDLE_MINUTES), " ");
            if (!Prefs.canWriteSettings(c))
                return "error: idle not allowed: this app may not change system settings on this TV"
                    + " (the TV's own screensaver settings can, or the shell: settings put system screen_off_timeout)";
        }
        List<String> genres = codes(i.getStringExtra("genres"), Prefs.GENRES);
        List<String> langs = codes(i.getStringExtra("langs"), Prefs.LANGS);
        if (genres != null && genres.contains(null)) return "error: genres are " + names(Prefs.GENRES);
        if (langs != null && langs.contains(null)) return "error: langs are " + names(Prefs.LANGS);

        if (idle != null) {   // first: a refusal here leaves everything else unsaved
            try {
                Settings.System.putInt(c.getContentResolver(), Settings.System.SCREEN_OFF_TIMEOUT,
                    Integer.parseInt(idle) * 60000);
            } catch (SecurityException e) {
                return "error: idle not allowed: the TV refused the change";
            }
        }
        if (city != null) p.setCity(city[0], city[1], city[2]);
        if (teams != null) p.setList("teams", teams);
        if (panel != null) p.setPanel(panel);
        if (home != null) p.setHomePanel(home);
        if (rating != null) p.setMinRating(rating);
        if (photos != null) p.setPhotoMinutes(photos);
        if (genres != null) p.setList("genres", genres);
        if (langs != null) p.setList("langs", langs);
        return "saved\n" + describe(c, p);
    }

    private static String describe(Context c, Prefs p) {
        String[] city = p.city();
        return "city: " + city[0] + " (" + city[1] + ", " + city[2] + ")"
            + "\nteams: " + Prefs.join(p.teams(), ", ")
            + "\npanel: " + p.panel() + "\nhome_panel: " + p.homePanel()
            + "\nminrating: " + p.minRating()
            + "\nphotos: " + p.photoMinutes()
            + "\nidle: " + idle(Prefs.idleMs(c))
            + "\ngenres: " + Prefs.join(p.list("genres"), ",") + "\nlangs: " + Prefs.join(p.list("langs"), ",")
            + "\nautoupdate: " + p.autoUpdate();
    }

    /** minutes the TV waits before the screensaver, "unknown" when it does not say */
    private static String idle(long ms) {
        if (ms <= 0) return "unknown";
        return ms % 60000 == 0 ? String.valueOf(ms / 60000) : (ms / 1000) + "s";
    }

    private static boolean isPanel(String v) {
        for (String[] x : Prefs.PANELS) if (x[0].equals(v)) return true;
        return false;
    }

    private static String panels() {
        return names(Prefs.PANELS);
    }

    private static String names(String[][] table) {
        List<String> out = new ArrayList<>();
        for (String[] x : table) out.add(x[0]);
        return Prefs.join(out, " ");
    }

    /** "Drama,Comedy" -> the same codes, checked against the table; null entry = unknown; "" = all. */
    private static List<String> codes(String raw, String[][] table) {
        if (raw == null) return null;
        List<String> out = new ArrayList<>();
        for (String s : raw.split(",")) {
            s = s.trim();
            if (s.isEmpty()) continue;
            String hit = null;
            for (String[] x : table) if (x[0].equalsIgnoreCase(s)) hit = x[0];
            out.add(hit);
        }
        return out;
    }
}
