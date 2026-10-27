# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Hybrid scalp workflow. Runs in the installed SimNIBS Python (no private deps)."""
import argparse,csv,json,subprocess,sys,time
from pathlib import Path
import numpy as np
from repair_assets import digest,read_surface,read_positions,nearest,FIDUCIALS,validate_pair,bind,select_components,unchanged_local_patch
from hybrid_geometry import build,unit,checked_topology,boundary_anomalies

def read_donor(path,audit=None):
 path=Path(path)
 if path.suffix.lower()!='.ply':
  _,v,t,_=read_surface(path,audit=audit);return v,t
 with path.open(encoding='ascii') as f:
  if f.readline().strip()!='ply' or f.readline().strip()!='format ascii 1.0':raise ValueError('Expected ASCII reviewed PLY or scalp MSH')
  nv=nf=None
  for line in f:
   if line.startswith('element vertex '):nv=int(line.split()[-1])
   if line.startswith('element face '):nf=int(line.split()[-1])
   if line.strip()=='end_header':break
  if not nv or not nf:raise ValueError('Empty donor surface')
  v=np.array([list(map(float,f.readline().split())) for _ in range(nv)]);raw=np.array([list(map(int,f.readline().split())) for _ in range(nf)])
 if v.shape!=(nv,3) or raw.shape!=(nf,4) or not np.all(raw[:,0]==3):raise ValueError('Invalid donor PLY')
 t=raw[:,1:]
 if t.min()<0 or t.max()>=len(v) or not np.isfinite(v).all():raise ValueError('Invalid donor vertices')
 from scalp_repair.surface_cleanup import clean_surface
 v,t,cleanup=clean_surface(v,t);keep,components=select_components(v,t);t=t[keep]
 if audit is not None:audit.update(triangle_cleanup=cleanup,components=components)
 a,b,c=v[t[:,0]],v[t[:,1]],v[t[:,2]]
 if np.sum(np.einsum('ij,ij->i',np.cross(b-a,c-a),(a+b+c)/3-v[np.unique(t)].mean(0)))<0:t=t[:,::-1]
 return v,t

def cutting_plane(v,work,cut_z,width):
 if cut_z is not None:return np.array([0.,0.,1.]),float(cut_z),{'method':'manual RAS Z lower cut'}
 work=Path(work) if work else None
 if work is None or not (work/'manifest.json').is_file():raise ValueError('Automatic cut requires the reviewed repair manifest; otherwise enter lower cut RAS Z')
 m=json.loads((work/'manifest.json').read_text(encoding='utf-8'));meta=m['T1'];aff=np.array(meta[meta.get('selected_form','qform')],float)
 directions=aff[:3,:3]/np.linalg.norm(aff[:3,:3],axis=0);axis=int(np.argmax(abs(directions[2])));sign=np.sign(directions[2,axis]);n=unit(directions[:,axis]*sign)
 if n[2]<.85:raise ValueError('Automatic superior cut requires near-axial T1; use an explicit RAS Z cut')
 i=meta['shape'][axis]-.5 if sign>0 else -.5;point=aff[:3,3]+aff[:3,axis]*i;fov=float(point@n)
 lower=min(fov-8.,float((v@n).max())-8.)
 return n,lower,{'method':'8 mm below T1 superior FOV / original surface maximum, whichever lower','T1_superior_plane_h_mm':fov,'transition_width_mm':width}

def write_msh(path,v,t):
 # 17 significant digits round-trip original double coordinates without moving them.
 with open(path,'w',encoding='ascii') as f:
  f.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n'+str(len(v))+'\n')
  for i,p in enumerate(v,1):f.write(str(i)+' '+' '.join(format(float(x),'.17g') for x in p)+'\n')
  f.write('$EndNodes\n$Elements\n'+str(len(t))+'\n')
  for i,p in enumerate(t+1,1):f.write(f'{i} 2 2 1005 1005 {p[0]} {p[1]} {p[2]}\n')
  f.write('$EndElements\n')

