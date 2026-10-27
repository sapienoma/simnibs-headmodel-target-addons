# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
import unittest,csv,json,tempfile,sys,types
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.spatial import ConvexHull
from target_geometry import TargetModel,Curve,arc_length
from target_workflow import transform_mni

def sphere():
    ph=np.deg2rad(np.arange(2,180,2));th=np.deg2rad(np.arange(0,360,2));p,t=np.meshgrid(ph,th,indexing='ij')
    v=100*np.column_stack([(np.sin(p)*np.cos(t)).ravel(),(np.sin(p)*np.sin(t)).ravel(),np.cos(p).ravel()]);v=np.vstack([v,[0,0,100],[0,0,-100]])
    tri=ConvexHull(v).simplices
    z=100*np.sin(np.deg2rad(18));r=100*np.cos(np.deg2rad(18))
    marks=dict(Cz=[0,0,100],Nz=[0,100,0],Iz=[0,-100,0],LPA=[-100,0,0],RPA=[100,0,0],Fpz=[0,r,z],Oz=[0,-r,z],T7=[-r,0,z],T8=[r,0,z])
    return v,tri,marks
class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v,cls.tri,cls.m=sphere();cls.model=TargetModel(cls.v,cls.tri,cls.m);cls.s=np.array([-50,30,np.sqrt(6600)])
    def test_cz_lateral_first_against_sphere(self):
        s,_=self.model.project(self.s);r=self.model.cz_lateral_first(s)
        self.assertEqual(r['lateral_direction'],'left');self.assertEqual(r['fore_direction'],'toward nose')
        self.assertAlmostEqual(r['lateral_mm'],100*np.arcsin(.5),delta=.15)
        self.assertAlmostEqual(r['fore_mm'],np.sqrt(7500)*np.arcsin(30/np.sqrt(7500)),delta=.15)
    def test_sgp_ratios(self):
        s,_=self.model.project(self.s);r=self.model.sgp(s)
        self.assertAlmostEqual(r['pAL'],1/3,delta=.001)
        self.assertAlmostEqual(r['pNZ'],np.arctan2(self.s[2],self.s[1])/np.pi,delta=.001)
        self.assertAlmostEqual(r['AL_to_target_mm']+r['AR_to_target_mm'],r['AL_target_AR_mm'],places=6)
    def test_cpc_inverse(self):
        s,_=self.model.project(self.s);r=self.model.sgp(s);p=self.model.from_cpc(r['pNZ'],r['pAL'])
        self.assertLess(np.linalg.norm(p-s),.1)
    def test_beam_style_sphere(self):
        s,_=self.model.project(self.s);r=self.model.beam_style(s)
        self.assertAlmostEqual(r['HC_mm'],2*np.pi*100*np.cos(np.deg2rad(18)),delta=.2)
        self.assertAlmostEqual(r['X_percent'],100*np.arctan2(50,30)/(2*np.pi),delta=.05)
        self.assertAlmostEqual(r['Y_mm'],100*np.arccos(self.s[2]/100),delta=.15)
    def test_rotation_translation_covariance(self):
        a=.4;rot=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
        off=np.array([14.,-22,30]);marks={k:np.array(v)@rot.T+off for k,v in self.m.items()}
        m=TargetModel(self.v@rot.T+off,self.tri,marks);r=m.measure(self.s@rot.T+off);base=self.model.measure(self.s)
        for method,field in [('SGP','pNZ'),('SGP','pAL'),('BEAM_style','X_mm'),('Cz_lateral_first','fore_mm')]:
            self.assertAlmostEqual(r['methods'][method][field],base['methods'][method][field],delta=.002)
    def test_same_segment_no_detour(self):
        c=Curve(np.array([[[0,0,0],[10,0,0]]],float));path,_=c.path([2,0,0],[3,0,0]);self.assertAlmostEqual(arc_length(path),1.)
    def test_zero_and_bad_cpc(self):
        r=self.model.measure(self.m['Cz']);self.assertLess(r['methods']['Cz_lateral_first']['lateral_mm'],.01)
        with self.assertRaises(ValueError):self.model.from_cpc(27,34)
    def test_missing_fiducials(self):
        marks=dict(self.m);del marks['Cz']
        with self.assertRaisesRegex(ValueError,'Cz'):TargetModel(self.v,self.tri,marks)
    def test_transformation_wiring(self):
        fake=types.ModuleType('simnibs');fake.mni2subject_coords=lambda p,sub,transformation_type:np.array(p)+[3,4,5];fake.subject2mni_coords=lambda p,sub,transformation_type:np.array(p)-[3,4,5]
        with tempfile.TemporaryDirectory() as temp,patch.dict(sys.modules,{'simnibs':fake}):
            with self.assertRaisesRegex(ValueError,'toMNI'):transform_mni([1,2,3],temp)
            (Path(temp)/'toMNI').mkdir();native,meta=transform_mni([1,2,3],temp)
            np.testing.assert_allclose(native,[4,6,8]);self.assertEqual(meta['roundtrip_error_mm'],0)
    def test_catalog_provenance(self):
        rows=json.loads((Path(__file__).parent/'targets.json').read_text())
        self.assertGreaterEqual(len(rows),7)
        for r in rows:self.assertEqual(len(r['mni']),3);self.assertTrue(r['url'].startswith('https://'));self.assertIn('MNI',r['space'])
if __name__=='__main__':unittest.main()
