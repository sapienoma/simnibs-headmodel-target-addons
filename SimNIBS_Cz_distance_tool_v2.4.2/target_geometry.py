# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Individual scalp cross-section distances. Not population MNI2CPC mapping."""
from ui_language import tr
import csv
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra,connected_components
from scipy.spatial import cKDTree
from scalp_arcs_legacy import project

def unit(a):
    a=np.asarray(a,float);n=np.linalg.norm(a)
    if n<1e-9:raise ValueError(tr('Collinear landmarks or a polar target do not define a unique measurement plane.'))
    return a/n

def plane(a,b,c):return unit(np.cross(np.asarray(b)-a,np.asarray(c)-a)),np.asarray(a)

def section(v,tri,normal,origin):
    ds=(v-origin)@unit(normal);ds[np.abs(ds)<1e-8]=0
    buf={};coplanar=[]
    for a,b in ((0,1),(1,2),(2,0)):
        ia=tri[:,a];ib=tri[:,b];da=ds[ia];db=ds[ib]
        mask=(da*db<0)|((da==0)&(db!=0))|((db==0)&(da!=0))
        idx=np.flatnonzero(mask);aa=ia[idx];bb=ib[idx];t=ds[aa]/(ds[aa]-ds[bb]);q=v[aa]+t[:,None]*(v[bb]-v[aa])
        for i,pt in zip(idx,q):buf.setdefault(i,[]).append(pt)
        both=(da==0)&(db==0)
        if both.any():coplanar.extend(np.stack([v[ia[both]],v[ib[both]]],axis=1))
    out=list(coplanar)
    for pts in buf.values():
        q=np.unique(np.round(pts,8),axis=0)
        if len(q)==2:out.append(q)
    if not out:raise ValueError(tr('Measurement plane does not intersect the scalp.'))
    seg=np.asarray(out);seg=seg[np.linalg.norm(seg[:,1]-seg[:,0],axis=1)>1e-7]
    return seg