def write_geo(path,v,lo,hi):
 with open(path,'w',encoding='ascii') as f:
  f.write('View "Hybrid seam rings - original lower / donor upper" {\n')
  for value,ring in [(1,lo),(2,hi)]:
   for a,b in zip(ring,np.roll(ring,-1)):
    f.write('SL('+','.join(format(float(x),'.17g') for x in np.r_[v[a],v[b]])+'){'+str(value)+','+str(value)+'};\n')
  f.write('};\n')

def preview(out,v,t,labels,lo,hi):
 try:
  import matplotlib;matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  from matplotlib.collections import PolyCollection
  from matplotlib.colors import to_rgb
  fig,axes=plt.subplots(1,2,figsize=(12,6));center=v[np.unique(t)].mean(0)
  triangles=v[t];normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-15)
  colors=np.array([to_rgb('#b6c6d8'),to_rgb('#4bad88'),to_rgb('#e99a35')])[labels]
  for ax,(view,title) in zip(axes,[(unit([.9,-.7,.4]),'Oblique'),(np.array([1.,0,0]),'Side')]):
   right=unit(np.cross([0,0,1.],view));up=np.cross(view,right)
   xy=np.column_stack([(v-center)@right,(v-center)@up]);depth=(triangles.mean(1)-center)@view
   visible=np.flatnonzero(normal@view>0);visible=visible[np.argsort(depth[visible])]
   light=unit(view+[0,0,.8]);shade=.55+.45*np.maximum(0,normal[visible]@light)
   polygons=PolyCollection(xy[t[visible]],facecolors=colors[visible]*shade[:,None],edgecolors='none',linewidths=0,antialiaseds=False,rasterized=True)
   ax.add_collection(polygons);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('Projected horizontal (mm)');ax.set_ylabel('Projected superior (mm)')
  fig.suptitle('HYBRID REVIEW: blue original, green donor cap, orange seam\nOrthographic full-mesh rendering; localization surface, not volume FEM.')
  fig.tight_layout(rect=(0,0,1,.91));fig.savefig(out/'hybrid_preview.png',dpi=140,bbox_inches='tight');plt.close(fig)
 except ImportError:pass


