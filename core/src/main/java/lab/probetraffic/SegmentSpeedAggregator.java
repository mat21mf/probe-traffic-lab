package lab.probetraffic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Per-segment, per-bin speed: length / median travel time.
 * Traversals are binned by midpoint; implausible speeds are dropped first.
 * Mirrors prototype/probetraffic/estimation/segment_speed.py.
 */
public final class SegmentSpeedAggregator {
    private final Map<Integer, Double> lengthM;
    private final double t0S;
    private final int binS;
    private final int nBins;
    private final int minSamples;
    private final double vminMps;
    private final double vmaxMps;

    public SegmentSpeedAggregator(Map<Integer, Double> lengthM, double t0S, int binS, int nBins,
                                  int minSamples, double vminMps, double vmaxMps) {
        this.lengthM = lengthM;
        this.t0S = t0S;
        this.binS = binS;
        this.nBins = nBins;
        this.minSamples = minSamples;
        this.vminMps = vminMps;
        this.vmaxMps = vmaxMps;
    }

    public List<SegmentSpeed> aggregate(List<Traversal> traversals) {
        Map<Long, List<Double>> cells = new HashMap<>();
        for (Traversal t : traversals) {
            Double len = lengthM.get(t.segmentId());
            double tt = t.travelTimeS();
            if (len == null || tt <= 0) continue;
            double v = len / tt;
            if (v < vminMps || v > vmaxMps) continue;
            int bin = (int) Math.floor((t.midS() - t0S) / binS);
            if (bin < 0 || bin >= nBins) continue;
            cells.computeIfAbsent(key(t.segmentId(), bin), k -> new ArrayList<>()).add(tt);
        }
        List<SegmentSpeed> out = new ArrayList<>(cells.size());
        for (Map.Entry<Long, List<Double>> e : cells.entrySet()) {
            int seg = (int) (e.getKey() >> 32);
            int bin = (int) (e.getKey() & 0xffffffffL);
            double med = median(e.getValue());
            int n = e.getValue().size();
            out.add(new SegmentSpeed(seg, bin, n, lengthM.get(seg) / med, n >= minSamples));
        }
        out.sort(Comparator.comparingInt(SegmentSpeed::segmentId).thenComparingInt(SegmentSpeed::bin));
        return out;
    }

    static long key(int seg, int bin) { return ((long) seg << 32) | (bin & 0xffffffffL); }

    static double median(List<Double> xs) {
        double[] a = xs.stream().mapToDouble(Double::doubleValue).toArray();
        Arrays.sort(a);
        int m = a.length / 2;
        return a.length % 2 == 1 ? a[m] : 0.5 * (a[m - 1] + a[m]);
    }
}
