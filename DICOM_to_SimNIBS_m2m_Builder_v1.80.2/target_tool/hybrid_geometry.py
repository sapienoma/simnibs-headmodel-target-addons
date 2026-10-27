# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Local superior-cap replacement with an explicit shared-vertex seam.

The original vertices and fully retained triangles are unchanged. Original lower
surface and donor upper cap occupy disjoint half spaces. Only the intervening
annulus is newly triangulated. Reject multi-loop cuts or intersecting seams rather than
inventing bridges. No whole-head resampling or smoothing is performed.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

EPS=1e-8

class SurfaceTopologyError(ValueError):
 def __init__(self,stage,reason,details=None):
  self.details={'stage':stage,'reason':str(reason),**(details or {})}
  super().__init__(stage+': '+str(reason))

def boundary_anomalies(t,nv):
 edges,count,_=edge_data(np.asarray(t,int));border=edges[count==1]
 degree=np.bincount(border.ravel(),minlength=nv)
 return np.flatnonzero((degree!=0)&(degree!=2)),degree

def checked_topology(v,t,stage,allowed_boundary_vertices=()):
 """Keep the failed input and boundary coordinates in the diagnostic output."""
 try:return topology(v,t,allowed_boundary_vertices)
 except ValueError as e:
  details={}
  try:
   edges,count,_=edge_data(np.asarray(t,int));border=edges[count==1]
   degree=np.bincount(border.ravel(),minlength=len(v));bad=np.flatnonzero((degree!=0)&(degree!=2))
   details={'boundary_edges':int(len(border)),'nonmanifold_edges':int((count>2).sum()),
    'boundary_vertices':[{'vertex_index_0based':int(i),'RAS_mm':np.asarray(v[i],float).tolist(),'boundary_degree':int(degree[i])} for i in bad]}
  except (ValueError,IndexError):pass
  raise SurfaceTopologyError(stage,e,details) from e

def checked_clip(v,t,n,h,below,stage):
 try:return clip(v,t,n,h,below)
 except ValueError as e:raise SurfaceTopologyError(stage,e,{'plane_h_mm':float(h),'normal_RAS':np.asarray(n).tolist()}) from e

def unit(x):
 x=np.asarray(x,float);d=np.linalg.norm(x)
 if d<1e-12:raise ValueError('Invalid cutting-plane normal')
 return x/d

def edge_data(t):
 directed=np.vstack([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]);edges=np.sort(directed,axis=1)
 unique,inverse,count=np.unique(edges,axis=0,return_inverse=True,return_counts=True)
 balance=np.bincount(inverse,weights=np.where(directed[:,0]<directed[:,1],1,-1),minlength=len(unique))
 return unique,count,balance

def topology(v,t,allowed_boundary_vertices=()):
 v=np.asarray(v,float);t=np.asarray(t,int)
 if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all() or t.ndim!=2 or t.shape[1]!=3 or not len(t) or t.min()<0 or t.max()>=len(v):raise ValueError('Invalid surface arrays')
 area=np.linalg.norm(np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]),axis=1)/2
 if np.any(area<=1e-10):raise ValueError('Degenerate triangles')
 if len(np.unique(np.sort(t,axis=1),axis=0))!=len(t):raise ValueError('Duplicate triangles')
 edges,count,balance=edge_data(t)
 if np.any(count>2):raise ValueError('Non-manifold edges')
 if np.any(balance[count==2]!=0):raise ValueError('Inconsistent triangle winding')
 graph=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
 _,labels=connected_components(graph,directed=False)
 if len(np.unique(labels[np.unique(t)]))!=1:raise ValueError('Surface is disconnected')
 # Vertex-link tests reject pinched vertices that edge-incidence alone misses.
 border=edges[count==1];bd=np.bincount(border.ravel(),minlength=len(v)) if len(border) else np.zeros(len(v),int)
 bad=np.flatnonzero((bd!=0)&(bd!=2))
 if np.any(~np.isin(bad,np.asarray(allowed_boundary_vertices,int))):raise ValueError('Non-manifold boundary vertex')
 return {'triangles':int(len(t)),'used_vertices':int(len(np.unique(t))),'boundary_edges':int(len(border)),'minimum_triangle_area_mm2':float(area.min())},border

