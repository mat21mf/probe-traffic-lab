"""Synthetic street grid loosely modelled on Barcelona's Eixample.

Nodes sit on a regular grid in a local metric frame (metres). Ordinary
streets are one-way with alternating direction; every `arterial_every`-th
street in each direction is two-way and faster. The result is a directed
segment graph small enough for exact all-pairs shortest paths.
Keep (n - 1) a multiple of arterial_every so the boundary streets are
two-way arterials; otherwise corner nodes can become unreachable.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path


@dataclass
class RoadGraph:
    nodes: pd.DataFrame      # node_id, x, y
    segments: pd.DataFrame   # segment_id, u, v, length_m, freeflow_mps, x0, y0, x1, y1
    dist: np.ndarray         # all-pairs shortest path distance between nodes (metres)

    @property
    def n_segments(self) -> int:
        return len(self.segments)


def build_grid(nx: int = 13, ny: int = 13, block_m: float = 130.0,
               arterial_every: int = 4, street_kmh: float = 30.0,
               arterial_kmh: float = 50.0) -> RoadGraph:
    def nid(i, j):
        return j * nx + i

    coords = {nid(i, j): (i * block_m, j * block_m) for j in range(ny) for i in range(nx)}
    edges = []

    def street(a, b, two_way, forward, kmh):
        if two_way:
            edges.extend([(a, b, kmh), (b, a, kmh)])
        elif forward:
            edges.append((a, b, kmh))
        else:
            edges.append((b, a, kmh))

    for j in range(ny):
        art = j % arterial_every == 0
        for i in range(nx - 1):
            street(nid(i, j), nid(i + 1, j), art, j % 2 == 0, arterial_kmh if art else street_kmh)
    for i in range(nx):
        art = i % arterial_every == 0
        for j in range(ny - 1):
            street(nid(i, j), nid(i, j + 1), art, i % 2 == 0, arterial_kmh if art else street_kmh)

    rows = []
    for k, (u, v, kmh) in enumerate(edges):
        (x0, y0), (x1, y1) = coords[u], coords[v]
        rows.append((k, u, v, float(np.hypot(x1 - x0, y1 - y0)), kmh / 3.6, x0, y0, x1, y1))
    segments = pd.DataFrame(rows, columns=["segment_id", "u", "v", "length_m",
                                           "freeflow_mps", "x0", "y0", "x1", "y1"])
    nodes = pd.DataFrame([(k, x, y) for k, (x, y) in coords.items()], columns=["node_id", "x", "y"])
    n = len(nodes)
    adj = csr_matrix((segments.length_m.to_numpy(), (segments.u.to_numpy(), segments.v.to_numpy())),
                     shape=(n, n))
    return RoadGraph(nodes=nodes, segments=segments, dist=shortest_path(adj, directed=True))
