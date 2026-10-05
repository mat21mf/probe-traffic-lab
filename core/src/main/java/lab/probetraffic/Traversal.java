package lab.probetraffic;

/** One fully observed segment traversal from map-matching (contracts/traversals.schema.json). */
public record Traversal(long probeId, int segmentId, double entryS, double exitS) {
    public double travelTimeS() { return exitS - entryS; }
    public double midS() { return 0.5 * (entryS + exitS); }
}
