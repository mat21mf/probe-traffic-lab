package lab.probetraffic;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Minimal CSV reader/writer for the contract files (header row, comma separated, no quoting). */
public final class CsvIO {
    private CsvIO() {}

    private static List<String[]> rows(Path p) throws IOException {
        List<String[]> out = new ArrayList<>();
        try (BufferedReader r = Files.newBufferedReader(p)) {
            String line = r.readLine();   // header
            while ((line = r.readLine()) != null) {
                if (!line.isBlank()) out.add(line.split(","));
            }
        }
        return out;
    }

    public static List<Traversal> traversals(Path p) throws IOException {
        List<Traversal> out = new ArrayList<>();
        for (String[] f : rows(p)) {
            out.add(new Traversal(Long.parseLong(f[0]), Integer.parseInt(f[1]),
                                  Double.parseDouble(f[2]), Double.parseDouble(f[3])));
        }
        return out;
    }

    public static Map<Integer, Double> segmentLengths(Path p) throws IOException {
        Map<Integer, Double> m = new HashMap<>();
        for (String[] f : rows(p)) m.put(Integer.parseInt(f[0]), Double.parseDouble(f[1]));
        return m;
    }

    /** expected_counts.csv: segment_id,bin,expected (dense or sparse; missing cells are 0). */
    public static double[][] expected(Path p, int nSeg, int nBins) throws IOException {
        double[][] m = new double[nSeg][nBins];
        for (String[] f : rows(p)) m[Integer.parseInt(f[0])][Integer.parseInt(f[1])] = Double.parseDouble(f[2]);
        return m;
    }

    public static void writeSpeeds(Path p, List<SegmentSpeed> xs) throws IOException {
        try (BufferedWriter w = Files.newBufferedWriter(p)) {
            w.write("segment_id,bin,n,speed_mps,published\n");
            for (SegmentSpeed s : xs) {
                w.write(String.format(Locale.ROOT, "%d,%d,%d,%.17g,%s%n", s.segmentId(), s.bin(), s.n(),
                                      s.speedMps(), s.published() ? "true" : "false"));
            }
        }
    }

    public static void writeClosures(Path p, List<ClosureEvent> xs) throws IOException {
        try (BufferedWriter w = Files.newBufferedWriter(p)) {
            w.write("segment_id,est_start_s,flag_s,cleared_s\n");
            for (ClosureEvent c : xs) {
                w.write(String.format(Locale.ROOT, "%d,%.17g,%.17g,%.17g%n", c.segmentId(), c.estStartS(),
                                      c.flagS(), c.clearedS()));
            }
        }
    }
}
