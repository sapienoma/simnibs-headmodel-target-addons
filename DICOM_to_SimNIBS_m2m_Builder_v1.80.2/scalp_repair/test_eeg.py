# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
import csv,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import eeg_recompute as e
class EEGTests(unittest.TestCase):
 def test_projection_and_manifold(self):
  v=np.array([[0,0,0],[10,0,0],[0,10,0]],float);t=np.array([[0,1,2]])
  q,d=e.project(v,t,np.array([2,2,5]));np.testing.assert_allclose(q,[2,2,0]);self.assertAlmostEqual(d,5);self.assertEqual(len(e.boundary_vertices(v,t)),3)
 def test_csv_duplicate_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fid.csv';p.write_text('Fiducial,0,1,2,Nz\nFiducial,0,1,3,Nz\n')
   with self.assertRaises(ValueError):e.read_positions(p)
 def test_identical_cross_type_duplicate_merged(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fid.csv';p.write_text('Electrode,1,2,3,Iz\nFiducial,1,2,3,Iz\n');audit=[]
   points=e.read_positions(p,audit);np.testing.assert_allclose(points['Iz'],[1,2,3]);self.assertEqual(audit[0]['selected_type'],'Fiducial')
 def test_fiducial_priority_independent_of_order(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fid.csv'
   for rows in [('Electrode,1,2,3,Iz','Fiducial,4,5,6,Iz'),('Fiducial,4,5,6,Iz','Electrode,1,2,3,Iz')]:
    p.write_text('\n'.join(rows));np.testing.assert_allclose(e.read_positions(p)['Iz'],[4,5,6])
 def test_identical_electrodes_merged(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fid.csv';p.write_text('Electrode,1,2,3,C3\nElectrode,1,2,3,C3\n');self.assertEqual(len(e.read_positions(p)),1)
 def test_cli_handoff_and_delta(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);mask=p/'scalp_envelope_REVIEWED.nii.gz';mask.write_bytes(b'test')
   v=np.array([[100,0,0],[-100,0,0],[0,100,0],[0,-100,0],[0,0,100],[0,0,-100]],float);t=np.array([[0,2,4],[2,1,4],[1,3,4],[3,0,4],[2,0,5],[1,2,5],[3,1,5],[0,3,5]])
   ply=p/'scalp_surface_REVIEWED_RAS.ply'
   with ply.open('w') as f:
    f.write('ply\nformat ascii 1.0\nelement vertex 6\nproperty float x\nproperty float y\nproperty float z\nelement face 8\nproperty list uchar int vertex_indices\nend_header\n');np.savetxt(f,v);np.savetxt(f,np.c_[np.full(8,3),t],fmt='%d')
   (p/'manifest.json').write_text(json.dumps({'user_review':{'mask_sha256':e.digest(mask),'surface_sha256':e.digest(ply)}}))
   fid=p/'fid.csv';fid.write_text('Fiducial,0,100,0,Nz\nFiducial,0,-100,0,Iz\nFiducial,-100,0,0,LPA\nFiducial,100,0,0,RPA\nElectrode,0,0,95,Cz\n')
   def fake_run(args,check):
    self.assertEqual(args[3],'simnibs.cli.eeg_positions');out=Path(args[args.index('-o')+1]).with_suffix('.csv');out.write_text('ReferenceElectrode,0,0,100,Cz\n');self.assertIn('1005',Path(args[args.index('-m',4)+1]).read_text())
   with patch.object(e.importlib.util,'find_spec',return_value=object()),patch.object(e.subprocess,'run',side_effect=fake_run):out=e.run(p,fid)
   j=json.loads((out/'eeg_manifest.json').read_text());self.assertEqual(j['Cz_change_mm'],5);self.assertFalse(j['FEM']);self.assertEqual(j['point_count'],1)
 def test_unreviewed_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'manifest.json').write_text('{}')
   with self.assertRaises(ValueError):e.run(p,p/'none.csv')
if __name__=='__main__':unittest.main()