def clip(v,t,n,h,below=True):
 """Clip triangles with cached edge intersections; preserve full inside faces."""
 v=np.asarray(v,float);t=np.asarray(t,int);d=(v@n-h)*(1 if below else -1)
 inside=d<=EPS;whole=inside[t].all(1);outside=(~inside[t]).all(1)
 output=t[whole].tolist();original_count=len(output);points=v.tolist();cache={}
 def crossing(a,b):
  if abs(d[a])<=EPS:return int(a)
  if abs(d[b])<=EPS:return int(b)
  key=tuple(sorted((int(a),int(b))))
  if key not in cache:
   q=v[a]+d[a]/(d[a]-d[b])*(v[b]-v[a]);cache[key]=len(points);points.append(q.tolist())
  return cache[key]
 for tri in t[~whole&~outside]:
  poly=[]
  for j in range(3):
   a=int(tri[j]);b=int(tri[(j+1)%3])
   if inside[a]:poly.append(a)
   if inside[a]!=inside[b]:poly.append(crossing(a,b))
  poly=list(dict.fromkeys(poly))
  for j in range(1,len(poly)-1):output.append([poly[0],poly[j],poly[j+1]])
 if not output:raise ValueError('Cut removed the entire surface; adjust cut height')
 outv=np.asarray(points,float);outt=np.asarray(output,int)
 # Exact-on-plane faces make the seam ambiguous; do not create overlapping caps.
 if np.any(np.max(np.abs(outv[outt]@n-h),axis=1)<EPS):raise ValueError('Cut coincides with a flat face; shift cut height slightly')
 edges,count,_=edge_data(outt);boundary=edges[count==1]
 on=np.all(np.abs(outv[boundary]@n-h)<1e-6,axis=1)
 ringedges=boundary[on]
 if len(ringedges)<3:raise ValueError('No valid closed cut ring; adjust height / verify scan coverage')
 adj={}
 for a,b in ringedges:
  adj.setdefault(int(a),[]).append(int(b));adj.setdefault(int(b),[]).append(int(a))
 if any(len(x)!=2 for x in adj.values()):raise ValueError('Cut boundary branches; cannot stitch reliably')
 first=min(adj);ring=[first];previous=None;current=first
 while True:
  nxt=next(x for x in adj[current] if x!=previous)
  if nxt==first:break
  if nxt in ring:raise ValueError('Cut ring repeats vertices')
  ring.append(nxt);previous,current=current,nxt
 if len(ring)!=len(adj):raise ValueError('Cut has multiple loops; no automatic joining')
 return outv,outt,np.array(ring,int),boundary[~on],original_count,whole

def basis(n):
 axis=np.eye(3)[int(np.argmin(np.abs(n)))];u=unit(np.cross(axis,n));return u,np.cross(n,u)

def polygon_centroid(p):
 q=np.roll(p,-1,axis=0);cross=p[:,0]*q[:,1]-q[:,0]*p[:,1];area=cross.sum()
 if abs(area)<1e-8:raise ValueError('Collapsed cut polygon')
 return ((p+q)*cross[:,None]).sum(0)/(3*area)

def parameter_ring(v,ring,u,w,center):
 p=np.column_stack([v[ring]@u,v[ring]@w]);q=np.roll(p,-1,axis=0)
 if np.sum(p[:,0]*q[:,1]-q[:,0]*p[:,1])<0:ring=ring[::-1];p=p[::-1]
 # A common angular anchor fixes cyclic phase; normalized boundary arc length
 # handles voxel-scale contour reversals without moving/resampling source vertices.
 projected=p-center;angles=np.arctan2(projected[:,1],projected[:,0]);k=int(angles.argmin())
 ring=np.roll(ring,-k);lengths=np.linalg.norm(np.roll(v[ring],-1,axis=0)-v[ring],axis=1)
 if np.any(lengths<=1e-10) or lengths.sum()<=0:raise ValueError('Collapsed / repeated cut-ring segment')
 parameter=np.r_[0.,np.cumsum(lengths[:-1])]/lengths.sum()
 return ring,parameter

