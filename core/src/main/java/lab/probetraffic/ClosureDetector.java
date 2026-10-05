package lab.probetraffic;

import java.util.ArrayList;
import java.util.List;

/**
 * Poisson silence test for closures. Mirrors
 * prototype/probetraffic/estimation/closure_detect.py:
 * expected counts are scaled by the network-wide volume ratio per bin;
 * consecutive empty bins accumulate expected volume L; flag when
 * L >= -ln(alpha); clear at the first bin with an observed traversal.
 */
public final class ClosureDetector {
    private final double t0S;
    private final int binS;
    private final double alpha;

    public ClosureDetector(double t0S, int binS, double alpha) {
        this.t0S = t0S;
        this.binS = binS;
        this.alpha = alpha;
    }

    /** Traversal counts per [segment][bin], binned by entry time. */
    public static double[][] counts(List<Traversal> traversals, int nSeg, double t0S, int binS, int nBins) {
        double[][] m = new double[nSeg][nBins];
        for (Traversal t : traversals) {
            int b = (int) Math.floor((t.entryS() - t0S) / binS);
            if (b >= 0 && b < nBins && t.segmentId() >= 0 && t.segmentId() < nSeg) m[t.segmentId()][b] += 1;
        }
        return m;
    }

    public List<ClosureEvent> detect(double[][] counts, double[][] expected) {
        int nSeg = counts.length;
        int nBins = counts[0].length;
        double[] ratio = new double[nBins];
        for (int b = 0; b < nBins; b++) {
            double c = 0, e = 0;
            for (int s = 0; s < nSeg; s++) { c += counts[s][b]; e += expected[s][b]; }
            ratio[b] = e > 0 ? c / Math.max(e, 1e-9) : 1.0;
        }
        double thr = -Math.log(alpha);
        List<ClosureEvent> out = new ArrayList<>();
        for (int s = 0; s < nSeg; s++) {
            double acc = 0;
            int first = -1, flagged = -1;
            for (int b = 0; b < nBins; b++) {
                if (counts[s][b] == 0) {
                    if (first < 0) { first = b; acc = 0; }
                    acc += expected[s][b] * ratio[b];
                    if (flagged < 0 && acc >= thr) flagged = b;
                } else {
                    if (flagged >= 0) out.add(event(s, first, flagged, b));
                    first = -1; flagged = -1; acc = 0;
                }
            }
            if (flagged >= 0) out.add(event(s, first, flagged, nBins));
        }
        return out;
    }

    private ClosureEvent event(int s, int first, int flagged, int clearedBin) {
        return new ClosureEvent(s, t0S + (double) first * binS, t0S + (double) (flagged + 1) * binS,
                                t0S + (double) clearedBin * binS);
    }
}
