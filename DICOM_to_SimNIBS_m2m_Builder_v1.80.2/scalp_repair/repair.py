# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""T2-assisted scalp envelope repair. Experimental surface geometry, NOT FEM tissues.
All ITK transforms use LPS physical millimetres. Output NIfTI/PLY use RAS mm.
"""
import argparse, hashlib, itertools, json, time
from pathlib import Path
import numpy as np
import nibabel as nib
import SimpleITK as sitk
from surface_cleanup import clean_surface
from scipy import ndimage as ndi

VERSION='0.1.0'
def log(s): print(s,flush=True)
def dump(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(path,policy='qform',binary=False):
 im=nib.load(str(path))
 if len(im.shape)!=3:raise ValueError('Only 3D images are supported')
 q,qc=im.get_qform(coded=True);s,sc=im.get_sform(coded=True)
 aff=q if policy=='qform' else s
 code=qc if policy=='qform' else sc
 if aff is None or not code:raise ValueError(f'{policy} is not valid: {path}')
 if not np.isfinite(aff).all():raise ValueError('Non-finite affine')
 a=im.get_fdata(dtype=np.float32)
 if not np.isfinite(a).all():raise ValueError('Non-finite image intensities')
 if binary:a=(a>0).astype(np.uint8)
 lps=np.diag([-1.,-1.,1.,1.])@aff;spacing=np.linalg.norm(lps[:3,:3],axis=0);direction=lps[:3,:3]/spacing
 if not np.allclose(direction.T@direction,np.eye(3),atol=1e-4):raise ValueError('Selected affine contains shear. Review header or choose qform.')
 out=sitk.GetImageFromArray(a.transpose(2,1,0));out.SetSpacing(tuple(spacing));out.SetDirection(tuple(direction.ravel()));out.SetOrigin(tuple(lps[:3,3]))
 meta={'path':str(Path(path).resolve()),'sha256':sha(path),'shape':list(im.shape),'spacing_mm':spacing.tolist(),'selected_form':policy,'qform_code':int(qc),'sform_code':int(sc),'qform':None if q is None else q.tolist(),'sform':None if s is None else s.tolist()}
 return out,meta

def corners(im):
 return np.array([im.TransformContinuousIndexToPhysicalPoint(tuple(map(float,i))) for i in itertools.product(*[(-.5,n-.5) for n in im.GetSize()])])
def union_grid(fixed,moving,fixed_to_moving,spacing=1.,margin=3.):
 """Bounding box of BOTH voxel volumes in fixed axes; transform moving corners inverse."""
 inv=fixed_to_moving.GetInverse();p=np.vstack([corners(fixed),[inv.TransformPoint(tuple(x)) for x in corners(moving)]])
 d=np.array(fixed.GetDirection()).reshape(3,3);u=p@d;lo=u.min(0)-margin;hi=u.max(0)+margin
 size=np.ceil((hi-lo)/spacing).astype(int)+1
 if np.prod(size)>70_000_000:raise ValueError('Union grid too large; check registration or use larger spacing')
 ref=sitk.Image(list(map(int,size)),sitk.sitkFloat32);ref.SetSpacing((spacing,)*3);ref.SetDirection(tuple(d.ravel()));ref.SetOrigin(tuple(d@lo));return ref

def sample(im,ref,tx=None,label=False):
 return sitk.Resample(im,ref,tx or sitk.Transform(3,sitk.sitkIdentity),sitk.sitkNearestNeighbor if label else sitk.sitkLinear,0.,sitk.sitkUInt8 if label else sitk.sitkFloat32)
def support(im,ref,tx=None):
 one=sitk.Image(im.GetSize(),sitk.sitkUInt8);one.CopyInformation(im);one=one+1
 return sitk.GetArrayFromImage(sample(one,ref,tx,True)).astype(bool)
def as_image(a,ref):
 im=sitk.GetImageFromArray(a);im.CopyInformation(ref);return im

def affine_ras(ref):
 a=np.eye(4);a[:3,:3]=np.array(ref.GetDirection()).reshape(3,3)@np.diag(ref.GetSpacing());a[:3,3]=ref.GetOrigin();return np.diag([-1.,-1.,1.,1.])@a

def save(a,ref,path):
 a=np.asarray(a);aff=affine_ras(ref);im=nib.Nifti1Image(a.transpose(2,1,0),aff);im.set_qform(aff,1);im.set_sform(aff,1);nib.save(im,str(path))

def largest(a):
 labels,num=ndi.label(a)
 if not num:return a
 counts=np.bincount(labels.ravel());counts[0]=0;return labels==counts.argmax()
def envelope(im,factor=.5):
 """Heuristic exterior envelope: threshold + per-acquisition-slice hole fill.
 Not scalp tissue segmentation. Never assigns GM/WM/skull/CSF labels.
 """
 a=sitk.GetArrayFromImage(im);smooth=ndi.gaussian_filter(a,(0,.7,.7))
 otsu=sitk.OtsuThresholdImageFilter();otsu.Execute(as_image(smooth,im));threshold=otsu.GetThreshold()*factor
 raw=smooth>threshold;out=np.zeros(raw.shape,bool)
 for k in range(len(raw)):
  sl=ndi.binary_closing(raw[k],iterations=2)
  out[k]=ndi.binary_fill_holes(largest(sl))
 return as_image(largest(out).astype(np.uint8),im),float(threshold)

def normalize(im):
 a=sitk.GetArrayFromImage(im);p=np.percentile(a[a>0],99.5);return as_image(np.clip(a/max(p,1e-6),0,1).astype(np.float32),im)
def register(fixed,moving):
 # Resample to 2 mm working grids, retain native orientation and FOV.
 def coarse(im):
  ref=sitk.Image([int(np.ceil((n-1)*s/2))+1 for n,s in zip(im.GetSize(),im.GetSpacing())],sitk.sitkFloat32);ref.SetOrigin(im.GetOrigin());ref.SetDirection(im.GetDirection());ref.SetSpacing((2.,)*3);return normalize(sample(im,ref))
 f,m=coarse(fixed),coarse(moving)
 tx=sitk.Euler3DTransform();tx.SetCenter(f.TransformContinuousIndexToPhysicalPoint(tuple((np.array(f.GetSize())-1)/2)))
 # Scanner coordinates initialize this within-session rigid alignment. Do not align FOV centres.
 r=sitk.ImageRegistrationMethod();r.SetMetricAsMattesMutualInformation(50);r.SetMetricSamplingStrategy(r.RANDOM);r.SetMetricSamplingPercentage(.25,42)
 r.SetInterpolator(sitk.sitkLinear);r.SetOptimizerAsRegularStepGradientDescent(1.,.001,200,gradientMagnitudeTolerance=1e-6);r.SetOptimizerScalesFromPhysicalShift();r.SetShrinkFactorsPerLevel([4,2,1]);r.SetSmoothingSigmasPerLevel([2,1,0]);r.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn();r.SetInitialTransform(tx,inPlace=True)
 r.AddCommand(sitk.sitkMultiResolutionIterationEvent,lambda:log('Registration level '+str(r.GetCurrentLevel())))
 r.Execute(f,m)
 if not np.isfinite(r.GetMetricValue()):raise ValueError('Registration failed')
 rotation=np.rad2deg(np.array(tx.GetParameters()[:3]));translation=tx.GetTranslation()
 if np.max(np.abs(rotation))>20 or np.linalg.norm(translation)>35:raise ValueError('Large registration correction; inspect headers / manually register first')
 return tx,{'metric':float(r.GetMetricValue()),'stop':r.GetOptimizerStopConditionDescription(),'rotation_degrees':rotation.tolist(),'translation_at_center_mm':list(translation),'meaning':'fixed T1 LPS -> moving T2 LPS (resampling pull transform)'}

def signed(a,spacing):return ndi.distance_transform_edt(a,sampling=spacing)-ndi.distance_transform_edt(~a,sampling=spacing)
def patch(base,donor,cov1,cov2,superior_mm,seam_mm,spacing):
 # superior_mm = signed distance above the original T1 superior FOV boundary.
 band=(superior_mm>-seam_mm)&cov2
 weight=np.clip((superior_mm+seam_mm)/seam_mm,0,1)
 d1=signed(base,spacing);d2=signed(donor,spacing)
 result=base.copy();blend=band&cov1
 result[blend]=((1-weight)*d1+weight*d2)[blend]>0
 # Above original FOV: donor segmentation only, no extrapolated synthetic cap.
 above=(superior_mm>=0)&cov2&~cov1
 result[above]=donor[above]
 provenance=np.zeros(base.shape,np.uint8);provenance[result]=1;provenance[result&blend]=3;provenance[result&above]=2
 return result,provenance,band

def superior_distance(fixed,ref):
 direction=np.array(fixed.GetDirection()).reshape(3,3);axis=int(np.argmax(np.abs(direction[2])))
 if abs(direction[2,axis])<.85:raise ValueError('T1 is not approximately axial; this superior-cap tool needs an axial input')
 sign=np.sign(direction[2,axis]);n=direction[:,axis]*sign
 # signed physical distance to the superior voxel-volume face, positive above.
 index=np.zeros(3);index[axis]=fixed.GetSize()[axis]-.5 if sign>0 else -.5
 plane=np.array(fixed.TransformContinuousIndexToPhysicalPoint(tuple(index)))
 size=ref.GetSize();d=np.array(ref.GetDirection()).reshape(3,3);sp=np.array(ref.GetSpacing());origin=np.array(ref.GetOrigin())
 x=np.arange(size[0])[None,None,:];y=np.arange(size[1])[None,:,None];z=np.arange(size[2])[:,None,None]
 return (np.dot(origin-plane,n)+x*np.dot(d[:,0]*sp[0],n)+y*np.dot(d[:,1]*sp[1],n)+z*np.dot(d[:,2]*sp[2],n)).astype(np.float32)

def surface(mask,ref,coverage,out):
 from skimage.measure import marching_cubes
 # Pad for marching cubes; omit any face at the acquisition-domain closure (incl neck).
 padded=np.pad(mask,1);v,f,_,_=marching_cubes(padded.astype(np.uint8),.5);v-=1
 centers=v[f].mean(1);idx=np.clip(np.rint(centers).astype(int),0,np.array(mask.shape)-1)
 safe=ndi.distance_transform_edt(coverage,sampling=ref.GetSpacing()[::-1])
 keep=safe[tuple(idx.T)]>max(ref.GetSpacing())*1.5;f=f[keep]
 xyz=v[:,::-1];aff=affine_ras(ref);verts=xyz@aff[:3,:3].T+aff[:3,3]
 verts,f,cleanup=clean_surface(verts,f)
 log('Surface cleanup: '+json.dumps(cleanup))
 # Reflections can flip triangle winding; ensure outside-facing after RAS conversion.
 if np.linalg.det(aff[:3,:3][:,::-1])<0:f=f[:,::-1]
 with open(out,'w',encoding='ascii') as h:
  h.write('ply\nformat ascii 1.0\ncomment DRAFT scalp envelope RAS mm; open acquisition boundaries; NOT FEM\n')
  h.write(f'element vertex {len(verts)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(f)}\nproperty list uchar int vertex_indices\nend_header\n')
  np.savetxt(h,verts,fmt='%.4f');np.savetxt(h,np.c_[np.full(len(f),3),f],fmt='%d')
 return {'vertices':len(verts),'faces':len(f),'faces_omitted_at_FOV_boundary':int((~keep).sum()),'coordinates':'T1 scanner RAS mm','closed':False,'usable_as_FEM':False,'cleanup':cleanup}

def qc(out,a,b,base,donor,result,prov,coverage,ref):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 # Array z,y,x follows T1 axes, not exact world axial/sagittal when oblique.
 inds=np.argwhere(result);center=np.median(inds,axis=0).astype(int)
 fig,axs=plt.subplots(3,4,figsize=(15,11))
 for row,(axis,title) in enumerate([(2,'T1-grid sagittal'),(1,'T1-grid coronal'),(0,'T1-grid axial')]):
  k=center[axis]
  if axis==0:k=int(np.percentile(inds[:,0],85))
  def sl(x):return np.take(x,k,axis=axis)
  for col,im in enumerate([a,b,a,b]):
   s=sl(im);v=np.percentile(im[im>0],99) if np.any(im>0) else 1
   axs[row,col].imshow(s,origin='lower',cmap='gray',vmin=0,vmax=v)
   if col==2:
    axs[row,col].contour(sl(base),[.5],colors=['cyan'],linewidths=.7);axs[row,col].contour(sl(donor),[.5],colors=['orange'],linewidths=.7)
   if col==3:
    axs[row,col].contour(sl(result),[.5],colors=['lime'],linewidths=.7)
    overlay=np.ma.masked_where(sl(prov)!=2,sl(prov));axs[row,col].imshow(overlay,origin='lower',cmap='autumn',alpha=.6,vmin=1,vmax=3)
   axs[row,col].axis('off');axs[row,col].set_title(title+' | '+['T1','T2 registered','T1 cyan / T2 orange','Draft green / added red'][col])
 fig.suptitle('EXPERIMENTAL scalp envelope | 1 mm grid is interpolation, not 1 mm acquisition accuracy',fontsize=12)
 fig.tight_layout();fig.savefig(out/'qc_overview.png',dpi=140);plt.close(fig)
 # Multiple parasagittal cuts around head centre to inspect the cap and seam.
 fig,axs=plt.subplots(2,4,figsize=(16,8))
 xs=np.linspace(np.percentile(inds[:,2],20),np.percentile(inds[:,2],80),8).astype(int)
 for ax,x in zip(axs.flat,xs):
  ax.imshow(b[:,:,x],origin='lower',cmap='gray',vmin=0,vmax=np.percentile(b[b>0],99));ax.contour(result[:,:,x],[.5],colors='lime',linewidths=.7);ax.contour(base[:,:,x],[.5],colors='cyan',linewidths=.7);ax.set_title(f'T1 grid x={x}: cyan original, green draft');ax.axis('off')
 fig.tight_layout();fig.savefig(out/'qc_cap_slices.png',dpi=140);plt.close(fig)

def prepare(args):
 start=time.monotonic();out=Path(args.output)
 if out.exists() and any(out.iterdir()):raise ValueError('Output folder must be new or empty; existing results will not be overwritten')
 out.mkdir(parents=True,exist_ok=True)
 sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(4)
 log('Reading inputs');fixed,fmeta=load(args.t1,args.form);moving,mmeta=load(args.t2,args.form)
 log('Rigid multimodal registration');tx,reg=register(fixed,moving)
 sitk.WriteTransform(tx,str(out/'T1_to_T2_pull_LPS.tfm'));sitk.WriteTransform(tx.GetInverse(),str(out/'T2_to_T1_points_LPS.tfm'))
 ref=union_grid(fixed,moving,tx,args.spacing)
 log('Resampling onto union grid');a=sitk.GetArrayFromImage(sample(fixed,ref));b=sitk.GetArrayFromImage(sample(moving,ref,tx));c1=support(fixed,ref);c2=support(moving,ref,tx)
 mask_info={}
 masks=[]
 for name,im,mpath in [('T1',fixed,args.t1_mask),('T2',moving,args.t2_mask)]:
  if mpath:
   m,meta=load(mpath,args.form,True)
   # A supplied envelope must be native-space and have matching spatial geometry.
   if m.GetSize()!=im.GetSize() or not np.allclose(m.GetOrigin(),im.GetOrigin(),atol=.01) or not np.allclose(m.GetDirection(),im.GetDirection(),atol=1e-4) or not np.allclose(m.GetSpacing(),im.GetSpacing(),atol=1e-4):raise ValueError(name+' envelope mask must match the native source geometry')
   mask_info[name]={'source':'user binary whole-head envelope','input':meta}
  else:
   m,threshold=envelope(im,args.threshold_factor);mask_info[name]={'source':'automatic heuristic whole-head envelope, requires manual review','threshold':threshold,'threshold_factor':args.threshold_factor}
  masks.append(sitk.GetArrayFromImage(sample(m,ref,None if name=='T1' else tx,True)).astype(bool))
 base,donor=masks;sup=superior_distance(fixed,ref)
 log('Building labelled cap draft');result,prov,band=patch(base,donor,c1,c2,sup,args.seam,ref.GetSpacing()[::-1])
 coverage=c1|((sup>=-args.seam)&c2)
 overlap=c1&c2
 dice=2*np.count_nonzero(base&donor&overlap)/max(1,np.count_nonzero(base&overlap)+np.count_nonzero(donor&overlap))
 added=result&~base;removed=base&~result
 for name,arr in [('T1_union',a),('T2_registered_union',b),('T1_FOV',c1),('T2_FOV',c2),('T1_envelope',base),('T2_envelope',donor),('scalp_envelope_DRAFT',result),('repair_provenance',prov),('added_envelope',added),('removed_envelope',removed),('surface_valid_domain',coverage)]:
  save(arr.astype(np.uint8) if arr.dtype==bool else arr,ref,out/(name+'.nii.gz'))
 stats={'version':VERSION,'T1':fmeta,'T2':mmeta,'registration':reg,'masks':mask_info,'grid':{'size_xyz':list(ref.GetSize()),'spacing_mm':list(ref.GetSpacing()),'affine_RAS':affine_ras(ref).tolist()},'seam_mm':args.seam,'overlap_envelope_dice':float(dice),'T2_cap_voxels':int((prov==2).sum()),'added_voxels':int(added.sum()),'removed_voxels':int(removed.sum()),'elapsed_seconds':time.monotonic()-start,'status':'DRAFT_REQUIRES_REVIEW','FEM_validated':False,'warnings':['Automatic masks are filled head envelopes, not scalp tissue labels.','6 mm slice sampling cannot be recovered by 1 mm resampling.','Rigid registration does not correct local distortion.','Support masks describe image slabs and include between-slice interpolation.','No extrapolation into regions absent from both inputs.','No EEG markers or m2m FEM have been updated.']}
 if dice<.85:stats['warnings'].append('Low whole-head envelope overlap; inspect registration before accepting.')
 if not stats['T2_cap_voxels']:stats['warnings'].append('No T2 cap was added. Check input coverage and masks.')
 dump(out/'manifest.json',stats)
 log('Rendering QC images');qc(out,a,b,base,donor,result,prov,coverage,ref)
 # Draft surface always explicitly labelled; reviewed export is a separate user action.
 stats['surface']=surface(result,ref,coverage,out/'scalp_surface_DRAFT_RAS.ply');dump(out/'manifest.json',stats)
 (out/'review.html').write_text('''<!doctype html><meta charset="utf-8"><title>頭皮補頂草稿檢查</title><style>body{font:18px sans-serif;max-width:1200px;margin:auto;padding:24px}img{width:100%}</style><h1>頭皮補頂草稿：待人工檢查</h1><p>這是填滿頭部內部的外輪廓遮罩，不是 scalp／skull／CSF 多組織標籤，也不是 m2m FEM。</p><p>請先在影像檢視器逐切面檢查 T1/T2 對位、耳前點／鼻根／枕點、頭頂輪廓與接縫。下圖只顯示部分切片，不代表全體積已確認。</p><p>青色：T1 原輪廓；橘色：T2 輪廓；綠色：補頂草稿；紅色：T2 補入區。影像沿 T1 網格顯示，不是完全正交解剖切面。</p><img src="qc_overview.png"><img src="qc_cap_slices.png"><p>repair_provenance：1=T1 外輪廓，2=T2 補頂，3=接縫融合。不要將此檔當 CHARM tissue labels。</p><p>PLY 座標為 T1 scanner RAS mm；採集邊界的封口三角形已移除，表面可能開口。重新計算 Cz／EEG 標記前需另行處理定位。</p>''',encoding='utf-8')
 log('Draft complete: '+str(out/'review.html'))
 return stats

def approve(folder,reviewed_mask=None):
 """Explicit review records which candidate was accepted; no claim of clinical validation."""
 out=Path(folder);manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
 if reviewed_mask:
  im=nib.load(str(reviewed_mask));orig=nib.load(out/'scalp_envelope_DRAFT.nii.gz')
  if im.shape!=orig.shape or not np.allclose(im.affine,orig.affine,atol=1e-4):raise ValueError('Reviewed mask must retain union-grid geometry')
  data=im.get_fdata()
  if not np.isfinite(data).all():raise ValueError('Invalid reviewed mask')
  mask=data.transpose(2,1,0)>0
 else:mask=nib.load(out/'scalp_envelope_DRAFT.nii.gz').get_fdata().transpose(2,1,0)>0
 ref,_=load(out/'T1_union.nii.gz','qform');coverage=nib.load(out/'surface_valid_domain.nii.gz').get_fdata().transpose(2,1,0)>0
 if np.any(mask&~coverage):raise ValueError('Reviewed mask extends beyond the supported repair domain')
 save(mask.astype(np.uint8),ref,out/'scalp_envelope_REVIEWED.nii.gz');surface(mask,ref,coverage,out/'scalp_surface_REVIEWED_RAS.ply')
 manifest['user_review']={'time':time.strftime('%Y-%m-%d %H:%M:%S'),'reviewed_mask':str(reviewed_mask) if reviewed_mask else 'draft accepted','mask_sha256':sha(out/'scalp_envelope_REVIEWED.nii.gz'),'surface_sha256':sha(out/'scalp_surface_REVIEWED_RAS.ply'),'meaning':'User accepted geometric draft, not clinical/FEM validation'}
 dump(out/'manifest.json',manifest);log('Reviewed surface exported; FEM remains unchanged')

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('prepare');a.add_argument('--t1',required=True);a.add_argument('--t2',required=True);a.add_argument('--output',required=True);a.add_argument('--t1-mask');a.add_argument('--t2-mask');a.add_argument('--form',choices=['qform','sform'],default='qform');a.add_argument('--spacing',type=float,default=1.);a.add_argument('--seam',type=float,default=6.);a.add_argument('--threshold-factor',type=float,default=.5)
 a=sub.add_parser('approve');a.add_argument('--output',required=True);a.add_argument('--reviewed-mask')
 args=p.parse_args()
 if args.command=='prepare':
  if args.spacing<.8 or args.spacing>3 or args.seam<=0 or not 0<args.threshold_factor<2:raise ValueError('Invalid spacing/seam/threshold factor')
  prepare(args)
 else:approve(args.output,args.reviewed_mask)
