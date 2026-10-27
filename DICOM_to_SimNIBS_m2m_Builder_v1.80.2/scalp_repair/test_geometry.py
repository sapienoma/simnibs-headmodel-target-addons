# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
import unittest,tempfile
from pathlib import Path
import numpy as np
import SimpleITK as sitk
import nibabel as nib
from repair import union_grid,corners,patch,sample,as_image,save,load,superior_distance

class GeometryTests(unittest.TestCase):
 def image(self):
  im=sitk.Image([20,24,16],sitk.sitkFloat32);im.SetSpacing((1.,2.,3.));im.SetOrigin((30.,-10.,4.));return im
 def test_union_contains_both_transformed_volumes(self):
  a=self.image();b=self.image();b.SetOrigin((-8.,15.,-30.));tx=sitk.Euler3DTransform();tx.SetRotation(.05,.1,-.2);tx.SetTranslation((10.,-8.,4.));ref=union_grid(a,b,tx,1.)
  for p in list(corners(a))+[tx.GetInverse().TransformPoint(tuple(p)) for p in corners(b)]:
   i=np.array(ref.TransformPhysicalPointToContinuousIndex(tuple(p)));self.assertTrue(np.all(i>=-.5));self.assertTrue(np.all(i<=np.array(ref.GetSize())-.5))
 def test_pull_transform_direction(self):
  a=sitk.Image([25]*3,sitk.sitkFloat32);a[14,10,10]=1
  ref=sitk.Image([25]*3,sitk.sitkFloat32);tx=sitk.TranslationTransform(3,(4.,0,0))
  out=sample(a,ref,tx);self.assertEqual(out[10,10,10],1);self.assertEqual(out[18,10,10],0)
 def test_nifti_ras_roundtrip(self):
  im=self.image();a=np.zeros((16,24,20),np.uint8);a[3,4,5]=1
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'mask.nii.gz';save(a,im,path);ni=nib.load(path);p=ni.affine@np.array([5,4,3,1]);expected=im.TransformIndexToPhysicalPoint((5,4,3));np.testing.assert_allclose(p[:3],np.array(expected)*[-1,-1,1],atol=1e-5)
   restored,_=load(path);np.testing.assert_allclose(restored.GetOrigin(),im.GetOrigin(),atol=1e-5);np.testing.assert_array_equal(sitk.GetArrayFromImage(restored),a)
 def test_patch_preserves_lower_region_and_no_uncovered_fill(self):
  z,y,x=np.indices((30,30,30));full=(x-15)**2+(y-15)**2+(z-15)**2<100;c1=z<20;c2=(x>5)&(x<24);base=full&c1;donor=full&c2;sup=z-19.5
  out,prov,band=patch(base,donor,c1,c2,sup,3,(1,1,1))
  np.testing.assert_array_equal(out[z<16],base[z<16]);self.assertFalse(np.any(out&~(c1|c2)));self.assertTrue(np.any(prov==2));self.assertTrue(np.all(out[~c1&c2]==donor[~c1&c2]))
 def test_superior_plane_respects_oblique_geometry(self):
  im=self.image();tx=sitk.Euler3DTransform();tx.SetRotation(.2,0,0);im.SetDirection(tx.GetMatrix());ref=union_grid(im,im,sitk.Transform(3,sitk.sitkIdentity),1.)
  distances=superior_distance(im,ref);idx=(10,11,12);world=np.array(ref.TransformIndexToPhysicalPoint(idx));n=np.array(im.GetDirection()).reshape(3,3)[:,2];face=np.array(im.TransformContinuousIndexToPhysicalPoint((0.,0.,15.5)))
  self.assertAlmostEqual(float(distances[idx[2],idx[1],idx[0]]),np.dot(world-face,n),places=4)
if __name__=='__main__':unittest.main()
