# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Qt integration checks with native SimNIBS/OpenGL adapters mocked."""
import importlib.util,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from mesh_metrics import density
try:
 from PyQt5 import QtCore,QtWidgets
except ImportError:QtCore=QtWidgets=None
V=np.array([[0.,0,0],[10,0,0],[0,10,0],[0,0,10]])
T=np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]])
class MetricsTests(unittest.TestCase):
 def test_density_uses_unique_edges(self):
  d=density(V,T);self.assertEqual(d['triangles'],4);self.assertEqual(d['used_vertices'],4)
  self.assertAlmostEqual(d['mean_edge_mm'],(30+30*np.sqrt(2))/6)
 def test_invalid_indices_rejected(self):
  with self.assertRaises(ValueError):density(V,T+10)

@unittest.skipIf(QtWidgets is None,'requires installed PyQt5 (SimNIBS Python)')
class ScalpSwitchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import os
  os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
  cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
  class Native(QtWidgets.QMainWindow):
   def drawModel(self):self.drawn=self.headModelWidget.glHeadModel.skin_surf
   def loadHeadModel(self,fn):self.session.fnamehead=fn
   def generateNNAVSession(self):return self.session
  main=types.ModuleType('simnibs.GUI.main_gui');main.TDCS_GUI=Native;main.except_hook=lambda *a:None
  sf=types.ModuleType('simnibs.GUI.surface');sf.Surface=lambda m,tags:types.SimpleNamespace(nodes=m.nodes.node_coord,tr_nodes=m.elm.node_number_list[:,:3]-1)
  mesh=types.SimpleNamespace(nodes=types.SimpleNamespace(node_coord=V/2),elm=types.SimpleNamespace(elm_type=np.array([2]*4),tag1=np.array([1005]*4),node_number_list=np.column_stack([T+1,-np.ones(4,int)])))
  sim=types.ModuleType('simnibs');sim.mesh_io=types.SimpleNamespace(read_msh=lambda fn:mesh)
  cls.modules={'simnibs':sim,'simnibs.GUI':types.ModuleType('simnibs.GUI'),'simnibs.GUI.main_gui':main,'simnibs.GUI.surface':sf}
  with patch.dict(sys.modules,cls.modules):
   spec=importlib.util.spec_from_file_location('switch_gui_under_test',Path(__file__).with_name('simnibs_cz_gui.py'))
   cls.gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.gui)
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.folder=self.root/'m2m_demo';self.folder.mkdir();(self.folder/'eeg_positions').mkdir()
  self.fem=self.folder/'demo.msh';self.fem.write_text('FEM');self.surface=self.folder/'localization.msh';self.surface.write_text('SURFACE')
  self.original_csv=self.folder/'eeg_positions'/'EEG10-10_UI_Jurak_2007.csv';self.original_csv.write_text('OLD');self.csv=self.folder/'new.csv';self.csv.write_text('NEW')
  self.record={'fem':str(self.fem),'surface':str(self.surface),'eeg_csv':str(self.csv),'surface_sha256':'test'}
  QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat);QtCore.QSettings.setPath(QtCore.QSettings.IniFormat,QtCore.QSettings.UserScope,str(self.root/'settings'))
  self.mods=patch.dict(sys.modules,self.modules);self.mods.start()
  self.loader=patch('repair_assets.load_binding',side_effect=lambda *args:self.record);self.loader.start()
  import ui_language
  self.oldlang=ui_language.LANG;self.pref=patch.object(ui_language,'PREF',self.root/'lang.json');self.pref.start();ui_language.set_language('zh-TW')
  self.windows=[];self.w,self.p,self.gl,self.original=self.window()
 def tearDown(self):
  import ui_language
  ui_language.set_language(self.oldlang);self.pref.stop();self.loader.stop();self.mods.stop()
  for w in self.windows:w.close()
  self.t.cleanup()
 def window(self):
  w=self.gui.CompanionWindow();self.windows.append(w);original=types.SimpleNamespace(nodes=V.copy(),tr_nodes=T.copy())
  gl=types.SimpleNamespace(skin_surf=original,intersect_point=None,indicator=0,makeCurrent=lambda:None,doneCurrent=lambda:None,drawModel=lambda n:1,setEEG=lambda p:None,selectRenderSurface=lambda n:None,update=lambda:None)
  w.headModelWidget=types.SimpleNamespace(glHeadModel=gl);w.session=types.SimpleNamespace(fnamehead=str(self.fem),eeg_cap=str(self.original_csv),poslists=[])
  w.file_name=QtWidgets.QLineEdit(str(self.fem));p=self.gui.TargetPanel(w);w.target_panel=p;p.timer.stop();p.notify=lambda message:None
  p.observe_model();return w,p,gl,original
 def test_bidirectional_switch_keeps_correct_pair_and_fem(self):
  self.assertEqual(self.p.scalp_mode,'repaired');repaired=self.gl.skin_surf
  for _ in range(2):
   self.p.scalp_selector.setCurrentIndex(0);self.assertIs(self.gl.skin_surf,self.original);self.assertEqual(self.w.session.eeg_cap,str(self.original_csv));self.assertEqual(self.p.paths()[0],str(self.fem))
   self.p.scalp_selector.setCurrentIndex(1);self.assertIs(self.gl.skin_surf,repaired);self.assertEqual(self.w.session.eeg_cap,str(self.csv));self.assertEqual(self.p.paths()[0],str(self.surface))
   self.assertEqual(self.w.session.fnamehead,str(self.fem))
 def test_stale_measurements_and_current_point_cleared(self):
  for index in [0,1]:
   self.p.last_result={'old':True};self.p.engine=object();self.p.pending=np.array([1,2,3]);self.gl.intersect_point=np.array([1,2,3]);self.gl.indicator=55
   self.p.scalp_selector.setCurrentIndex(index)
   self.assertIsNone(self.p.last_result);self.assertIsNone(self.p.engine);self.assertIsNone(self.p.pending);self.assertIsNone(self.gl.intersect_point);self.assertEqual(self.gl.indicator,0)
 def test_mode_saved_per_mesh_without_patient_autoload(self):
  self.p.scalp_selector.setCurrentIndex(0);w,p,gl,orig=self.window();self.assertEqual(p.scalp_mode,'original');self.assertTrue(p.scalp_selector.model().item(1).isEnabled())
  p.scalp_selector.setCurrentIndex(1);w,p,gl,orig=self.window();self.assertEqual(p.scalp_mode,'repaired')
 def test_busy_calculation_blocks_switch(self):
  self.p.worker=types.SimpleNamespace(isRunning=lambda:True);self.p.scalp_selector.setCurrentIndex(0)
  self.assertEqual(self.p.scalp_mode,'repaired');self.assertEqual(self.p.scalp_selector.currentIndex(),1);self.p.worker=None
 def test_hybrid_label_and_original_option_preserved(self):
  self.record['surface_kind']='hybrid';self.p.set_scalp_mode('original');self.p.set_scalp_mode('repaired');self.p.language.setCurrentIndex(1)
  self.assertIn('Hybrid scalp',self.p.scalp_selector.itemText(1));self.assertIn('Original T1',self.p.scalp_selector.itemText(0))
  self.p.set_scalp_mode('original');self.assertIs(self.gl.skin_surf,self.original)
 def test_launch_hybrid_passes_original_m2m(self):
  with patch.object(self.gui.QtCore.QProcess,'startDetached',return_value=(True,123)) as launch:
   self.p.open_hybrid_builder()
  args=launch.call_args.args[1];self.assertEqual(args[args.index('--original-msh')+1],str(self.fem));self.assertIn('scalp_repair',args[0])
 def test_no_repair_disables_option(self):
  self.record=None;w,p,gl,orig=self.window();self.assertEqual(p.scalp_mode,'original');self.assertFalse(p.scalp_selector.model().item(1).isEnabled())
 def test_missing_repair_falls_back_to_original(self):
  self.p.set_scalp_mode('original');self.record=None;self.p.scalp_selector.setCurrentIndex(1)
  self.assertEqual(self.p.scalp_mode,'original');self.assertIs(self.gl.skin_surf,self.original);self.assertEqual(self.w.session.eeg_cap,str(self.original_csv))
 def test_reset_on_other_model_clears_cached_pair(self):
  self.w.loadHeadModel(str(self.folder/'other.msh'));self.assertIsNone(self.p.available_binding);self.assertIsNone(self.p.binding);self.assertIsNone(self.p._repaired_skin);self.assertFalse(self.p.scalp_selector.isEnabled())
 def test_density_display_and_session_guard_follow_mode(self):
  self.assertGreater(self.p._mesh_metrics['original']['mean_edge_mm'],self.p._mesh_metrics['repaired']['mean_edge_mm'])
  self.p.language.setCurrentIndex(1);self.assertIn('mean edge length',self.p.mesh_comparison.text());self.assertIn('Original T1',self.p.scalp_selector.itemText(0))
  self.w.session.poslists=[types.SimpleNamespace(type='TDCSLIST',electrode=[1])]
  with self.assertRaises(ValueError):self.w.generateNNAVSession()
  self.p.scalp_selector.setCurrentIndex(0);self.assertIs(self.w.generateNNAVSession(),self.w.session)
if __name__=='__main__':unittest.main()