def bridge(v,lower,upper,n,max_gap):
 u,w=basis(n)
 centers=[polygon_centroid(np.column_stack([v[r]@u,v[r]@w])) for r in (lower,upper)];center=np.mean(centers,axis=0)
 lower,la=parameter_ring(v,lower,u,w,center);upper,ua=parameter_ring(v,upper,u,w,center)
 # Bounds prevent connecting wrong subjects / poorly aligned cap contours.
 d1=cKDTree(v[upper]).query(v[lower])[0];d2=cKDTree(v[lower]).query(v[upper])[0]
 gap=float(max(d1.max(),d2.max()))
 if gap>max_gap:raise ValueError(f'Cut rings are too far apart ({gap:.2f} mm > {max_gap} mm); review registration / cut')
 # Solve an ordered cyclic strip using physical inter-ring edge costs. This
 # tolerates voxel-scale jagged contours without resampling either source ring.
 upper=np.roll(upper,-int(np.argmin(np.linalg.norm(v[upper]-v[lower[0]],axis=1))))
 nl,nu=len(lower),len(upper)
 if (nl+1)*(nu+1)>20_000_000:raise ValueError('Cut rings too dense for this seam solver; adjust cut / use a less dense donor cap')
 from scipy.spatial.distance import cdist
 av=v[np.r_[lower,lower[0]]];bv=v[np.r_[upper,upper[0]]]
 cost=cdist(av,bv,'sqeuclidean');distance=np.full(cost.shape,np.inf);direction=np.zeros(cost.shape,np.uint8);distance[0,0]=cost[0,0]
 for i in range(nl+1):
  for j in range(nu+1):
   if (i==0 and j==0) or (i==nl and j==0) or (j==nu and i==0):continue
   left=distance[i-1,j] if i else np.inf;down=distance[i,j-1] if j else np.inf
   if left<=down:distance[i,j]=left+cost[i,j];direction[i,j]=1
   else:distance[i,j]=down+cost[i,j];direction[i,j]=2
 i,j=nl,nu;out=[]
 while i or j:
  if direction[i,j]==1:
   out.append([lower[(i-1)%nl],lower[i%nl],upper[j%nu]]);i-=1
  elif direction[i,j]==2:
   out.append([lower[i%nl],upper[j%nu],upper[(j-1)%nu]]);j-=1
  else:raise ValueError('No valid ordered seam path')
 seam=np.asarray(out,int);edges=np.unique(np.sort(np.vstack([seam[:,[0,1]],seam[:,[1,2]],seam[:,[2,0]]]),axis=1),axis=0)
 longest=float(np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1).max())
 sampling_edge=max(float(np.linalg.norm(np.roll(v[ring],-1,axis=0)-v[ring],axis=1).max()) for ring in (lower,upper))
 if longest>max_gap+sampling_edge:raise ValueError(f'Corresponding seam edge too long ({longest:.2f} mm > gap limit plus source sampling {max_gap+sampling_edge:.2f} mm); inspect alignment')
 return seam,{'lower_ring_vertices':nl,'upper_ring_vertices':nu,'maximum_nearest_ring_gap_mm':gap,'allowed_nearest_ring_gap_mm':float(max_gap),'longest_seam_edge_mm':longest,'maximum_source_ring_edge_mm':sampling_edge,'boundary_correspondence':'ordered cyclic dynamic programming; squared physical edge cost; no source boundary resampling'}

def triangles_intersect(a,b,tolerance=1e-9):
 """Triangle SAT including in-plane axes for coplanar triangles."""
 origin=(a.mean(0)+b.mean(0))/2;a=a-origin;b=b-origin
 ea=np.roll(a,-1,axis=0)-a;eb=np.roll(b,-1,axis=0)-b
 na=np.cross(ea[0],ea[1]);nb=np.cross(eb[0],eb[1])
 axes=np.vstack([na,nb,np.cross(ea[:,None,:],eb[None,:,:]).reshape(-1,3),np.cross(na,ea),np.cross(nb,eb)])
 lengths=np.linalg.norm(axes,axis=1);axes=axes[lengths>1e-12]/lengths[lengths>1e-12,None]
 pa=a@axes.T;pb=b@axes.T
 return not bool(np.any((pa.max(0)<pb.min(0)-tolerance)|(pb.max(0)<pa.min(0)-tolerance)))

