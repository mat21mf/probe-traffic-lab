package lab.probetraffic;

/** A detected closure (contracts/closures.schema.json). */
public record ClosureEvent(int segmentId, double estStartS, double flagS, double clearedS) {}
