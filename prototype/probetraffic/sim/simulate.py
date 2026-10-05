"""Ground-truth traffic simulator.

Produces, for one simulated day:
- truth_speeds: true speed per segment per time bin
- closures:     injected closures (segment_id, start_s, end_s)
- traversals:   true segment traversals per vehicle (the matching target)
- probes:       noisy, sparse GPS points per vehicle (the pipeline input)

Vehicles route on travel times at departure, avoid closed segments, and
reroute from the current node if they reach a segment that closed meanwhile.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

from probetraffic.graph.grid import RoadGraph


@dataclass
class SimConfig:
    seed: int = 1
    start_h: float = 6.0
    end_h: float = 22.0
    bin_s: int = 900
    n_trips: int = 4000
    min_trip_m: float = 600.0
    probe_dt_s: float = 10.0
    probe_dt_jitter_s: float = 2.0
    gps_sigma_m: float = 8.0
    dropout: float = 0.1
    vehicle_sigma: float = 0.08
    traversal_sigma: float = 0.10
    n_closures: int = 0
    closure_min_s: int = 2700
    closure_max_s: int = 7200
    closure_ids: list = field(default_factory=list)  # optional fixed segment ids


def _peak(h, mu, sd):
    return np.exp(-0.5 * ((h - mu) / sd) ** 2)


def bin_edges(cfg: SimConfig) -> np.ndarray:
    return np.arange(cfg.start_h * 3600, cfg.end_h * 3600 + 1, cfg.bin_s)


def truth_speeds(g: RoadGraph, cfg: SimConfig, rng) -> pd.DataFrame:
    edges = bin_edges(cfg)
    mids_h = (edges[:-1] + cfg.bin_s / 2) / 3600.0
    shape = _peak(mids_h, 8.5, 1.0) + 0.9 * _peak(mids_h, 18.5, 1.2)
    seg = g.segments
    arterial = seg.freeflow_mps.to_numpy() > 10
    severity = np.where(arterial, rng.uniform(0.35, 0.65, len(seg)), rng.uniform(0.15, 0.45, len(seg)))
    factor = 1.0 - severity[:, None] * shape[None, :]
    factor *= np.exp(rng.normal(0, 0.04, factor.shape))
    speed = seg.freeflow_mps.to_numpy()[:, None] * np.clip(factor, 0.2, 1.05)
    s_idx, b_idx = np.meshgrid(seg.segment_id.to_numpy(), np.arange(len(mids_h)), indexing="ij")
    return pd.DataFrame({"segment_id": s_idx.ravel(), "bin": b_idx.ravel(), "speed_mps": speed.ravel()})


def make_closures(g: RoadGraph, cfg: SimConfig, rng, volume_hint=None) -> pd.DataFrame:
    if cfg.n_closures == 0 and not cfg.closure_ids:
        return pd.DataFrame(columns=["segment_id", "start_s", "end_s"])
    if cfg.closure_ids:
        ids = list(cfg.closure_ids)
    else:
        pool = g.segments.segment_id.to_numpy()
        if volume_hint is not None:
            # closures that matter: draw from the busier half of segments
            pool = volume_hint.sort_values(ascending=False).index[: len(volume_hint) // 2].to_numpy()
        ids = rng.choice(pool, size=cfg.n_closures, replace=False)
    t0, t1 = cfg.start_h * 3600 + 3600, cfg.end_h * 3600 - 3600
    rows = []
    for sid in ids:
        dur = rng.uniform(cfg.closure_min_s, cfg.closure_max_s)
        st = rng.uniform(t0, t1 - dur)
        rows.append((int(sid), float(st), float(st + dur)))
    return pd.DataFrame(rows, columns=["segment_id", "start_s", "end_s"])


class _Router:
    """Shortest-time routing per (time bin, set of closed segments), cached."""

    def __init__(self, g: RoadGraph, speed_mat: np.ndarray):
        self.g, self.speed_mat, self.cache = g, speed_mat, {}
        s = g.segments
        self.u, self.v, self.len = s.u.to_numpy(), s.v.to_numpy(), s.length_m.to_numpy()
        self.seg_of = {(a, b): k for k, (a, b) in enumerate(zip(self.u, self.v))}

    def pred(self, b, closed):
        key = (b, closed)
        if key not in self.cache:
            w = self.len / self.speed_mat[:, b]
            keep = np.ones(len(w), bool)
            keep[list(closed)] = False
            n = len(self.g.nodes)
            m = csr_matrix((w[keep], (self.u[keep], self.v[keep])), shape=(n, n))
            _, p = shortest_path(m, directed=True, return_predecessors=True)
            self.cache[key] = p
        return self.cache[key]

    def path(self, o, d, b, closed):
        p = self.pred(b, closed)
        if o == d or p[o, d] < 0:
            return None if o != d else []
        nodes = [d]
        while nodes[-1] != o:
            nodes.append(p[o, nodes[-1]])
        nodes.reverse()
        return [self.seg_of[(a, c)] for a, c in zip(nodes[:-1], nodes[1:])]


def simulate_day(g: RoadGraph, cfg: SimConfig, closures: pd.DataFrame = None,
                 speeds: pd.DataFrame = None):
    rng = np.random.default_rng(cfg.seed)
    edges = bin_edges(cfg)
    nb = len(edges) - 1
    if speeds is None:
        speeds = truth_speeds(g, cfg, rng)
    if closures is None:
        closures = make_closures(g, cfg, rng)
    speed_mat = speeds.pivot(index="segment_id", columns="bin", values="speed_mps").to_numpy()
    router = _Router(g, speed_mat)
    cl = closures.to_numpy() if len(closures) else np.zeros((0, 3))

    def closed_at(t):
        return frozenset(int(s) for s, a, z in cl if a <= t < z)

    def bin_of(t):
        return int(min(max((t - edges[0]) // cfg.bin_s, 0), nb - 1))

    mids_h = (edges[:-1] + cfg.bin_s / 2) / 3600.0
    demand = 0.35 + _peak(mids_h, 8.5, 1.0) + 0.9 * _peak(mids_h, 18.5, 1.2)
    dep_bins = rng.choice(nb, size=cfg.n_trips, p=demand / demand.sum())
    deps = edges[dep_bins] + rng.uniform(0, cfg.bin_s, cfg.n_trips)
    nodes_xy = g.nodes[["x", "y"]].to_numpy()
    seg = g.segments
    sx0, sy0, sx1, sy1 = (seg[c].to_numpy() for c in ["x0", "y0", "x1", "y1"])
    slen = seg.length_m.to_numpy()

    trav_rows, probe_rows = [], []
    end_s = edges[-1]
    for pid in range(cfg.n_trips):
        while True:
            o, d = rng.integers(0, len(nodes_xy), 2)
            if g.dist[o, d] >= cfg.min_trip_m:
                break
        t = deps[pid]
        vfac = np.exp(rng.normal(0, cfg.vehicle_sigma))
        node, legs = o, []          # legs: (segment_id, entry, exit)
        path = router.path(o, d, bin_of(t), closed_at(t))
        while path and t < end_s:
            sid = path[0]
            if sid in closed_at(t):
                path = router.path(node, d, bin_of(t), closed_at(t))
                if not path:
                    break
                continue
            v = speed_mat[sid, bin_of(t)] * vfac * np.exp(rng.normal(0, cfg.traversal_sigma))
            dt = slen[sid] / v
            legs.append((sid, t, t + dt))
            t += dt
            node = seg.v.iat[sid]
            path = path[1:]
        if not legs:
            continue
        for sid, a, z in legs:
            trav_rows.append((pid, sid, a, z))
        # sample probes along the legs
        ts = legs[0][1] + rng.uniform(0, cfg.probe_dt_s)
        li = 0
        while ts < legs[-1][2]:
            while legs[li][2] < ts:
                li += 1
            sid, a, z = legs[li]
            f = (ts - a) / (z - a)
            x = sx0[sid] + f * (sx1[sid] - sx0[sid]) + rng.normal(0, cfg.gps_sigma_m)
            y = sy0[sid] + f * (sy1[sid] - sy0[sid]) + rng.normal(0, cfg.gps_sigma_m)
            if rng.random() >= cfg.dropout:
                probe_rows.append((pid, ts, x, y))
            ts += cfg.probe_dt_s + rng.uniform(-cfg.probe_dt_jitter_s, cfg.probe_dt_jitter_s)

    traversals = pd.DataFrame(trav_rows, columns=["probe_id", "segment_id", "entry_s", "exit_s"])
    probes = pd.DataFrame(probe_rows, columns=["probe_id", "t_s", "x", "y"])
    return {"truth_speeds": speeds, "closures": closures, "traversals": traversals, "probes": probes}