def check_seam_intersections(v,seam):
 tri=v[seam];centers=tri.mean(1);r=np.linalg.norm(tri-centers[:,None,:],axis=2).max(1);tree=cKDTree(centers)
 boxes_min=tri.min(1);boxes_max=tri.max(1);tested=0
 for i in range(len(seam)):
  for j in tree.query_ball_point(centers[i],r[i]+r.max()+1e-8):
   if j<=i or np.any(boxes_max[i]<boxes_min[j]-1e-8) or np.any(boxes_max[j]<boxes_min[i]-1e-8):continue
   a,b=tri[i],tri[j]
   shared=np.intersect1d(seam[i],seam[j]).size
   if shared==2:
    normal=unit(np.cross(a[1]-a[0],a[2]-a[0]))
    # Non-coplanar triangles sharing an edge can only meet on that edge.
    # Treating that expected contact as a collision rejects skinny voxel faces.
    if np.max(np.abs((b-a[0])@normal))>1e-8:continue
   if shared:
    # Exclude expected boundary contact; center SAT for numerical stability.
    a=a.mean(0)+(a-a.mean(0))*(1-1e-4);b=b.mean(0)+(b-b.mean(0))*(1-1e-4)
   tested+=1
   if triangles_intersect(a,b,tolerance=1e-12 if shared else 1e-9):raise ValueError(f'Seam self-intersection between triangles {i} and {j}')
 return tested

def seam_vertex_fans(faces,seam_vertices):
    chosen=set(map(int,seam_vertices));near=faces[np.isin(faces,seam_vertices).any(1)];links={k:[] for k in chosen}
    for face in near:
        for j,node in enumerate(face):
            if int(node) in chosen:links[int(node)].append((int(face[(j+1)%3]),int(face[(j+2)%3])))
    for node,edges in links.items():
        graph={}
        for a,b in edges:graph.setdefault(a,[]).append(b);graph.setdefault(b,[]).append(a)
        if not graph or any(len(neighbors)!=2 for neighbors in graph.values()):raise ValueError('Non-manifold seam vertex: '+str(node))
        seen=set();stack=[next(iter(graph))]
        while stack:
            k=stack.pop()
            if k in seen:continue
            seen.add(k);stack.extend(graph[k])
        if len(seen)!=len(graph):raise ValueError('Pinched/disconnected seam vertex fan: '+str(node))
    return len(chosen)