class Curve:
    def __init__(self,segments):
        nodes,ix=np.unique(np.round(segments.reshape(-1,3),8),axis=0,return_inverse=True)
        # Weld near-identical edge intersections by distance, not a rounding grid;
        # a grid alone can split connected vertices after rotating the mesh.
        parent=np.arange(len(nodes))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        for a,b in cKDTree(nodes).query_pairs(1e-5):parent[find(b)]=find(a)
        roots=np.array([find(i) for i in range(len(nodes))]);unique,mapping=np.unique(roots,return_inverse=True)
        welded=np.zeros((len(unique),3));np.add.at(welded,mapping,nodes);welded/=np.bincount(mapping)[:,None]
        nodes=welded;ix=mapping[ix]
        edges=np.unique(np.sort(ix.reshape(-1,2),axis=1),axis=0);edges=edges[edges[:,0]!=edges[:,1]]
        if not len(edges):raise ValueError(tr('Empty scalp intersection curve.'))
        self.nodes=nodes;self.edges=edges;self.a=nodes[edges[:,0]];self.e=nodes[edges[:,1]]-self.a
        self.seg=np.stack([self.a,self.a+self.e],axis=1)
    def nearest(self,p):
        u=np.clip(((np.asarray(p)-self.a)*self.e).sum(1)/(self.e*self.e).sum(1),0,1)
        q=self.a+u[:,None]*self.e;d=np.linalg.norm(q-p,axis=1);i=int(d.argmin());return i,q[i],float(d[i])
    def path(self,start,end,tolerance=3.):
        i,s,ds=self.nearest(start);j,t,dt=self.nearest(end)
        if max(ds,dt)>tolerance:raise ValueError(tr(f'Reference point too far from section curve ({max(ds, dt):.2f} mm); check landmarks.'))
        if np.linalg.norm(s-t)<1e-6:return np.array([s,t]),max(ds,dt)
        n=len(self.nodes);nodes=np.vstack([self.nodes,s,t]);edges=self.edges.tolist()
        edges += [[n,int(x)] for x in self.edges[i]]+[[n+1,int(x)] for x in self.edges[j]]
        if i==j:edges.append([n,n+1])
        edges=np.asarray(edges);lengths=np.linalg.norm(nodes[edges[:,0]]-nodes[edges[:,1]],axis=1)
        graph=coo_matrix((np.r_[lengths,lengths],(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(n+2,n+2)).tocsr()
        distance,prev=dijkstra(graph,indices=n,return_predecessors=True)
        if not np.isfinite(distance[n+1]):raise ValueError(tr('Disconnected intersection curve; cannot report a tape distance.'))
        route=[n+1]
        while route[-1]!=n:
            route.append(int(prev[route[-1]]))
            if len(route)>n+3:raise ValueError(tr('Invalid section path.'))
        return nodes[route[::-1]],max(ds,dt)
    def through(self,a,via,b,tolerance=3.):
        p,d1=self.path(a,via,tolerance);q,d2=self.path(via,b,tolerance)
        return np.vstack([p,q[1:]]),max(d1,d2)

def arc_length(path):return float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum())
def arc_coordinate(path,p,tolerance=3.):
    a=path[:-1];e=np.diff(path,axis=0);lens=np.linalg.norm(e,axis=1);good=lens>1e-8
    a=a[good];e=e[good];lens=lens[good]
    if not len(lens):return 0.,0.
    u=np.clip(((np.asarray(p)-a)*e).sum(1)/(lens*lens),0,1);q=a+u[:,None]*e;dist=np.linalg.norm(q-p,axis=1);i=dist.argmin()
    if dist[i]>tolerance:raise ValueError(tr('Point is outside the reference arc.'))
    return float(lens[:i].sum()+u[i]*lens[i]),float(dist[i])
def crossings(segments,normal,origin):
    d=(segments-origin)@normal;found=[]
    for seg,(da,db) in zip(segments,d):
        if abs(da)<1e-7:found.append(seg[0])
        if da*db<0:found.append(seg[0]+da/(da-db)*(seg[1]-seg[0]))
        if abs(db)<1e-7:found.append(seg[1])
    if not found:raise ValueError(tr('Reference curves do not intersect.'))
    return np.unique(np.round(found,6),axis=0)

class TargetModel:
    def __init__(self,v,tri,marks):
        self.v=np.asarray(v,float);self.tri=np.asarray(tri,int);self.m={k:np.asarray(a,float) for k,a in marks.items()}
        for k in ('Cz','Nz','Iz','LPA','RPA'):
            if k not in self.m:raise ValueError(tr('EEG CSV missing ')+k)
        self.cz=self.m['Cz'];self.lr=unit(self.m['RPA']-self.m['LPA'])
        self.ap=unit((self.m['Nz']-self.m['Iz'])-self.lr*np.dot(self.m['Nz']-self.m['Iz'],self.lr));self.up=unit(np.cross(self.lr,self.ap))
        self.mid_n,self.mid_o=plane(self.m['Nz'],self.cz,self.m['Iz'])
        self.mid=self.cut(self.mid_n,self.mid_o)
        self.ni_path,_=self.mid.through(self.m['Nz'],self.cz,self.m['Iz'])
        self.ni=arc_length(self.ni_path);self.cz_arc=arc_coordinate(self.ni_path,self.cz)[0]
    @classmethod
    def from_files(cls,mesh_path,csv_path):
        from repair_assets import read_surface, read_positions
        _,v,tri,_ = read_surface(mesh_path)
        marks = read_positions(csv_path)
        return cls(v,tri,marks)
    def cut(self,n,o):return Curve(section(self.v,self.tri,n,o))
    def project(self,p):
        p=np.asarray(p,float)
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError(tr('Coordinates must be three finite numbers.'))
        d,q,_=project(self.v,self.tri,p);return q,float(np.sqrt(d))
    def cz_lateral_first(self,s):
        first=self.cut(self.ap,self.cz);second=self.cut(self.lr,s)
        pts=crossings(first.seg,self.lr,s);q=pts[np.argmax(pts@self.up)]
        a,da=first.path(self.cz,q);b,db=second.path(q,s)
        return dict(lateral_mm=arc_length(a),lateral_direction='right' if np.dot(q-self.cz,self.lr)>=0 else 'left',
                    fore_mm=arc_length(b),fore_direction='toward nose' if np.dot(s-q,self.ap)>=0 else 'toward occiput',
                    via=q.tolist(),paths=[a.tolist(),b.tolist()],offset_mm=max(da,db),definition='Cz lateral first, then parasagittal; orthogonal anatomical axes')
    def sgp(self,s):
        n,o=plane(self.m['LPA'],self.m['RPA'],s);active=self.cut(n,o)
        pts=crossings(self.mid.seg,n,o);q=pts[np.argmax(pts@self.up)]
        nz_distance,d1=arc_coordinate(self.ni_path,q)
        al_path,d2=active.path(self.m['LPA'],s);ar_path,d3=active.path(s,self.m['RPA'])
        al=arc_length(al_path);ar=arc_length(ar_path);total=al+ar
        if total<1e-6:raise ValueError(tr('Preauricular reference arc has zero length.'))
        p_nz=nz_distance/self.ni;p_al=al/total
        if not 0<=p_nz<=1 or not 0<=p_al<=1:raise ValueError(tr('Point is outside the upper-scalp SGP coverage.'))
        return dict(pNZ=p_nz,pAL=p_al,NI_mm=self.ni,Nz_to_intersection_mm=nz_distance,
                    Cz_to_intersection_mm=abs(nz_distance-self.cz_arc),fore_direction='toward nose' if nz_distance<self.cz_arc else 'toward occiput',
                    AL_to_target_mm=al,AR_to_target_mm=ar,AL_target_AR_mm=total,
                    intersection=q.tolist(),offset_mm=max(d1,d2,d3),paths=[self.ni_path.tolist(),al_path.tolist(),ar_path.tolist()],
                    definition='Individual CPC/SGP geometry (Jiang 2022); NOT population MNI2CPC lookup')
    def beam_style(self,s):
        for k in ('Fpz','Oz'):
            if k not in self.m:raise ValueError(tr('BEAM-style requires EEG landmark ')+k)
        landmarks=np.array([self.m[k] for k in ('Fpz','Oz')]);o=landmarks.mean(0)
        n=unit(np.cross(self.mid_n,self.m['Oz']-self.m['Fpz']))
        if np.dot(n,self.up)<0:n=-n
        if np.dot(s-o,n)<-2:raise ValueError(tr('Target is below the head-circumference plane; BEAM-style not applicable.'))
        hc=self.cut(n,o);center=self.cz-n*np.dot(self.cz-o,n)
        radial=(s-center)-n*np.dot(s-center,n)
        if np.linalg.norm(radial)<1e-6:radial=(self.m['Fpz']-center)-n*np.dot(self.m['Fpz']-center,n)
        mer_n=unit(np.cross(self.cz-center,radial));mer=self.cut(mer_n,self.cz)
        choices=crossings(hc.seg,mer_n,self.cz);foot=choices[np.argmax((choices-center)@unit(radial))]
        # Follow the outer head circumference component nearest Fpz, reject branches.
        fp_idx,fp,fp_offset=hc.nearest(self.m['Fpz']);x_path,xd=hc.path(fp,foot,tolerance=15.)
        # Full loop length of the same component, no arbitrary disconnected parts.
        edges=hc.edges;weights=np.linalg.norm(hc.e,axis=1)
        graph=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(hc.nodes),len(hc.nodes))).tocsr()
        _,labels=connected_components(graph,directed=False);component=labels[edges[fp_idx,0]]
        if labels[edges[hc.nearest(foot)[0],0]]!=component:raise ValueError(tr('Circumference footpoint is in a different component.'))
        mask=labels[edges[:,0]]==component
        degree=np.bincount(edges[mask].ravel(),minlength=len(hc.nodes));active_nodes=np.unique(edges[mask])
        if not np.all(degree[active_nodes]==2):raise ValueError(tr('Circumference section is not one closed loop; HC cannot be measured reliably.'))
        hc_length=float(weights[mask].sum())
        y_path,yd=mer.path(self.cz,s)
        # Ensure target lies on the Cz -> foot arc, rather than the lower head.
        whole,_=mer.through(self.cz,s,foot);radial_total=arc_length(whole)
        x=arc_length(x_path);y=arc_length(y_path)
        tt_normal,tt_origin=plane(self.m['LPA'],self.cz,self.m['RPA'])
        tt_path,_=self.cut(tt_normal,tt_origin).through(self.m['LPA'],self.cz,self.m['RPA'])
        # Published 2015 mean proportions, NOT the exact Beam-F3 algorithm.
        reference={'X_mm':.1154*hc_length,'Y_mm':.2637*(self.ni+arc_length(tt_path))/2,
                   'kind':'approximate mean-proportion F3 reference only',
                   'source':'Mir-Moghtadaei et al. 2015; https://pmc.ncbi.nlm.nih.gov/articles/PMC4833442/'}
        return dict(X_mm=x,Y_mm=y,HC_mm=hc_length,X_percent=100*x/hc_length,
                    side='right' if np.dot(s-self.cz,self.lr)>=0 else 'left',foot=foot.tolist(),F3_mean_proportion_reference=reference,
                    HC_landmark_max_plane_residual_mm=float(np.max(np.abs((landmarks-o)@n))),
                    Fpz_curve_offset_mm=fp_offset,endpoint_offset_mm=max(xd,yd),
                    paths=[x_path.tolist(),y_path.tolist()],definition='Generalized individual BEAM-style X/Y; HC Fpz/Oz plane perpendicular to sagittal reference plane; not original Beam F3 prediction')
    def from_cpc(self,pnz,pal):
        if not (0<pnz<1 and 0<pal<1):raise ValueError(tr('CPC proportions must be between 0 and 1, not percentages.'))
        q=point_on_path(self.ni_path,pnz*self.ni)
        n,o=plane(self.m['LPA'],self.m['RPA'],q)
        active=self.cut(n,o);path,_=active.through(self.m['LPA'],q,self.m['RPA'])
        return point_on_path(path,pal*arc_length(path))
    def measure(self,p):
        s,offset=self.project(p);out=dict(scalp=s.tolist(),input=np.asarray(p).tolist(),projection_distance_mm=offset,methods={},errors={})
        for name,method in [('Cz_lateral_first',self.cz_lateral_first),('BEAM_style',self.beam_style),('SGP',self.sgp)]:
            try:out['methods'][name]=method(s)
            except (ValueError,IndexError,FloatingPointError) as e:out['errors'][name]=str(e)
        return out

def point_on_path(path,distance):
    lengths=np.linalg.norm(np.diff(path,axis=0),axis=1);cum=np.r_[0,np.cumsum(lengths)]
    distance=float(np.clip(distance,0,cum[-1]));i=min(int(np.searchsorted(cum,distance,side='right')-1),len(lengths)-1)
    if lengths[i]<1e-8:return path[i].copy()
    return path[i]+(distance-cum[i])/lengths[i]*(path[i+1]-path[i])
