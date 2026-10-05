package lab.probetraffic;

/** Speed estimate for one segment and time bin (contracts/segment_speeds.schema.json). */
public record SegmentSpeed(int segmentId, int bin, int n, double speedMps, boolean published) {}
