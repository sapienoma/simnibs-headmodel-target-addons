# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
import unittest
import numpy as np
from surface_cleanup import clean_surface
class CleanupTests(unittest.TestCase):
 def setUp(self):
  self.v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,.5,1.]])
  self.t=np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]])
 def test_opposite_sheet_cancelled_without_moving_vertices(self):
  # Extra opposite pair on an already valid face leaves original boundary intact.
  v,t,r=clean_surface(self.v,np.vstack([self.t,self.t[0],self.t[0][::-1]]))
  np.testing.assert_array_equal(v,self.v);self.assertEqual(len(t),4);self.assertEqual(r['opposite_duplicate_pairs_cancelled'],1);self.assertEqual(r['nonmanifold_edges_remaining'],0)
 def test_same_winding_duplicate(self):
  _,t,r=clean_surface(self.v,np.vstack([self.t,self.t[0]]));self.assertEqual(len(t),4);self.assertEqual(r['same_winding_duplicates_removed'],1)
 def test_real_branch_rejected(self):
  with self.assertRaises(ValueError):clean_surface(self.v,np.vstack([self.t,[0,1,4]]))
 def test_zero_area_removed(self):
  _,t,r=clean_surface(self.v,np.vstack([self.t,[0,0,1]]));self.assertEqual(len(t),4);self.assertEqual(r['degenerate_faces_removed'],1)
if __name__=='__main__':unittest.main()
