package lab.probetraffic;

import java.nio.file.Path;
import java.util.List;
import java.util.Map;

/**
 * Dependency-free golden test: runs the core on contracts/golden/in and checks
 * the result against contracts/golden/expected (produced by the Python
 * prototype). Exit code 0 on success, 1 on mismatch.
 *
 *   java -cp core/build lab.probetraffic.GoldenFixtureTest contracts/golden
 */
public final class GoldenFixtureTest {
    static final double TOL = 1e-9;
    static int failures = 0;

    public static void main(String[] args) throws Exception {
        Path g = Path.of(args.length > 0 ? args[0] : "contracts/golden");
        double t0 = 21600; int bin = 900, nBins = 64, cbin = 300, ncb = 192; double alpha = 1e-4;

        List<Traversal> trav = CsvIO.traversals(g.resolve("in/traversals.csv"));
        Map<Integer, Double> len = CsvIO.segmentLengths(g.resolve("in/segments.csv"));
        int nSeg = len.keySet().stream().mapToInt(Integer::intValue).max().orElse(-1) + 1;
        double[][] expected = CsvIO.expected(g.resolve("in/expected_counts.csv"), nSeg, ncb);

        List<SegmentSpeed> speeds = new SegmentSpeedAggregator(len, t0, bin, nBins, 3, 0.5, 40.0).aggregate(trav);
        List<ClosureEvent> closures = new ClosureDetector(t0, cbin, alpha)
                .detect(ClosureDetector.counts(trav, nSeg, t0, cbin, ncb), expected);

        List<String[]> expSp = rows(g.resolve("expected/segment_speeds.csv"));
        check("speed cell count", expSp.size() == speeds.size());
        for (int i = 0; i < Math.min(expSp.size(), speeds.size()); i++) {
            String[] e = expSp.get(i);
            SegmentSpeed s = speeds.get(i);
            boolean ok = Integer.parseInt(e[0]) == s.segmentId() && Integer.parseInt(e[1]) == s.bin()
                    && Integer.parseInt(e[2]) == s.n() && close(Double.parseDouble(e[3]), s.speedMps())
                    && Boolean.parseBoolean(e[4].toLowerCase()) == s.published();
            if (!ok) { check("speed row " + i, false); break; }
        }
        List<String[]> expCl = rows(g.resolve("expected/closures_detected.csv"));
        check("closure event count", expCl.size() == closures.size());
        for (int i = 0; i < Math.min(expCl.size(), closures.size()); i++) {
            String[] e = expCl.get(i);
            ClosureEvent c = closures.get(i);
            boolean ok = Integer.parseInt(e[0]) == c.segmentId() && close(Double.parseDouble(e[1]), c.estStartS())
                    && close(Double.parseDouble(e[2]), c.flagS()) && close(Double.parseDouble(e[3]), c.clearedS());
            if (!ok) { check("closure row " + i, false); break; }
        }
        System.out.printf("golden: %d speed cells, %d closure events, %s%n", speeds.size(), closures.size(),
                          failures == 0 ? "PASS" : failures + " FAILURES");
        System.exit(failures == 0 ? 0 : 1);
    }

    static boolean close(double a, double b) { return Math.abs(a - b) <= TOL * Math.max(1, Math.abs(a)); }

    static void check(String what, boolean ok) {
        if (!ok) { failures++; System.out.println("FAIL: " + what); }
    }

    static List<String[]> rows(Path p) throws Exception {
        List<String> lines = java.nio.file.Files.readAllLines(p);
        return lines.subList(1, lines.size()).stream().filter(l -> !l.isBlank()).map(l -> l.split(",")).toList();
    }
}