def build(original_v,original_t,donor_v,donor_t,n,lower_h,width=4.,max_gap=15.,preserve_existing_boundary=False):
 n=unit(n)
 if not np.isfinite(lower_h) or not 0.5<=width<=15 or max_gap<width:raise ValueError('Transition width must be 0.5–15 mm and no larger than maximum ring gap')
 original_v=np.asarray(original_v,float);original_t=np.asarray(original_t,int);donor_v=np.asarray(donor_v,float);donor_t=np.asarray(donor_t,int)
 inherited,degree=boundary_anomalies(original_t,len(original_v))
 allowed=inherited if preserve_existing_boundary else np.array([],int)
 _,original_border=checked_topology(original_v,original_t,'original_source',allowed)
 # Original tagged scalp can have existing inferior boundary contacts. They
 # may be carried through only outside the repair ROI, with their full face
 # stars and every boundary edge unchanged. No welding/filling is performed.
 if len(allowed):
  clearance=lower_h-original_v[allowed]@n
  if np.any(clearance<10.):raise SurfaceTopologyError('original_boundary_near_cut','Existing boundary anomaly is within 10 mm of or above the cut; review the original surface / cut',{'minimum_clearance_mm':float(clearance.min())})
  if np.any(degree[allowed]<4) or np.any(degree[allowed]%2):raise SurfaceTopologyError('original_source','Unsupported original boundary degree')
 upper_h=lower_h+width
 lv,lt,lr,other_border,kept,whole=checked_clip(original_v,original_t,n,lower_h,True,'original_cut')
 # The unused lower donor surface is not part of the hybrid. Validate the
 # retained cap, so unrelated inferior boundary pinches do not reject it.
 uv,ut,ur,cap_holes,_,_=checked_clip(donor_v,donor_t,n,upper_h,False,'donor_cut')
 checked_topology(lv,lt,'original_retained',allowed)
 checked_topology(uv,ut,'donor_cap')
 if len(cap_holes):raise ValueError('Donor cap has an open boundary above the seam; image coverage is incomplete')
 if float((uv[np.unique(ut)]@n).max())<=upper_h+1:raise ValueError('Donor cap is too shallow; select a lower cut')
 # Compact only donor vertices outside the retained cap; original vertices stay exact.
 used=np.unique(ut);remap=np.full(len(uv),-1,int);remap[used]=np.arange(len(used));uv=uv[used];ut=remap[ut];ur=remap[ur]
 # The only boundaries retained on the original side must be the original neck / scan boundaries.
 before=set(map(tuple,np.sort(original_border,axis=1)));after=set(map(tuple,np.sort(other_border,axis=1)))
 if before!=after:raise ValueError('Cut intersects an existing original boundary; lower region cannot be preserved')
 vertices=np.vstack([lv,uv]);offset=len(lv);upper=ur+offset
 seam,ring_report=bridge(vertices,lr,upper,n,max_gap)
 faces=np.vstack([lt,ut+offset,seam]);summary,border=checked_topology(vertices,faces,'hybrid_joined',allowed)
 if len(allowed):
  final_bad,final_degree=boundary_anomalies(faces,len(vertices))
  if not np.array_equal(final_bad,allowed) or not np.array_equal(final_degree[allowed],degree[allowed]):raise ValueError('Original boundary anomaly set changed')
  original_star=original_t[np.isin(original_t,allowed).any(1)]
  final_star=faces[np.isin(faces,allowed).any(1)]
  if not np.array_equal(original_star,final_star):raise ValueError('Triangles incident to an inherited boundary anomaly changed')
 # Enforce exact incidence at every original/cap attachment edge.
 edges,count,_=edge_data(faces);lookup={tuple(e):int(k) for e,k in zip(edges,count)}
 for ring in (lr,upper):
  for a,b in zip(ring,np.roll(ring,-1)):
   if lookup.get(tuple(sorted((int(a),int(b)))))!=2:raise ValueError('Open seam attachment edge')
 if len(border)!=len(original_border):raise ValueError('Unexpected hole introduced by cap replacement')
 fan_count=seam_vertex_fans(faces,np.unique(seam))
 tests=check_seam_intersections(vertices,seam)
 # Original lower triangles and all original vertex coordinates must remain exactly unchanged.
 if not np.array_equal(vertices[:len(original_v)],original_v) or not np.array_equal(faces[:kept],original_t[whole]):raise AssertionError('Original lower geometry was modified')
 # Slab separation proves interior seam cannot intersect lower/cap triangles.
 if np.max(vertices[lt]@n)>lower_h+1e-6 or np.min(vertices[ut+offset]@n)<upper_h-1e-6:raise AssertionError('Half-space separation failed')
 report=dict(summary,**ring_report,original_vertices_unchanged=True,original_fully_retained_triangles=kept,
             inherited_boundary_anomalies=[{'vertex_index_0based':int(i),'RAS_mm':original_v[i].tolist(),'boundary_degree':int(degree[i]),'distance_below_cut_mm':float(lower_h-original_v[i]@n)} for i in allowed],
             inherited_boundary_face_stars_unchanged=True,boundary_policy='Existing original boundary contacts at least 10 mm below cut may be retained exactly; donor cap and new seam remain strict. This is not a globally manifold-surface repair.',
             original_boundary_edges_preserved=len(original_border),seam_triangles=int(len(seam)),seam_attachment_open_edges=0,
             seam_self_intersections=0,seam_contact_exclusion_fraction=1e-4,seam_SAT_tolerance_mm=1e-9,seam_nonmanifold_vertices=0,seam_vertices_checked=fan_count,seam_candidate_pairs_tested=tests,
             seam_intersection_scope='annulus self-intersection; original/cap separated from seam interior by cutting planes; source surfaces still require anatomical review',
             source_original_triangles=len(original_t),donor_cap_triangles=len(ut),lower_plane_h_mm=float(lower_h),upper_plane_h_mm=float(upper_h),normal_RAS=n.tolist())
 return vertices,faces,report,lr,upper,np.r_[np.zeros(len(lt),int),np.ones(len(ut),int),np.full(len(seam),2)]
