# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Bind a reviewed localization surface/cap to an unchanged volume FEM.

No surface triangles are spliced into the FEM. Paths in the binding are relative
to the m2m folder; hashes detect stale/replaced source geometry.
"""
import csv, hashlib, json, shutil, time, uuid
from pathlib import Path
import numpy as np

REQUIRED = ('Cz', 'Nz', 'Iz', 'LPA', 'RPA')
FIDUCIALS = ('Nz', 'Iz', 'LPA', 'RPA')

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()

def read_positions(path,required_names=REQUIRED):
    groups = {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        for line, row in enumerate(csv.reader(f), 1):
            if len(row) < 5 or row[0].strip() not in ('Electrode','ReferenceElectrode','Fiducial','Generic'): continue
            name = row[4].strip()
            p = np.asarray(row[1:4], float)
            if not name or not np.isfinite(p).all(): raise ValueError('Invalid CSV point at line ' + str(line))
            groups.setdefault(name, []).append((row[0].strip(), p, line))
    marks = {}
    for name, rows in groups.items():
        preferred = [r for r in rows if r[0] == 'Fiducial'] if name in FIDUCIALS else []
        rows = preferred or rows
        if any(not np.allclose(r[1], rows[0][1], atol=1e-4, rtol=0) for r in rows[1:]):
            raise ValueError('Conflicting duplicate CSV point: ' + name)
        marks[name] = rows[0][1]
    for name in required_names:
        if name not in marks: raise ValueError('EEG CSV missing ' + name)
    if np.linalg.norm(marks['LPA']-marks['RPA']) < 50 or np.linalg.norm(marks['Nz']-marks['Iz']) < 80:
        raise ValueError('Implausible fiducial spacing; scanner RAS coordinates must be in mm')
    return marks

def select_components(v,tri,reference_only=False):
    """Retain a dominant scalp only if discarded islands satisfy BOTH limits.

    No welding, bridging or volume-mesh edits. All cap points are checked later
    against the retained surface, so a landmark-bearing island cannot be hidden.
    """
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    edges=np.vstack((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]))
    graph=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
    _,labels=connected_components(graph,directed=False)
    face_labels=labels[tri[:,0]];components=np.unique(face_labels)
    a,b,c=v[tri[:,0]],v[tri[:,1]],v[tri[:,2]]
    area=np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
    areas=np.array([area[face_labels==k].sum() for k in components]);total=float(areas.sum())
    if total<=0:raise ValueError('Scalp has no positive surface area')
    main=int(components[int(areas.argmax())]);keep=face_labels==main
    discarded=float(area[~keep].sum());fraction=discarded/total
    info={'input_components':int(len(components)),'input_triangles':int(len(tri)),
          'component_areas_mm2':sorted(map(float,areas),reverse=True),
          'tiny_island_policy':{'maximum_total_removed_area_mm2':50.0,'maximum_total_removed_area_fraction':0.001},
          'triangles_removed':0,'area_removed_mm2':0.0,'area_removed_fraction':0.0,
          'vertices_moved_or_welded':False,'reference_only':bool(reference_only)}
    if reference_only or len(components)==1:return np.ones(len(tri),bool),info
    if discarded>50.0 or fraction>0.001:
        raise ValueError('Scalp has disconnected components: '+str(len(components))+f'; secondary area {discarded:.3f} mm2 ({100*fraction:.4f}%). Too large for automatic tiny-island removal; review the mask. No components were joined.')
    info.update(triangles_removed=int((~keep).sum()),area_removed_mm2=discarded,area_removed_fraction=fraction)
    return keep,info

def read_surface(path,reference_only=False,audit=None):
    from simnibs import mesh_io
    m=mesh_io.read_msh(str(path))
    scalp=(m.elm.elm_type==2)&(m.elm.tag1==1005)
    if not np.any(scalp):raise ValueError('No scalp triangles with tag 1005 in '+str(path))
    # SimNIBS crop_mesh combines different selectors with OR, not AND.
    # Passing tags=1005 AND elm_type=2 would also include cortex/skull triangles!
    m=m.crop_mesh(elements=m.elm.elm_number[scalp])
    v=np.asarray(m.nodes.node_coord,float);tri=np.asarray(m.elm.node_number_list[:,:3],int)-1
    if len(v)<4 or len(tri)<4 or not np.isfinite(v).all() or tri.min()<0 or tri.max()>=len(v):raise ValueError('Invalid scalp mesh: '+str(path))
    try:keep,info=select_components(v,tri,reference_only)
    except ValueError as e:raise ValueError(str(path)+': '+str(e)) from e
    if not keep.all():
        m=m.crop_mesh(elements=m.elm.elm_number[keep])
        v=np.asarray(m.nodes.node_coord,float);tri=np.asarray(m.elm.node_number_list[:,:3],int)-1
        print('Localization scalp: removed '+str(info['triangles_removed'])+' tiny-island triangles; '+str(round(info['area_removed_mm2'],4))+' mm2. Source MSH and FEM retained.',flush=True)
    if audit is not None:audit.update(info)
    a,b,c=v[tri[:,0]],v[tri[:,1]],v[tri[:,2]]
    if np.any(np.linalg.norm(np.cross(b-a,c-a),axis=1)<=1e-10):raise ValueError('Degenerate scalp triangles: '+str(path))
    if len(np.unique(np.sort(tri,axis=1),axis=0))!=len(tri):raise ValueError('Duplicate scalp triangles: '+str(path))
    directed=np.vstack((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]));edges=np.sort(directed,axis=1)
    unique,inverse,count=np.unique(edges,axis=0,return_inverse=True,return_counts=True)
    if np.any(count>2):raise ValueError('Non-manifold scalp edges; rebuild/review the mask: '+str(path))
    balance=np.bincount(inverse,weights=np.where(directed[:,0]<directed[:,1],1,-1),minlength=len(unique))
    if np.any(balance[count==2]!=0):raise ValueError('Inconsistent scalp triangle winding: '+str(path))
    if np.sum(np.einsum('ij,ij->i',np.cross(b-a,c-a),(a+b+c)/3-v.mean(0)))<=0:raise ValueError('Scalp triangle normals face inward; review/re-export: '+str(path))
    return m,v,tri,v[np.unique(unique[count==1])]

def nearest(v,tri,p):
    # Exact triangle projection, including edge/vertex cases.
    a,b,c=v[tri[:,0]],v[tri[:,1]],v[tri[:,2]];ab=b-a;ac=c-a;ap=p-a
    aa=(ab*ab).sum(1);bb=(ab*ac).sum(1);cc=(ac*ac).sum(1);dd=(ap*ab).sum(1);ee=(ap*ac).sum(1);den=aa*cc-bb*bb
    good=den>1e-14;u=np.zeros(len(den));w=u.copy();u[good]=(dd*cc-ee*bb)[good]/den[good];w[good]=(ee*aa-dd*bb)[good]/den[good]
    q=a+u[:,None]*ab+w[:,None]*ac;valid=good&(u>=0)&(w>=0)&(u+w<=1);dist=((q-p)**2).sum(1);dist[~valid]=np.inf;i=dist.argmin();best=(float(dist[i]),q[i])
    for x,y in ((a,b),(b,c),(c,a)):
        e=y-x;den=(e*e).sum(1);valid=den>1e-14;t=np.zeros(len(den));t[valid]=np.clip(((p-x)*e).sum(1)[valid]/den[valid],0,1);q=x+t[:,None]*e;dist=((q-p)**2).sum(1);dist[~valid]=np.inf;i=dist.argmin()
        if dist[i]<best[0]:best=(float(dist[i]),q[i])
    return best[1], float(np.sqrt(best[0]))

def unchanged_local_patch(v,tri,p,reference,radius=10.):
    """A near-boundary fiducial may inherit only an identical original patch."""
    if reference is None:return False
    rv,rt=reference
    rq,rd=nearest(rv,rt,p)
    if rd>1e-6:return False
    def local_faces(vertices,faces):
        xyz=vertices[faces];distance=np.maximum(np.maximum(xyz.min(1)-p,p-xyz.max(1)),0)
        xyz=xyz[np.linalg.norm(distance,axis=1)<=radius]
        # Coordinate comparison survives node renumbering and MSH round trips.
        rows=[]
        for face in np.round(xyz,8):rows.append(tuple(sorted(map(tuple,face))))
        return sorted(rows)
    a=local_faces(v,tri);return bool(a) and a==local_faces(rv,rt)

def validate_pair(surface, csvpath,original_reference=None):
    cleanup={};m,v,tri,boundary=read_surface(surface,audit=cleanup);marks=read_positions(csvpath);residuals={}
    inherited=[]
    # All points are checked, so a partly stale cap cannot silently be mixed in.
    for name,p in marks.items():
        q,d=nearest(v,tri,p);residuals[name]=d
        if d>3: raise ValueError(f'{name}: scalp residual {d:.2f} mm > 3 mm; check surface/CSV pairing')
        if name in REQUIRED and len(boundary) and np.linalg.norm(boundary-q,axis=1).min()<5:
            if name in FIDUCIALS and unchanged_local_patch(v,tri,q,original_reference):inherited.append(name)
            else:raise ValueError(name + ': too close to an open scalp boundary')
    return m,marks,{'point_count':len(marks),'max_surface_residual_mm':max(residuals.values()),'residuals_mm':residuals,'boundary_vertices':len(boundary),'surface_cleanup':cleanup,'fiducials_on_unchanged_original_boundary_patches':inherited}

def find_fem(folder):
    folder=Path(folder)
    preferred=folder/(folder.name.removeprefix('m2m_')+'.msh')
    if preferred.is_file(): return preferred
    files=list(folder.glob('*.msh'))
    if len(files)!=1: raise ValueError('Select an m2m folder containing one volume head mesh')
    return files[0]

def ensure_reviewable(folder):
    folder=Path(folder).resolve();status=folder.parent/'remesh_status.json'
    if status.is_file():
        record=json.loads(status.read_text(encoding='utf-8'))
        if record.get('status')!='BUILT_REQUIRES_VISUAL_REVIEW':
            raise ValueError('FEM candidate is incomplete or failed: '+str(record.get('status')))

def bind(folder, surface, csvpath,surface_kind="repaired",provenance=None):
    from simnibs import mesh_io
    folder=Path(folder).resolve();ensure_reviewable(folder);fem=find_fem(folder)
    volume=mesh_io.read_msh(str(fem))
    if not np.any(volume.elm.elm_type==4): raise ValueError('Simulation head mesh must contain tetrahedra')
    hybrid_report=Path(surface).resolve().parent/'hybrid_manifest.json';original_reference=None
    if hybrid_report.is_file():
        hybrid=json.loads(hybrid_report.read_text(encoding='utf-8'))
        if hybrid.get('status')!='COMPUTED_REQUIRES_VISUAL_REVIEW' or hybrid.get('surface_sha256')!=digest(surface) or hybrid.get('EEG_csv_sha256')!=digest(csvpath):
            raise ValueError('Hybrid surface / EEG is incomplete, changed or mismatched; rebuild or select the verified pair')
        surface_kind='hybrid'
        if hybrid.get('original_MSH_sha256')!=digest(fem):raise ValueError('Hybrid source FEM hash does not match selected m2m')
        _,rv,rt,_=read_surface(fem,reference_only=True);original_reference=(rv,rt)
        if provenance is None:provenance={'hybrid_manifest_sha256':digest(hybrid_report),'seam_quality':hybrid.get('seam_quality')}
    m,marks,report=validate_pair(surface,csvpath,original_reference=original_reference)
    # A geometry sanity check complements the user's explicit same-subject review.
    reference_audit={}
    _,fv,ft,_=read_surface(fem,reference_only=True,audit=reference_audit)
    report['original_FEM_scalp_reference']=reference_audit
    report['fiducial_distance_to_original_FEM_mm']={n:nearest(fv,ft,marks[n])[1] for n in FIDUCIALS}
    if max(report['fiducial_distance_to_original_FEM_mm'].values())>30:
        raise ValueError('Fiducials are >30 mm from FEM scalp; check subject and RAS coordinate frame')
    sub=Path('repair_assets')/('import_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out=folder/sub;out.mkdir(parents=True)
    # Export scalp only: even if a full mesh was selected, the localization role stays explicit.
    sp=out/'localization_scalp.msh';mesh_io.write_msh(m,str(sp))
    cp=out/'EEG10-10_repaired.csv'
    # Normalize duplicates for the official GUI, whose reader does not resolve them.
    with cp.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f)
        for n,p in marks.items(): w.writerow(['Fiducial' if n in FIDUCIALS else 'ReferenceElectrode' if n=='Cz' else 'Electrode',*p,n])
    record={'schema':1,'suite_version':'1.80.2','mode':'LOCALIZATION_OVERLAY_ORIGINAL_FEM',
        'coordinate_system':'scanner RAS mm','fem':str(fem.relative_to(folder)),
        'surface':str(sp.relative_to(folder)),'eeg_csv':str(cp.relative_to(folder)),
        'fem_sha256':digest(fem),'surface_sha256':digest(sp),'eeg_csv_sha256':digest(cp),
        'source_surface_sha256':digest(surface),'source_csv_sha256':digest(csvpath),
        'same_subject_and_anatomy_confirmed_by_user':True,'validation':report,
        'FEM_geometry_modified':False,'surface_kind':surface_kind,'provenance':provenance,'note':'Repaired surface is for localization/measurement; electromagnetic fields use the original volume FEM.'}
    (out/'binding.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    p=folder/'repair_binding.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(record,indent=2),encoding='utf-8');tmp.replace(p)
    return record

def load_binding(folder, fem=None):
    folder=Path(folder).resolve();p=folder/'repair_binding.json'
    if not p.is_file(): return None
    r=json.loads(p.read_text(encoding='utf-8'))
    if r.get('schema')!=1: raise ValueError('Unknown repair binding schema')
    paths={}
    for key in ('fem','surface','eeg_csv'):
        path=(folder/r[key]).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or digest(path)!=r[key+'_sha256']:
            raise ValueError('Repair binding is stale or invalid: '+key+'; import the reviewed pair again')
        paths[key]=str(path)
    if fem is not None and Path(paths['fem'])!=Path(fem).resolve(): raise ValueError('Repair binding belongs to a different FEM')
    return dict(r,**paths)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--m2m',required=True);p.add_argument('--surface',required=True);p.add_argument('--csv',required=True)
    a=p.parse_args();print(json.dumps(bind(a.m2m,a.surface,a.csv),indent=2))
