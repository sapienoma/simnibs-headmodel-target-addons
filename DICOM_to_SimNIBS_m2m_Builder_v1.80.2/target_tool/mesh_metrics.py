# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Surface sampling statistics; these do not estimate source MRI resolution."""
import numpy as np

def density(vertices,triangles):
    v=np.asarray(vertices,float);t=np.asarray(triangles,int)
    if v.ndim!=2 or v.shape[1]!=3 or t.ndim!=2 or t.shape[1]!=3 or not len(t):raise ValueError('Invalid triangle surface')
    if not np.isfinite(v).all() or t.min()<0 or t.max()>=len(v):raise ValueError('Invalid surface indices')
    edges=np.unique(np.sort(np.vstack([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]),axis=1),axis=0)
    lengths=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
    return {'triangles':int(len(t)),'used_vertices':int(len(np.unique(t))),'mean_edge_mm':float(lengths.mean()),'median_edge_mm':float(np.median(lengths))}