def run(original,donor,out,work=None,cut_z=None,width=4.,fidcsv=None,bind_m2m=None):
 out=Path(out).resolve()
 if out.exists() and any(out.iterdir()):raise ValueError('Hybrid output must be new or empty')
 out.mkdir(parents=True,exist_ok=True);record={'version':'1.80.2','status':'RUNNING','FEM':False,'surface_kind':'hybrid',
  'original_MSH':str(Path(original).resolve()),'original_MSH_sha256':digest(original),'donor':str(Path(donor).resolve()),'donor_sha256':digest(donor)}
 def save(): (out/'hybrid_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
 save()
 try:
  if work:
   manifest=Path(work)/'manifest.json'
   m=json.loads(manifest.read_text(encoding='utf-8'));review=m.get('user_review',{})
   if not review:raise ValueError('Export and review the donor surface before hybrid stitching')
   if Path(donor).suffix.lower()=='.ply' and digest(donor)!=review.get('surface_sha256'):raise ValueError('Donor PLY differs from reviewed surface; export again')
   record['repair_manifest_sha256']=digest(manifest)
   pipeline=Path(original).resolve().parent.parent/'pipeline_state.json'
   if pipeline.is_file():
    state=json.loads(pipeline.read_text(encoding='utf-8'));source_hash=state.get('signature',{}).get('T1',{}).get('sha256')
    if source_hash and source_hash!=m['T1'].get('sha256'):raise ValueError('Original Builder m2m and donor repair use different T1 source hashes; check subject / acquisition')
    record['Builder_T1_source_hash_match']=bool(source_hash)
   else:record['Builder_T1_source_hash_match']=None
  print('Reading original m2m scalp and reviewed donor cap',flush=True)
  from simnibs import mesh_io
  source_volume=mesh_io.read_msh(str(original))
  if not np.any(source_volume.elm.elm_type==4):raise ValueError('Original input must be the original m2m volume FEM, not a scalp-only MSH')
  _,ov,ot,_=read_surface(original,reference_only=True);donor_audit={};dv,dt=read_donor(donor,donor_audit);record['donor_preprocessing']=donor_audit
  # Source defects do not depend on cut height: diagnose once, before searching.
  inherited,_=boundary_anomalies(ot,len(ov))
  checked_topology(ov,ot,'original_source',inherited)
  record['original_boundary_anomaly_count']=int(len(inherited))
  if len(inherited):print('Original scalp has '+str(len(inherited))+' existing boundary contacts. Each candidate must preserve them and all incident faces exactly, at least 10 mm below the cut.',flush=True)
  n,h,cutinfo=cutting_plane(ov,work,cut_z,width)
  print('Hybrid lower cut: normal RAS '+str(n.tolist())+'; h='+str(h)+' mm; transition='+str(width)+' mm',flush=True)
  attempts=[]
  offsets=[0.] if cut_z is not None else [0.,-1.,-2.,-3.,-4.,-6.,-8.,-10.,-12.]
  for offset in offsets:
   candidate=h+offset
   try:
    v,t,q,lo,hi,groups=build(ov,ot,dv,dt,n,candidate,width,max_gap=max(15.,width+8.),preserve_existing_boundary=True)
    attempts.append({'lower_h_mm':candidate,'status':'passed'});break
   except ValueError as e:
    attempts.append({'lower_h_mm':candidate,'status':'rejected','reason':str(e),'details':getattr(e,'details',{})})
    print('Cut rejected at h='+str(candidate)+': '+str(e),flush=True)
  else:
   record['cut_attempts']=attempts;save()
   raise ValueError('No valid local superior seam. Review the donor / original surfaces or set a manual cut. Last error: '+attempts[-1]['reason'])
  record['cut_attempts']=attempts;cutinfo['selected_lower_h_mm']=candidate
  cutinfo['automatic_downward_search_limit_mm']=12.0 if cut_z is None else 0.0
  mesh=out/'hybrid_scalp_ONLY.msh';write_msh(mesh,v,t);write_geo(out/'hybrid_seam.geo',v,lo,hi)
  record.update(status='GEOMETRY_CHECKED_REQUIRES_REVIEW',cut=cutinfo,seam_quality=q,surface=str(mesh),surface_sha256=digest(mesh));save()
  preview(out,v,t,groups,lo,hi)
  import html
  (out/'hybrid_report.html').write_text('<!doctype html><meta charset="utf-8"><title>Hybrid scalp v1.80.2</title><style>body{font:17px sans-serif;max-width:1100px;margin:30px auto}img{max-width:100%}pre{white-space:pre-wrap}</style><h1>Hybrid scalp — geometry review required</h1><p>Blue: original lower scalp; green: donor cap; orange: new seam. Source FEM unchanged. Review cap anatomy, cut height and seam in MRI / Gmsh before using this localization surface.</p>'+('<img src="hybrid_preview.png">' if (out/'hybrid_preview.png').is_file() else '')+'<p>Preview renders all visible faces; geometry tests use all faces. Source surfaces were not globally screened for self-intersection.</p><pre>'+html.escape(json.dumps(q,indent=2))+'</pre><p>Open hybrid_scalp_ONLY.msh with hybrid_seam.geo to inspect exact rings.</p>',encoding='utf-8')
  if not fidcsv:raise ValueError('Geometry generated, but fiducial CSV is required to recompute hybrid EEG before use')
  points=read_positions(fidcsv,required_names=FIDUCIALS);projected={};offsets={};inherited_fiducials=[]
  from hybrid_geometry import edge_data
  edges,count,_=edge_data(t);boundary=v[np.unique(edges[count==1])]
  for name in FIDUCIALS:
   p,d=nearest(v,t,points[name]);offsets[name]=d
   if d>5:raise ValueError(f'{name} is {d:.2f} mm from hybrid scalp; review anatomical fiducial position')
   if len(boundary) and np.linalg.norm(boundary-p,axis=1).min()<5:
    if unchanged_local_patch(v,t,p,(ov,ot)):
     inherited_fiducials.append(name);print(name+': retaining original near-boundary fiducial; surrounding 10 mm triangle patch verified unchanged.',flush=True)
    else:raise ValueError(name+' is too close to a changed/new boundary')
   projected[name]=p
  prefix=out/'EEG10-10_hybrid';args=[sys.executable,'-u','-m','simnibs.cli.eeg_positions','-m',str(mesh),'-o',str(prefix)]
  for name in FIDUCIALS:args+=['-'+name,*map(str,projected[name])]
  record.update(status='RECOMPUTING_EEG',fiducial_projection_mm=offsets,inherited_boundary_fiducials=inherited_fiducials,EEG_command=args,fiducial_csv_sha256=digest(fidcsv));save()
  subprocess.run(args,check=True)
  cap=prefix.with_suffix('.csv');_,new,validation=validate_pair(mesh,cap,original_reference=(ov,ot))
  with (out/'EEG_coordinate_changes.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(['name','old_x','old_y','old_z','new_x','new_y','new_z','displacement_mm'])
   for name,p in new.items():
    old=points.get(name);w.writerow([name,*(['','',''] if old is None else old),*p,'' if old is None else float(np.linalg.norm(p-old))])
  record.update(status='COMPUTED_REQUIRES_VISUAL_REVIEW',EEG_csv=str(cap),EEG_csv_sha256=digest(cap),EEG_validation=validation,Cz_RAS_mm=new['Cz'].tolist());save()
  if digest(original)!=record['original_MSH_sha256'] or digest(donor)!=record['donor_sha256']:raise ValueError('Source mesh changed during hybrid construction; rerun with stable inputs')
  if bind_m2m:
   from repair_assets import find_fem
   if find_fem(bind_m2m).resolve()!=Path(original).resolve():raise ValueError('Selected original MSH is not the simulation FEM selected by this m2m folder')
   if Path(original).resolve().parent!=Path(bind_m2m).resolve():raise ValueError('Import target m2m must be the original mesh folder')
   binding=bind(bind_m2m,mesh,cap,surface_kind='hybrid',provenance={'hybrid_manifest_sha256':digest(out/'hybrid_manifest.json'),'seam_quality':q})
   record['binding_imported']=True;record['binding_m2m']=str(Path(bind_m2m).resolve());save()
  print('Hybrid scalp / seam checks / EEG completed: '+str(out),flush=True)
 except Exception as e:
  details=getattr(e,'details',{}) or next((a.get('details',{}) for a in reversed(record.get('cut_attempts',[])) if a.get('details')), {})
  record.update(status='FAILED_DO_NOT_USE',error=str(e),error_details=details);save()
  if details:
   diagnostic=out/'topology_diagnostics.json';diagnostic.write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
   with (out/'topology_boundary_vertices.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['stage','vertex_index_0based','RAS_x_mm','RAS_y_mm','RAS_z_mm','boundary_degree'])
    for row in details.get('boundary_vertices',[]):w.writerow([details['stage'],row['vertex_index_0based'],*row['RAS_mm'],row['boundary_degree']])
   print('Topology diagnostic: '+str(diagnostic),flush=True)
   if details.get('stage')=='original_source':
    print('Original scalp topology failed before cutting. Changing cut height cannot fix this source check. Inspect topology_boundary_vertices.csv against the original m2m scalp; no FEM was modified.',flush=True)
  raise
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--original',required=True);p.add_argument('--donor',required=True);p.add_argument('--output',required=True);p.add_argument('--work');p.add_argument('--cut-z',type=float);p.add_argument('--width',type=float,default=4.);p.add_argument('--fiducials',required=True);p.add_argument('--bind-m2m')
 a=p.parse_args();run(a.original,a.donor,a.output,a.work,a.cut_z,a.width,a.fiducials,a.bind_m2m)
