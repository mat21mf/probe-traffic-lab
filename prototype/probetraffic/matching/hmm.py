"""HMM map-matching (Newson and Krumm, 2009) and traversal reconstruction.

States are candidate projections of each GPS point onto nearby segments.
- Emission: gaussian on the point-to-segment distance.
- Transition: exponential on |route distance - straight-line distance|
  between consecutive points; transitions implying an impossible speed are
  forbidden.
Viterbi decoding restarts a new chain when no transition is feasible.

The matched path is then expanded with the shortest-path segments between
consecutive matches, and segment boundary crossing times are interpolated
assuming constant speed between two probes. Only fully observed segment
traversals (entry and exit both inside the matched trace) are emitted.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path

from probetraffic.graph.grid import RoadGraph

NEG = -1e18


@dataclass
class MatchConfig:
    sigma_m: float = 8.0          # GPS noise, emission scale
    beta_m: float = 10.0          # transition scale
    radius_m: float = 45.0        # candidate search radius
    max_candidates: int = 6
    vmax_mps: float = 30.0        # forbid transitions faster than this
    backtrack_tol_m: float = 20.0 # same-segment backward jitter treated as standing still


class Matcher:
    def __init__(self, g: RoadGraph, cfg: MatchConfig):
        self.g, self.cfg = g, cfg
        s = g.segments
        self.x0, self.y0 = s.x0.to_numpy(), s.y0.to_numpy()
        self.dx, self.dy = (s.x1 - s.x0).to_numpy(), (s.y1 - s.y0).to_numpy()
        self.len = s.length_m.to_numpy()
        self.u, self.v = s.u.to_numpy(), s.v.to_numpy()
        n = len(g.nodes)
        adj = csr_matrix((self.len, (self.u, self.v)), shape=(n, n))
        self.dist, self.pred = shortest_path(adj, directed=True, return_predecessors=True)
        self.seg_of = {(a, b): k for k, (a, b) in enumerate(zip(self.u, self.v))}

    # -- candidates -------------------------------------------------------
    def candidates(self, x, y):
        f = ((x - self.x0) * self.dx + (y - self.y0) * self.dy) / self.len ** 2
        f = np.clip(f, 0, 1)
        px, py = self.x0 + f * self.dx, self.y0 + f * self.dy
        d = np.hypot(x - px, y - py)
        idx = np.where(d <= self.cfg.radius_m)[0]
        idx = idx[np.argsort(d[idx])][: self.cfg.max_candidates]
        return idx, f[idx] * self.len[idx], d[idx]

    # -- transition -------------------------------------------------------
    def route_dist(self, sa, oa, sb, ob):
        """Matrix of route distances from candidates (sa, oa) to (sb, ob)."""
        rd = (self.len[sa] - oa)[:, None] + self.dist[self.v[sa]][:, self.u[sb]] + ob[None, :]
        same = sa[:, None] == sb[None, :]
        fwd = ob[None, :] - oa[:, None]
        tol = self.cfg.backtrack_tol_m
        rd = np.where(same & (fwd >= 0), fwd, rd)
        rd = np.where(same & (fwd < 0) & (fwd > -tol), 0.0, rd)
        return rd

    def seg_path(self, a_node, b_node):
        if a_node == b_node:
            return []
        nodes = [b_node]
        while nodes[-1] != a_node:
            p = self.pred[a_node, nodes[-1]]
            if p < 0:
                return None
            nodes.append(p)
        nodes.reverse()
        return [self.seg_of[(p, q)] for p, q in zip(nodes[:-1], nodes[1:])]

    # -- viterbi ----------------------------------------------------------
    def match_trace(self, t, x, y):
        """Return list of chains; each chain is a list of (t, seg, offset)."""
        c = self.cfg
        chains, cur = [], None
        prev = None   # (segs, offs, score, backptr list, point index list)
        steps = []
        for i in range(len(t)):
            segs, offs, d = self.candidates(x[i], y[i])
            if len(segs) == 0:
                continue
            emis = -0.5 * (d / c.sigma_m) ** 2
            if prev is None:
                prev = (segs, offs, emis, i)
                steps = [(i, segs, offs, None)]
                continue
            psegs, poffs, pscore, pi = prev
            gc = np.hypot(x[i] - x[pi], y[i] - y[pi])
            dt = max(t[i] - t[pi], 1e-3)
            rd = self.route_dist(psegs, poffs, segs, offs)
            trans = -np.abs(rd - gc) / c.beta_m
            trans = np.where(np.isfinite(rd) & (rd / dt <= c.vmax_mps), trans, NEG)
            tot = pscore[:, None] + trans
            back = tot.argmax(axis=0)
            best = tot.max(axis=0)
            if best.max() <= NEG / 2:
                chains.append(self._backtrack(steps, pscore, t))
                prev = (segs, offs, emis, i)
                steps = [(i, segs, offs, None)]
                continue
            score = best + emis
            score -= score.max()
            prev = (segs, offs, score, i)
            steps.append((i, segs, offs, back))
        if prev is not None:
            chains.append(self._backtrack(steps, prev[2], t))
        return chains

    @staticmethod
    def _backtrack(steps, last_score, t):
        k = int(np.argmax(last_score))
        out = []
        for i, segs, offs, back in reversed(steps):
            out.append((t[i], int(segs[k]), float(offs[k])))
            if back is not None:
                k = int(back[k])
        out.reverse()
        return out

    # -- traversal reconstruction -------------------------------------------
    def traversals(self, chain):
        """Complete segment traversals (segment, entry_s, exit_s) for one chain."""
        events = []   # (segment, kind, time) kind: 0 entry, 1 exit
        for (t1, a, oa), (t2, b, ob) in zip(chain[:-1], chain[1:]):
            if a == b and ob >= oa - self.cfg.backtrack_tol_m:
                continue
            mid = self.seg_path(self.v[a], self.u[b])
            if mid is None:
                continue
            legs = [(a, self.len[a] - oa)] + [(s, self.len[s]) for s in mid]
            total = sum(l for _, l in legs) + ob
            if total <= 0:
                continue
            speed_t = (t2 - t1) / total
            pos = 0.0
            for k, (s, l) in enumerate(legs):
                pos += l
                tb = t1 + pos * speed_t          # boundary: exit s, enter next
                events.append((s, 1, tb))
                nxt = mid[k] if k < len(mid) else b
                events.append((nxt, 0, tb))
        out, open_entry = [], {}
        for s, kind, tb in events:
            if kind == 0:
                open_entry = {s: tb}
            elif s in open_entry:
                out.append((s, open_entry[s], tb))
                open_entry = {}
        return out


def match_probes(g: RoadGraph, probes: pd.DataFrame, cfg: MatchConfig = None):
    """Match all probe traces. Returns (traversals, matched_points)."""
    m = Matcher(g, cfg or MatchConfig())
    trav, pts = [], []
    for pid, grp in probes.sort_values(["probe_id", "t_s"]).groupby("probe_id", sort=False):
        t, x, y = grp.t_s.to_numpy(), grp.x.to_numpy(), grp.y.to_numpy()
        for chain in m.match_trace(t, x, y):
            pts.extend((pid, tt, s) for tt, s, _ in chain)
            trav.extend((pid, s, a, z) for s, a, z in m.traversals(chain))
    return (pd.DataFrame(trav, columns=["probe_id", "segment_id", "entry_s", "exit_s"]),
            pd.DataFrame(pts, columns=["probe_id", "t_s", "segment_id"]))
