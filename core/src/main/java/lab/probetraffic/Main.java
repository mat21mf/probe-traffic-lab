package lab.probetraffic;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * CLI: estimate speeds and closures from matched traversals.
 *
 *   java -cp core/build lab.probetraffic.Main estimate --in DIR --out DIR
 *        [--t0 21600] [--bin 900] [--nbins 64] [--count-bin 300] [--count-nbins 192]
 *        [--min-samples 3] [--alpha 1e-4]
 *
 * DIR must contain traversals.csv, segments.csv and expected_counts.csv.
 */
public final class Main {
    public static void main(String[] args) throws Exception {
        if (args.length == 0 || !args[0].equals("estimate")) {
            System.err.println("usage: Main estimate --in DIR --out DIR [options]");
            System.exit(2);
        }
        Map<String, String> o = new HashMap<>();
        for (int i = 1; i + 1 < args.length; i += 2) o.put(args[i], args[i + 1]);
        Path in = Path.of(o.getOrDefault("--in", "."));
        Path out = Path.of(o.getOrDefault("--out", "."));
        double t0 = Double.parseDouble(o.getOrDefault("--t0", "21600"));
        int bin = Integer.parseInt(o.getOrDefault("--bin", "900"));
        int nBins = Integer.parseInt(o.getOrDefault("--nbins", "64"));
        int cbin = Integer.parseInt(o.getOrDefault("--count-bin", "300"));
        int ncb = Integer.parseInt(o.getOrDefault("--count-nbins", "192"));
        int minSamples = Integer.parseInt(o.getOrDefault("--min-samples", "3"));
        double alpha = Double.parseDouble(o.getOrDefault("--alpha", "1e-4"));

        long t = System.nanoTime();
        List<Traversal> trav = CsvIO.traversals(in.resolve("traversals.csv"));
        Map<Integer, Double> len = CsvIO.segmentLengths(in.resolve("segments.csv"));
        int nSeg = len.keySet().stream().mapToInt(Integer::intValue).max().orElse(-1) + 1;
        double[][] expected = CsvIO.expected(in.resolve("expected_counts.csv"), nSeg, ncb);
        long tRead = System.nanoTime();

        List<SegmentSpeed> speeds = new SegmentSpeedAggregator(len, t0, bin, nBins, minSamples, 0.5, 40.0)
                .aggregate(trav);
        List<ClosureEvent> closures = new ClosureDetector(t0, cbin, alpha)
                .detect(ClosureDetector.counts(trav, nSeg, t0, cbin, ncb), expected);
        long tEst = System.nanoTime();

        Files.createDirectories(out);
        CsvIO.writeSpeeds(out.resolve("segment_speeds.csv"), speeds);
        CsvIO.writeClosures(out.resolve("closures_detected.csv"), closures);
        System.out.printf("traversals=%d speeds=%d closures=%d read_ms=%.1f estimate_ms=%.1f%n",
                          trav.size(), speeds.size(), closures.size(),
                          (tRead - t) / 1e6, (tEst - tRead) / 1e6);
    }
}
