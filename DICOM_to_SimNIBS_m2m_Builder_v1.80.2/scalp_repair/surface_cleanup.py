# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Remove degenerate/duplicate index faces, without moving or welding vertices.
Opposite coincident faces cancel as zero-thickness sheets in a binary-volume boundary.
Remaining non-manifold edges are never removed arbitrarily.
"""
import numpy as np

def clean_surface(v,tri):
 v=np.asarray(v,float);tri=np.asarray(tri,int)
 if tri.ndim!=2 or tri.shape[1]!=3 or not len(tri):raise ValueError('Empty or invalid surface faces')
 if not np.isfinite(v).all() or tri.min()<0 or tri.max()>=len(v):raise ValueError('Invalid surface vertices')
 original=len(tri);area2=np.linalg.norm(np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]]),axis=1)
 valid=area2>1e-10;degenerate=int((~valid).sum());tri=tri[valid]
 _,inverse,counts=np.unique(np.sort(tri,axis=1),axis=0,return_inverse=True,return_counts=True)
 keep=np.ones(len(tri),bool);opposite_pairs=0;same_removed=0
 # Only visit duplicate groups. Ordinary faces retain their exact winding and vertices.
 for group in np.flatnonzero(counts>1):
  indices=np.flatnonzero(inverse==group);t=tri[indices]
  parity=((t[:,0]>t[:,1]).astype(int)+(t[:,0]>t[:,2])+(t[:,1]>t[:,2]))%2
  plus=indices[parity==0];minus=indices[parity==1];pairs=min(len(plus),len(minus));opposite_pairs+=pairs
  keep[plus[:pairs]]=False;keep[minus[:pairs]]=False
  rest=np.r_[plus[pairs:],minus[pairs:]]
  if len(rest)>1:keep[rest[1:]]=False;same_removed+=len(rest)-1
 result=tri[keep]
 if not len(result):raise ValueError('Surface contains only degenerate/coincident sheets; rebuild the mask')
 edges=np.sort(np.vstack([result[:,[0,1]],result[:,[1,2]],result[:,[2,0]]]),axis=1);_,n=np.unique(edges,axis=0,return_counts=True)
 report={'input_faces':original,'output_faces':len(result),'degenerate_faces_removed':degenerate,'opposite_duplicate_pairs_cancelled':opposite_pairs,'same_winding_duplicates_removed':same_removed,'nonmanifold_edges_remaining':int((n>2).sum()),'boundary_edges':int((n==1).sum()),'vertices_moved_or_welded':False}
 if report['nonmanifold_edges_remaining']:
  raise ValueError(f"Remaining {report['nonmanifold_edges_remaining']} non-manifold edges (more than two triangles per edge). Duplicate faces were checked; automatic cleanup cannot resolve this. Inspect the REVIEWED mask and PLY, or edit the mask and export again.")
 return v,result,report
