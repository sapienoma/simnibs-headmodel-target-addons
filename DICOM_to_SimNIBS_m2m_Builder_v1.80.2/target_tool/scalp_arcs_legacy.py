# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Cz -> longitudinal scalp arc -> transverse scalp arc. Units: mm."""
import csv
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
def section(v,tri,normal,origin):
 ds=(v-origin)@normal;out=[]
 for pair in [(0,1),(1,2),(2,0)]:
  ia=tri[:,pair[0]];ib=tri[:,pair[1]];hit=(ds[ia]*ds[ib]<0)
  # collect per triangle
  aa=ia[hit];bb=ib[hit];u=ds[aa]/(ds[aa]-ds[bb]);points=v[aa]+u[:,None]*(v[bb]-v[aa]);out.append((np.flatnonzero(hit),points))
 buf={}
 for inds,pts in out:
  for i,pt in zip(inds,pts):buf.setdefault(i,[]).append(pt)
 return np.array([pts for pts in buf.values() if len(pts)==2])
def curve_distance(seg,start,end):
 coords,inv=np.unique(np.round(seg.reshape(-1,3),6),axis=0,return_inverse=True);edges=inv.reshape(-1,2).tolist();pts=coords.tolist();snaps=[]
 for target in [start,end]:
  a=seg[:,0];e=seg[:,1]-a;u=np.clip(((target-a)*e).sum(1)/(e*e).sum(1),0,1);proj=a+u[:,None]*e;i=np.argmin(((proj-target)**2).sum(1));point=proj[i];idx=len(pts);pts.append(point.tolist());edges.extend([[idx,int(inv.reshape(-1,2)[i,0])],[idx,int(inv.reshape(-1,2)[i,1])]]);snaps.append((idx,point,np.linalg.norm(point-target)))
 pts=np.array(pts);edges=np.array(edges);L=np.linalg.norm(pts[edges[:,0]]-pts[edges[:,1]],axis=1);g=coo_matrix((np.r_[L,L],(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(pts),len(pts))).tocsr();d,pre=dijkstra(g,indices=snaps[0][0],return_predecessors=True)
 return d[snaps[1][0]],snaps
def project(v,tri,p):
 a,b,c=v[tri[:,0]],v[tri[:,1]],v[tri[:,2]]; ab=b-a;ac=c-a;ap=p-a
 aa=(ab*ab).sum(1);bb=(ab*ac).sum(1);cc=(ac*ac).sum(1);dd=(ap*ab).sum(1);ee=(ap*ac).sum(1);den=aa*cc-bb*bb
 u=(dd*cc-ee*bb)/den;w=(ee*aa-dd*bb)/den
 q=a+u[:,None]*ab+w[:,None]*ac; valid=(u>=0)&(w>=0)&(u+w<=1)
 dist=((q-p)**2).sum(1);dist[~valid]=np.inf;i=dist.argmin();best=(dist[i],q[i],i)
 for x,y in [(a,b),(b,c),(c,a)]:
  e=y-x;z=np.clip(((p-x)*e).sum(1)/(e*e).sum(1),0,1);q=x+z[:,None]*e;dist=((q-p)**2).sum(1);i=dist.argmin()
  if dist[i]<best[0]:best=(dist[i],q[i],i)
 return best

class ScalpModel:
    def __init__(self,mesh_path,csv_path):
        from simnibs import mesh_io
        mesh=mesh_io.read_msh(str(mesh_path)).crop_mesh(tags=1005,elm_type=2)
        self.v=np.asarray(mesh.nodes.node_coord)
        self.tri=np.asarray(mesh.elm.node_number_list[:,:3],dtype=int)-1
        self.initialize(csv_path)
    @classmethod
    def from_arrays(cls,v,tri,csv_path):
        obj=cls.__new__(cls);obj.v=v;obj.tri=tri;obj.initialize(csv_path);return obj
    def initialize(self,csv_path):
        with open(csv_path,encoding='utf-8-sig') as f:
            marks={r[-1].strip():np.array(r[1:4],float) for r in csv.reader(f) if len(r)>=5}
        self.cz=marks['Cz']; self.lr=marks['RPA']-marks['LPA'];self.lr/=np.linalg.norm(self.lr)
        self.ap=marks['Nz']-marks['Iz'];self.ap-=self.lr*np.dot(self.ap,self.lr);self.ap/=np.linalg.norm(self.ap)
        self.up=np.cross(self.lr,self.ap);self.up/=np.linalg.norm(self.up)
        self.vertical=section(self.v,self.tri,self.lr,self.cz)
    def calculate(self,current):
        raw=np.asarray(current,float);offset,cur,_=project(self.v,self.tri,raw);offset=float(np.sqrt(offset))
        if offset>2:raise ValueError('Current point is >2 mm from scalp. Select Scalp, then click the surface.')
        h=section(self.v,self.tri,self.ap,cur)
        if len(h)==0:raise ValueError('No transverse scalp intersection.')
        mid=(h-self.cz)@self.lr;hit=mid[:,0]*mid[:,1]<=0;hh=h[hit];dd=mid[hit]
        if not len(hh):raise ValueError('No intersection with Cz longitudinal plane.')
        good=np.abs(dd[:,0]-dd[:,1])>1e-12;hh=hh[good];dd=dd[good]
        qq=hh[:,0]+(dd[:,0]/(dd[:,0]-dd[:,1]))[:,None]*(hh[:,1]-hh[:,0])
        if not len(qq):raise ValueError('Degenerate plane intersection; choose a nearby point.')
        q=qq[np.argmax(qq@self.up)]
        fore,sf=curve_distance(self.vertical,self.cz,q)
        lateral,sl=curve_distance(h,q,cur)
        deviations=[x[2] for x in sf+sl]
        if not np.isfinite(fore+lateral):raise ValueError('Disconnected scalp cross-section; cannot measure this route.')
        if max(deviations)>2:raise ValueError('Endpoints >2 mm from section curve; inspect scalp mesh.')
        return dict(current=raw.tolist(),projected=cur.tolist(),cz=self.cz.tolist(),via=q.tolist(),
                    fore_mm=float(fore),lateral_mm=float(lateral),total_mm=float(fore+lateral),
                    fore_direction='toward nose' if np.dot(q-self.cz,self.ap)>=0 else 'toward occiput',
                    lateral_direction='right' if np.dot(cur-q,self.lr)>=0 else 'left',
                    scalp_offset_mm=offset,section_offset_mm=float(max(deviations)))
