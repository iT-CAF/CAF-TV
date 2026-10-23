package sa.urtv.screensaver;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/** For tests/team_search_test.py: TeamSearch.java on the same list and queries as optimize/team_search.py.
 *  Args: teams.tsv (id, en, ar, leagues, alt; lists split by ";"), queries.txt (one per line). Prints one line
 *  per query: the ids found, comma-separated. */
public final class TeamSearchRun {
    public static void main(String[] args) throws IOException {
        List<TeamSearch.Team> teams = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(args[0]), StandardCharsets.UTF_8)) {
            String[] f = line.split("\t", -1);
            teams.add(new TeamSearch.Team(f[0], f[1], f[2], split(f[3]), split(f[4])));
        }
        StringBuilder out = new StringBuilder();
        for (String q : Files.readAllLines(Paths.get(args[1]), StandardCharsets.UTF_8)) {
            List<String> ids = new ArrayList<>();
            for (TeamSearch.Team t : TeamSearch.search(teams, q)) ids.add(t.id);
            out.append(String.join(",", ids)).append('\n');
        }
        System.out.write(out.toString().getBytes(StandardCharsets.UTF_8));
        System.out.flush();
    }

    private static String[] split(String s) { return s.isEmpty() ? new String[0] : s.split(";"); }
}
