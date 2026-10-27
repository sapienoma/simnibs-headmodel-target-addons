# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""SimNIBS 4.6 integrated targeting panel v2.4."""
from ui_language import tr
import csv,html,json,sys,traceback,webbrowser
from pathlib import Path
import numpy as np
from PyQt5 import QtCore,QtGui,QtWidgets
from simnibs.GUI.main_gui import TDCS_GUI,except_hook
from target_geometry import TargetModel,unit
from target_workflow import transform_mni

BASE=Path(__file__).resolve().parent

def fmtpoint(p):return ', '.join(f'{v:.3f}' for v in p)
def mm(value):return f'{value:.2f} mm ({value/10:.2f} cm)'

class Worker(QtCore.QThread):
    result=QtCore.pyqtSignal(object)
    failure=QtCore.pyqtSignal(str)
    def __init__(self,panel,key,request):
        super().__init__(panel);self.panel=panel;self.key=key;self.request=request
    def run(self):
        try:
            if self.panel.engine_key!=self.key:
                self.panel.engine=TargetModel.from_files(self.key[0],self.key[1]);self.panel.engine_key=self.key
            model=self.panel.engine;req=self.request;kind=req['kind'];meta={}
            if kind=='mni':
                native,meta=transform_mni(req['point'],Path(self.key[2]).parent)
                p=native;meta['preset']=req.get('preset')
            elif kind=='cpc':
                p=model.from_cpc(*req['point']);meta=dict(external_CPC=req['point'],note='User-entered CPC; not automatically verified against MNI2CPC lookup.')
            else:
                p=np.asarray(req['point'],float)
                _,distance=model.project(p)
                if distance>2:raise ValueError(tr('Current Position is >2 mm from scalp. Select Scalp and double-click.'))
            result=model.measure(p);result.update(source=kind,metadata=meta,scalp_source_kind=(self.panel.binding or {}).get('surface_kind','original' if self.key[0]==self.key[2] else 'repaired'),mesh=self.key[0],eeg_csv=self.key[1],fem_mesh=self.key[2],input_mtimes=list(self.key[3:]),geometry_mode='REPAIRED_LOCALIZATION_ORIGINAL_FEM' if self.key[0]!=self.key[2] else 'ORIGINAL_FEM_SCALP')
            if result['projection_distance_mm']>50:result.setdefault('warnings',[]).append(tr('腦內點距頭皮超過 50 mm，請核對轉換與解剖位置。'))
            if meta.get('roundtrip_error_mm',0)>2:result.setdefault('warnings',[]).append(tr('MNI 正反向誤差超過 2 mm，請檢查配準。'))
            self.result.emit(result)
        except Exception as exc:
            traceback.print_exc();self.failure.emit(str(exc))

class TargetPanel(QtWidgets.QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.engine=None;self.engine_key=None;self.worker=None;self.last_point_key=None;self.pending=None;self.last_result=None
        self.catalog=json.loads((BASE/'targets.json').read_text(encoding='utf-8'))
        self.settings=QtCore.QSettings('SimNIBSCompanion','CzDistanceTool')
        self._observed_mesh=None;self.binding=None;self._original_skin=None;self._original_cap=None;self._binding_error=None;self.available_binding=None;self.scalp_mode='original';self._mesh_metrics={};self._repaired_skin=None;self._repaired_skin_key=None
        layout=QtWidgets.QVBoxLayout(self)
        bar=QtWidgets.QHBoxLayout();layout.addLayout(bar)
        for text,callback in [(tr('載入 m2m 模型'),self.choose_model),(tr('匯出結果 JSON／CSV'),self.export),(tr('標記頭皮點於 GUI'),self.mark)]:
            b=QtWidgets.QPushButton(text);b.clicked.connect(callback);bar.addWidget(b)
        self.recent=QtWidgets.QPushButton(tr('開啟最近的 m2m'));self.recent.clicked.connect(self.open_recent);bar.addWidget(self.recent);self.refresh_recent()
        repairbar=QtWidgets.QHBoxLayout();layout.addLayout(repairbar)
        b=QtWidgets.QPushButton(tr('匯入修補頭皮／EEG…'));b.clicked.connect(self.import_repaired);repairbar.addWidget(b)
        b=QtWidgets.QPushButton(tr('建立混合頭皮…'));b.clicked.connect(self.open_hybrid_builder);repairbar.addWidget(b)
        repairbar.addWidget(QtWidgets.QLabel(tr('頭皮模型')))
        self.scalp_selector=QtWidgets.QComboBox();self.scalp_selector.setObjectName('scalpModelSelector')
        self.scalp_selector.addItem(tr('原始 T1／m2m 頭皮＋原始 EEG'),'original');self.scalp_selector.addItem(tr('修補頭皮＋新 EEG'),'repaired')
        self.scalp_selector.setEnabled(False);self.scalp_selector.currentIndexChanged.connect(self.scalp_selection_changed);repairbar.addWidget(self.scalp_selector)
        self.mesh_comparison=QtWidgets.QLabel('');self.mesh_comparison.setWordWrap(True);layout.addWidget(self.mesh_comparison)
        self.asset_status=QtWidgets.QLabel(tr('頭皮／EEG：尚未載入'));self.asset_status.setWordWrap(True);layout.addWidget(self.asset_status)
        self.route=QtWidgets.QComboBox();self.route.addItems([tr('Cz：左右→前後'),'BEAM-style','SGP']);bar.addWidget(self.route)
        self.tabs=QtWidgets.QTabWidget();self.tabs.setMaximumHeight(235);layout.addWidget(self.tabs)
        current=QtWidgets.QWidget();box=QtWidgets.QVBoxLayout(current)
        self.auto=QtWidgets.QCheckBox(tr('雙擊頭皮後自動計算三種量測'));self.auto.setChecked(True);box.addWidget(self.auto)
        b=QtWidgets.QPushButton(tr('讀取 GUI Current Position 並計算'));b.clicked.connect(self.current);box.addWidget(b)
        label=QtWidgets.QLabel(tr('請選 Scalp，於模型雙擊。直接讀取 GUI 座標，不讀取 TMS 表格。'));label.setWordWrap(True);box.addWidget(label);box.addStretch();self.tabs.addTab(current,'GUI Current Position')
        mni=QtWidgets.QWidget();box=QtWidgets.QVBoxLayout(mni)
        self.presets=QtWidgets.QComboBox();self.presets.addItem(tr('自訂 MNI（請輸入 X／Y／Z）'),None)
        for item in self.catalog:self.presets.addItem(item['name'],item)
        self.presets.currentIndexChanged.connect(self.preset_changed);box.addWidget(self.presets)
        row=QtWidgets.QHBoxLayout();self.mni_fields=[]
        for name in ('X','Y','Z'):
            row.addWidget(QtWidgets.QLabel(name));edit=QtWidgets.QLineEdit();edit.setPlaceholderText('mm');row.addWidget(edit);self.mni_fields.append(edit)
        box.addLayout(row)
        self.info=QtWidgets.QLabel(tr('MNI 世界座標（mm），不是 voxel index。X 正值為右，Y 正值為前，Z 正值為上。'));self.info.setWordWrap(True);box.addWidget(self.info)
        row=QtWidgets.QHBoxLayout();box.addLayout(row)
        self.mni_button=QtWidgets.QPushButton(tr('MNI → 個人腦內點 → 最近頭皮點 → 三種量測'));self.mni_button.clicked.connect(self.mni);row.addWidget(self.mni_button)
        b=QtWidgets.QPushButton(tr('開啟此靶點文獻'));b.clicked.connect(self.source);row.addWidget(b)
        box.addStretch();self.tabs.addTab(mni,tr('MNI 靶點與自訂座標'))
        cpc=QtWidgets.QWidget();box=QtWidgets.QVBoxLayout(cpc)
        note=QtWidgets.QLabel(tr('選用：若你已從作者 MNI2CPC 工具查得比例，可在此輸入。此功能將外部比例套到個人頭皮；不會將本工具的個人幾何計算冒稱為群體 MNI2CPC 查表。'));note.setWordWrap(True);box.addWidget(note)
        row=QtWidgets.QHBoxLayout();self.cpc_fields=[]
        for name in ('pNZ','pAL'):
            row.addWidget(QtWidgets.QLabel(name));edit=QtWidgets.QLineEdit();edit.setPlaceholderText(tr('0–1 比例'));row.addWidget(edit);self.cpc_fields.append(edit)
        box.addLayout(row);row=QtWidgets.QHBoxLayout();box.addLayout(row)
        b=QtWidgets.QPushButton(tr('套用外部 CPC 並量測'));b.clicked.connect(self.cpc);row.addWidget(b)
        b=QtWidgets.QPushButton(tr('開啟作者 MNI2CPC 工具'));b.clicked.connect(lambda:webbrowser.open('https://transcranial-brain-atlas.org/mni2cpc/'));row.addWidget(b)
        box.addStretch();self.tabs.addTab(cpc,tr('外部 MNI2CPC 比例'))
        self.result=QtWidgets.QTextBrowser();self.result.setOpenExternalLinks(False);self.result.setMinimumHeight(220);layout.addWidget(self.result)
        self.result.setPlainText(tr('載入完整 m2m 資料夾後開始。MNI 轉換需要 toMNI；距離量測需要 EEG CSV 的 Cz／Nz／Iz／LPA／RPA。'))
        from ui_language import install_qt
        self.language=install_qt(self,layout,lambda:self.language_changed())
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(500)
    def language_changed(self):
        from ui_language import qt_translate
        qt_translate(self.window);self.preset_changed()
        self.sync_scalp_label();self.update_mesh_comparison()
        if self.last_result:self.show_result(self.last_result)
        else:
            from ui_language import source
            self.result.setPlainText(tr(source(self.result.toPlainText())))
    def notify(self,text):QtWidgets.QMessageBox.warning(self,tr('Targeting tool'),tr(str(text)))
    def refresh_recent(self):
        recent=str(self.settings.value('recent_m2m','') or '')
        self.recent.setEnabled(bool(recent) and Path(recent).is_dir())
        self.recent.setToolTip(recent if recent else tr('尚無最近使用紀錄；請手動載入 m2m。'))
    def open_recent(self):
        folder=str(self.settings.value('recent_m2m','') or '')
        if not folder or not Path(folder).is_dir():
            self.refresh_recent();return self.notify(tr('Recent m2m folder no longer exists; select manually.'))
        self.load_folder(folder)
    def choose_model(self):
        if self.worker is not None and self.worker.isRunning():return self.notify(tr('Wait for the current calculation to finish.'))
        recent=str(self.settings.value('recent_m2m','') or '')
        initial=recent if recent and Path(recent).is_dir() else r'C:\SimNIBS_Data\Projects'
        folder=QtWidgets.QFileDialog.getExistingDirectory(self,tr('選擇 m2m 資料夾'),initial)
        if folder:self.load_folder(folder)
    def load_folder(self,folder):
        if self.worker is not None and self.worker.isRunning():return self.notify(tr('Wait for the current calculation to finish.'))
        from repair_assets import find_fem
        path=Path(folder)
        try:
            from repair_assets import ensure_reviewable
            ensure_reviewable(path);files=[find_fem(path)]
        except ValueError as e:return self.notify(e)
        self.last_result=None;self.last_point_key=None;self.pending=None
        gl=self.window.headModelWidget.glHeadModel
        gl.intersect_point=None;gl.indicator=0
        self.reset_scalp_sources()
        self._observed_mesh=None;self._original_skin=None
        self.window.session.eeg_cap=None;self.window.session.subpath=''
        self.window.loadHeadModel(str(files[0]))
        self.result.setPlainText(tr('模型載入中。請等待頭部顯示，再選位點或輸入 MNI。'))
    def observe_model(self):
        # Also remember models opened through SimNIBS's own File menu.
        try:
            mesh=Path(str(self.window.session.fnamehead or ''))
            thread=getattr(self.window,'loadThread',None)
            if thread is not None and thread.isRunning():return
            gl=self.window.headModelWidget.glHeadModel
            if not mesh.is_file() or getattr(gl,'skin_surf',None) is None:return
            identity=str(mesh.resolve())
            if identity!=self._observed_mesh:
                self._observed_mesh=identity;self.last_result=None;self.last_point_key=None;self.pending=None
                self._original_skin=gl.skin_surf
                original_csv=mesh.parent/'eeg_positions'/'EEG10-10_UI_Jurak_2007.csv'
                self._original_cap=str(original_csv) if original_csv.is_file() else self.window.session.eeg_cap
                try:
                    from repair_assets import load_binding
                    self.available_binding=load_binding(mesh.parent,mesh);self._binding_error=None;self.sync_scalp_label()
                    preferred=str(self.settings.value(self.scalp_setting_key(mesh),'repaired' if self.available_binding else 'original'))
                    self.set_scalp_mode(preferred if self.available_binding else 'original',persist=False)
                except Exception as e:
                    self.binding=None;self.available_binding=None;self._binding_error=None
                    self.set_scalp_mode('original',persist=False)
                    self.asset_status.setText(tr('Repair unavailable; reverted to the original scalp: ')+str(e))
                self.settings.setValue('recent_m2m',str(mesh.resolve().parent));self.settings.sync();self.refresh_recent()
                self.result.setPlainText(tr('模型已載入。請雙擊頭皮，或在 MNI 分頁選擇／輸入座標。'))
        except (AttributeError,OSError):pass
    def open_hybrid_builder(self):
        if self.worker is not None and self.worker.isRunning():return self.notify(tr('Wait for the current calculation to finish.'))
        mesh=Path(str(self.window.session.fnamehead or ''))
        if not mesh.is_file():return self.notify(tr('Load a head model first.'))
        script=BASE/'scalp_repair'/'gui.py'
        if not script.is_file():script=BASE.parent/'scalp_repair'/'gui.py'
        if not script.is_file():return self.notify(tr('Hybrid tool missing; extract the complete v1.80.2 archive.'))
        ok=QtCore.QProcess.startDetached(sys.executable,[str(script),'--original-msh',str(mesh),'--output',str(mesh.parent.parent/'ScalpRepair')])
        started=ok[0] if isinstance(ok,tuple) else ok
        if not started:self.notify(tr('Could not start the hybrid repair tool.'))
    def sync_scalp_label(self):
        hybrid=bool(self.available_binding and self.available_binding.get('surface_kind')=='hybrid')
        source='混合頭皮＋重算 EEG' if hybrid else '修補頭皮＋新 EEG'
        self.scalp_selector.setItemText(1,tr(source))
        self.scalp_selector.setItemData(1,source,QtCore.Qt.UserRole+71)
    def import_repaired(self):
        if self.worker is not None and self.worker.isRunning():return self.notify(tr('Wait for the current calculation to finish.'))
        mesh=Path(str(self.window.session.fnamehead or ''))
        if not mesh.is_file():return self.notify(tr('Load a head model first.'))
        thread=getattr(self.window,'loadThread',None)
        if thread is not None and thread.isRunning():return self.notify(tr('Model still loading; please wait.'))
        from repair_ui import RepairDialog
        dialog=RepairDialog(self,str(mesh.parent));self.import_dialog=dialog
        if dialog.exec_()==QtWidgets.QDialog.Accepted:
            # Importing into another m2m must also load that FEM before applying its overlay.
            folder=Path(dialog.fields[0].text()).resolve()
            self.settings.setValue(self.scalp_setting_key(__import__('repair_assets').find_fem(folder)),'repaired')
            self.load_folder(str(folder))
    def apply_overlay(self):
        if not self.binding:return
        self._bound_signature=None
        from simnibs import mesh_io
        from simnibs.GUI.surface import Surface
        gl=self.window.headModelWidget.glHeadModel
        gl.makeCurrent()
        try:
            cache_key=(self.binding['surface'],self.binding['surface_sha256'])
            if self._repaired_skin_key!=cache_key:
                self._repaired_skin=Surface(mesh_io.read_msh(self.binding['surface']),[5,1005]);self._repaired_skin_key=cache_key
                self._repaired_skin.mesh_name=self.binding['surface']
            replacement=self._repaired_skin
            gl.skin_surf=replacement;gl.skin_model=gl.drawModel('Skin')
            self.window.session.eeg_cap=self.binding['eeg_csv']
            gl.setEEG(self.binding['eeg_csv']);gl.intersect_point=None;gl.indicator=0
            gl.selectRenderSurface('Skin');gl.update()
            if hasattr(self.window,'changeGlStimulators'):self.window.changeGlStimulators()
        except Exception:
            # Never leave a partly installed surface paired with the old cap.
            if self._original_skin is not None:gl.skin_surf=self._original_skin
            self.window.session.eeg_cap=self._original_cap
            raise
        finally:gl.doneCurrent()
        self.engine=None;self.engine_key=None;self.last_result=None;self.last_point_key=None;self.pending=None
        text=tr('混合頭皮與重算 EEG 已套用；請目視檢查接縫。TMS 定位使用混合表面，電場仍使用原始 FEM。\nMSH: ') if self.binding.get('surface_kind')=='hybrid' else tr('修補頭皮與新 EEG 已套用。TMS 線圈位置依修補表面；電場使用原始體積 FEM。\nMSH: ')
        self.asset_status.setText(text+self.binding['surface']+'\nEEG: '+self.binding['eeg_csv'])
    def reset_scalp_sources(self):
        self.binding=None;self.available_binding=None;self._binding_error=None;self.scalp_mode='original'
        self._repaired_skin=None;self._repaired_skin_key=None;self._mesh_metrics={}
        self.scalp_selector.blockSignals(True);self.scalp_selector.setCurrentIndex(0);self.scalp_selector.setEnabled(False);self.scalp_selector.blockSignals(False)
        self.mesh_comparison.clear()
    def scalp_setting_key(self,mesh=None):
        import hashlib,os
        identity=os.path.normcase(str(Path(mesh or self.window.session.fnamehead).resolve()))
        return 'scalp_mode/'+hashlib.sha256(identity.encode('utf-8')).hexdigest()
    def scalp_selection_changed(self):
        self.set_scalp_mode(self.scalp_selector.currentData())
    def reset_measurement(self):
        gl=self.window.headModelWidget.glHeadModel;gl.intersect_point=None;gl.indicator=0
        self.engine=None;self.engine_key=None;self.last_result=None;self.last_point_key=None;self.pending=None
        self.result.setPlainText(tr('頭皮模型已切換。舊測量已清除，請重新雙擊頭皮或計算 MNI 位點；既有 TMS 表格位置請重新核對。'))
    def set_scalp_mode(self,mode,persist=True):
        previous=self.scalp_mode
        if self.worker is not None and self.worker.isRunning():
            self.scalp_selector.blockSignals(True);self.scalp_selector.setCurrentIndex(1 if previous=='repaired' else 0);self.scalp_selector.blockSignals(False)
            return self.notify(tr('Wait for the current calculation to finish.'))
        if self._original_skin is None:return
        self.reset_measurement()
        try:
            if mode=='repaired':
                from repair_assets import load_binding
                mesh=Path(str(self.window.session.fnamehead));candidate=load_binding(mesh.parent,mesh)
                if not candidate:raise ValueError(tr('No repaired pair available. Import the repaired MSH and EEG CSV first.'))
                if not self.available_binding or self.available_binding.get('surface_sha256')!=candidate['surface_sha256']:self._mesh_metrics.pop('repaired',None)
                self.available_binding=candidate;self.binding=candidate;self._binding_error=None;self.sync_scalp_label()
                self.apply_overlay();self.scalp_mode='repaired'
            else:
                # Keep the saved pair available for switching back without reimport.
                if self.binding:self.available_binding=self.binding
                self.binding=None;self._binding_error=None;self.scalp_mode='original'
                self.render_original()
                self.asset_status.setText(tr('Using original scalp + original EEG. Fields use the original volume FEM.')+'\nEEG: '+str(self._original_cap or ''))
            self.reset_measurement()
            self.scalp_selector.blockSignals(True);self.scalp_selector.setEnabled(True)
            self.scalp_selector.model().item(1).setEnabled(self.available_binding is not None)
            self.scalp_selector.setCurrentIndex(1 if self.scalp_mode=='repaired' else 0);self.scalp_selector.blockSignals(False)
            if persist:self.settings.setValue(self.scalp_setting_key(),self.scalp_mode);self.settings.sync()
            self.update_mesh_comparison()
        except Exception as e:
            # Fall back to a complete, consistent original surface/cap pair.
            self.binding=None;self._binding_error=None;self.scalp_mode='original'
            self.render_original();self.reset_measurement()
            self.scalp_selector.blockSignals(True);self.scalp_selector.setCurrentIndex(0);self.scalp_selector.blockSignals(False)
            self.asset_status.setText(tr('Could not switch to repaired scalp; using the original scalp: ')+str(e));self.notify(e)
    def render_original(self):
        gl=self.window.headModelWidget.glHeadModel;gl.skin_surf=self._original_skin
        self.window.session.eeg_cap=self._original_cap;gl.makeCurrent()
        try:
            self.window.drawModel()
            if hasattr(self.window,'changeGlStimulators'):self.window.changeGlStimulators()
        finally:gl.doneCurrent()
    def restore_original(self):
        self.set_scalp_mode('original')
    def update_mesh_comparison(self):
        from mesh_metrics import density
        if self._original_skin is None:return
        try:
            if 'original' not in self._mesh_metrics:
                self._mesh_metrics['original']=density(self._original_skin.nodes,self._original_skin.tr_nodes)
            if self.available_binding and 'repaired' not in self._mesh_metrics:
                from simnibs import mesh_io
                m=mesh_io.read_msh(self.available_binding['surface']);mask=(m.elm.elm_type==2)&(m.elm.tag1==1005)
                self._mesh_metrics['repaired']=density(m.nodes.node_coord,m.elm.node_number_list[mask,:3]-1)
            parts=[]
            for key,label in [('original',tr('原始頭皮')),('repaired',tr('混合頭皮') if self.available_binding and self.available_binding.get('surface_kind')=='hybrid' else tr('修補頭皮'))]:
                d=self._mesh_metrics.get(key)
                if d:parts.append(tr('{0}：{1:,} 個三角面；平均邊長 {2:.3f} mm').format(label,d['triangles'],d['mean_edge_mm']))
            parts.append(tr('以上為表面網格細緻度，不代表 MRI 解剖解析度。'))
            self.mesh_comparison.setText(' | '.join(parts))
        except (AttributeError,ValueError,OSError):
            self.mesh_comparison.setText(tr('網格細緻度資訊暫不可用；模型切換仍可使用。'))
    def paths(self):
        mesh=Path(str(self.window.session.fnamehead or ''))
        if not mesh.is_file():raise ValueError(tr('Load a head model first.'))
        if self._binding_error:raise ValueError(self._binding_error)
        surface=Path(self.binding['surface']) if self.binding else mesh
        cap=Path(self.binding['eeg_csv']) if self.binding else Path(str(self.window.session.eeg_cap or mesh.parent/'eeg_positions'/'EEG10-10_UI_Jurak_2007.csv'))
        if not cap.is_file():raise ValueError(tr('EEG10-10_UI_Jurak_2007.csv missing beside this model. Use the complete m2m folder.'))
        if self.binding:
            signature=tuple((Path(self.binding[k]).stat().st_mtime_ns,Path(self.binding[k]).stat().st_size) for k in ('fem','surface','eeg_csv'))
            if signature!=getattr(self,'_bound_signature',None):
                from repair_assets import load_binding
                load_binding(mesh.parent,mesh);self._bound_signature=signature
        # Cache is invalidated when either actual measurement input changes.
        return (str(surface.resolve()),str(cap.resolve()),str(mesh.resolve()),surface.stat().st_mtime_ns,cap.stat().st_mtime_ns)
    def point(self):
        p=getattr(self.window.headModelWidget.glHeadModel,'intersect_point',None)
        if p is None:return None
        p=np.asarray(p,float).reshape(-1)
        return p.copy() if p.shape==(3,) and np.isfinite(p).all() else None
    def poll(self):
        self.observe_model()
        if self.tabs.currentIndex()!=0 or not self.auto.isChecked():return
        p=self.point()
        if p is None:return
        try:key=(self.paths(),tuple(np.round(p,6)))
        except ValueError:return
        if key!=self.last_point_key:self.last_point_key=key;self.pending=p
        if self.pending is not None and (self.worker is None or not self.worker.isRunning()):
            p=self.pending;self.pending=None;self.start(dict(kind='current',point=p.tolist()))
    def current(self):
        p=self.point()
        if p is None:return self.notify(tr('Double-click the scalp to obtain Current Position first.'))
        self.start(dict(kind='current',point=p.tolist()))
    def preset_changed(self):
        item=self.presets.currentData()
        for i,edit in enumerate(self.mni_fields):edit.setText(str(item['mni'][i]) if item else '')
        if item:self.info.setText(tr(item['evidence_type']+'\n'+item['source']+'\n'+item['note']))
        else:self.info.setText(tr('請輸入 MNI 世界座標（mm，RAS）；不能直接輸入 Talairach 或影像 voxel index。'))
    def source(self):
        item=self.presets.currentData()
        if item:webbrowser.open(item['url'])
    def mni(self):
        try:
            values=[float(e.text()) for e in self.mni_fields]
            if not np.isfinite(values).all():raise ValueError(tr('Coordinates must be finite numbers.'))
            self.start(dict(kind='mni',point=values,preset=self.presets.currentData()))
        except ValueError as e:self.notify(tr('Check MNI X/Y/Z: ')+str(e))
    def cpc(self):
        try:
            values=[float(e.text()) for e in self.cpc_fields]
            if not all(0<x<1 for x in values):raise ValueError(tr('Enter proportions from 0 to 1 (e.g. 0.27, not 27).'))
            self.start(dict(kind='cpc',point=values))
        except ValueError as e:self.notify(e)
    def start(self,request):
        if self.worker is not None and self.worker.isRunning():return self.notify(tr('Wait for the current calculation to finish.'))
        try:key=self.paths()
        except ValueError as e:return self.notify(e)
        self.last_result=None;self.result.setPlainText(tr('計算中…首次需讀取網格；結果尚未完成。'))
        self.worker=Worker(self,key,request);self.worker.result.connect(self.show_result);self.worker.failure.connect(self.failed);self.worker.start()
    def failed(self,text):self.last_result=None;self.result.setPlainText(tr('未能計算：')+text)
    def show_result(self,r):
        try:
            if self.paths()[:3]!=(r['mesh'],r['eeg_csv'],r['fem_mesh']) or list(self.paths()[3:])!=r['input_mtimes']:return
        except ValueError:return
        self.last_result=r;parts=[tr('<b>個人頭皮 XYZ（mm）</b>：')+fmtpoint(r['scalp'])]
        parts+=['FEM: '+html.escape(r['fem_mesh']),'Scalp: '+html.escape(r['mesh']),'EEG: '+html.escape(r['eeg_csv'])]
        if r['geometry_mode']=='REPAIRED_LOCALIZATION_ORIGINAL_FEM':parts+=[tr('修補表面用於測距／TMS 定位；體積 FEM 未修改。')]
        meta=r['metadata']
        if 'native_brain_mm' in meta:
            parts+=['MNI：'+fmtpoint(meta['MNI_mm']),tr('個人腦內 XYZ：')+fmtpoint(meta['native_brain_mm']),tr(f"MNI 正反向誤差：{meta['roundtrip_error_mm']:.3f} mm")]
            if meta.get('preset'):parts+=[tr('文獻：')+html.escape(tr(meta['preset']['source'])),tr('備註：')+html.escape(tr(meta['preset']['note']))]
        parts+=[tr('輸入點至最近頭皮距離：')+mm(r['projection_distance_mm'])]
        for warning in r.get('warnings',[]):parts+=[tr('<b>需核對：</b>')+html.escape(warning)]
        a=r['methods'].get('Cz_lateral_first');parts+=[tr('<hr><b>① Cz：先左右，再往前／後</b>')]
        if a:
            side=tr('右') if a['lateral_direction']=='right' else tr('左');fore=tr('鼻部／前方') if a['fore_direction']=='toward nose' else tr('枕部／後方')
            parts += [tr(f"從 Cz 向{side}：{mm(a['lateral_mm'])}；再向{fore}：{mm(a['fore_mm'])}")]
        else:parts+=[html.escape(r['errors'].get('Cz_lateral_first',tr('無結果')))]
        a=r['methods'].get('BEAM_style');parts+=[tr('<hr><b>② BEAM-style X／Y（指定靶點的幾何表示）</b>')]
        if a:
            side=tr('右') if a['side']=='right' else tr('左')
            parts += [tr(f"頭圍 HC：{mm(a['HC_mm'])}"),tr(f"X：從 Fpz 沿頭圍向{side} {mm(a['X_mm'])}（HC 的 {a['X_percent']:.2f}%）"),tr(f"Y：從 Cz 沿通往該頭圍足點的弧線移動 {mm(a['Y_mm'])}"),tr('這不是原始 Beam F3 的預測位置，也不是 adjusted Beam F3。'),tr(f"文獻 F3 平均比例近似參考（非本靶點）：X ≈ {a['F3_mean_proportion_reference']['X_mm']:.2f} mm，Y ≈ {a['F3_mean_proportion_reference']['Y_mm']:.2f} mm；此近似不是原始 Beam F3 完整演算法。")]
        else:parts+=[html.escape(r['errors'].get('BEAM_style',tr('無結果')))]
        a=r['methods'].get('SGP');parts+=[tr('<hr><b>③ SGP／個人 CPC</b>')]
        if a:
            fore=tr('鼻部／前方') if a['fore_direction']=='toward nose' else tr('枕部／後方')
            parts += [f"pNZ = {a['pNZ']:.5f}；pAL = {a['pAL']:.5f}",tr(f"Nz–Cz–Iz 全弧長：{mm(a['NI_mm'])}"),tr(f"從 Nz 沿中線向枕部量 {mm(a['Nz_to_intersection_mm'])}，標記 s′"),tr(f"也可從 Cz 向{fore}量 {mm(a['Cz_to_intersection_mm'])} 到 s′"),tr(f"將量尺由左耳前 AL 經 s′ 到右耳前 AR（全弧長 {mm(a['AL_target_AR_mm'])}）；沿此弧從 AL 量 {mm(a['AL_to_target_mm'])} 即達靶點"),tr(f"反向從 AR 量 {mm(a['AR_to_target_mm'])}"),tr('此為個人頭皮幾何比例；不是作者群體 MNI2CPC 查表或其誤差估計。')]
        else:parts+=[html.escape(r['errors'].get('SGP',tr('無結果')))]
        parts+=[tr('<hr>三種路徑皆在三角頭皮表面的切面交線上量測，不等於自由最短測地線。MNI 最近頭皮投影不等於最佳電場位置／線圈方向。')]
        self.result.setHtml('<br>'.join(parts))
    def mark(self):
        if self.last_result is None:return self.notify(tr('Calculate a point first.'))
        if self.worker is not None and self.worker.isRunning():return
        try:
            gl=self.window.headModelWidget.glHeadModel;p=np.array(self.last_result['scalp']);_,_,idx=__import__('scalp_arcs_legacy').project(self.engine.v,self.engine.tri,p)
            a,b,c=self.engine.v[self.engine.tri[idx]];normal=unit(np.cross(b-a,c-a))
            gl.makeCurrent();gl.intersect_point=p;gl.intersect_normal=normal
            marker=gl.drawIndicator(p,normal)
            method=['Cz_lateral_first','BEAM_style','SGP'][self.route.currentIndex()]
            paths=self.last_result['methods'].get(method,{}).get('paths',[])
            from OpenGL import GL
            composite=GL.glGenLists(1);GL.glNewList(composite,GL.GL_COMPILE);GL.glCallList(marker)
            GL.glPushAttrib(GL.GL_ENABLE_BIT|GL.GL_CURRENT_BIT|GL.GL_LINE_BIT);GL.glDisable(GL.GL_LIGHTING);GL.glLineWidth(2.5)
            center=self.engine.v.mean(0)
            for i,path in enumerate(paths):
                GL.glColor3f(*[(1.,.2,.1),(.1,.8,.2),(.2,.4,1.)][i%3]);GL.glBegin(GL.GL_LINE_STRIP)
                for x in path:
                    x=np.asarray(x,float);direction=x-center;direction/=max(np.linalg.norm(direction),1e-9);GL.glVertex3dv(x+.4*direction)
                GL.glEnd()
            GL.glPopAttrib();GL.glEndList()
            old=getattr(gl,'_target_tool_lists',[])
            gl.indicator=composite;gl._target_tool_lists=[marker,composite]
            for handle in old:GL.glDeleteLists(handle,1)
            gl.update();self.window.headModelWidget.writePosition()
        except Exception as e:self.notify(tr('Point calculated, but this GUI marker interface failed: ')+str(e))
    def export(self):
        if self.last_result is None:return self.notify(tr('Complete a calculation first.'))
        file,_=QtWidgets.QFileDialog.getSaveFileName(self,tr('匯出結果'),'C:/SimNIBS_Data/target_measurements.json','JSON (*.json)')
        if not file:return
        try:
            path=Path(file);path.write_text(json.dumps(self.last_result,ensure_ascii=False,indent=2),encoding='utf-8')
            with path.with_name(path.stem+'_scalp.csv').open('w',newline='',encoding='utf-8') as f:csv.writer(f).writerow(['Electrode',*self.last_result['scalp'],'Target_scalp'])
            self.notify(tr('Exported JSON with three paths and native scalp-coordinate CSV.'))
        except OSError as e:self.notify(e)

class CompanionWindow(TDCS_GUI):
    def loadHeadModel(self,filename):
        from repair_assets import ensure_reviewable
        ensure_reviewable(Path(filename).parent)
        panel=getattr(self,'target_panel',None)
        if panel is not None:
            if panel.worker is not None and panel.worker.isRunning():
                panel.notify(tr(tr('請等待目前計算完成。')));return
            if panel.binding and self.session.eeg_cap==panel.binding['eeg_csv']:self.session.eeg_cap=None
            panel.reset_scalp_sources();panel._observed_mesh=None;panel._original_skin=None
            self.session.subpath=''
        super().loadHeadModel(filename)
    def drawModel(self):
        super().drawModel()
        panel=getattr(self,'target_panel',None)
        if panel is not None and panel.binding:
            # File menu cap/redraw actions must not silently restore the old scalp.
            panel.apply_overlay()
    def generateNNAVSession(self):
        panel=getattr(self,'target_panel',None)
        if panel is not None:
            if panel._binding_error:raise ValueError(panel._binding_error)
            if panel.binding:
                from repair_assets import load_binding
                load_binding(Path(panel.binding['fem']).parent,Path(str(self.file_name.text())))
        session=super().generateNNAVSession()
        if panel is not None and panel.binding:
            session.eeg_cap=panel.binding['eeg_csv']
            # SimNIBS GUI returnCoilAndConds freezes matsimnibs using getSurface('Scalp'),
            # so TMS matrices here use the repaired surface while fnamehead stays the FEM.
            for poslist in session.poslists:
                if str(getattr(poslist,'type','')).upper()=='TDCSLIST' and getattr(poslist,'electrode',[]):
                    raise ValueError('Repaired localization overlay supports TMS. TES electrodes require a consistent remeshed FEM.')
        return session

def main():
    app=QtWidgets.QApplication(sys.argv);app.setFont(QtGui.QFont('Microsoft JhengHei',10));sys.excepthook=except_hook
    import simnibs
    if not str(simnibs.__version__).startswith('4.6'):
        QtWidgets.QMessageBox.critical(None,tr('Incompatible version'),tr('Use the installed SimNIBS 4.6 Python.'));return 1
    window=CompanionWindow()
    if not hasattr(window.headModelWidget.glHeadModel,'intersect_point'):
        QtWidgets.QMessageBox.critical(window,tr('Incompatible version'),tr('This tool requires the SimNIBS 4.6 GUI intersect_point interface.'));return 1
    dock=QtWidgets.QDockWidget(tr('Cz／MNI／BEAM-style／SGP 靶點工具 v2.4.2 | 混合頭皮 v1.80.2'),window);panel=TargetPanel(window);window.target_panel=panel;dock.setWidget(panel);window.addDockWidget(QtCore.Qt.BottomDockWidgetArea,dock);window.resize(1400,1050);window.show()
    # Manual launch stays blank. Only an explicit Builder handoff loads a folder.
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--m2m');args=parser.parse_args()
    if args.m2m:QtCore.QTimer.singleShot(0,lambda:panel.load_folder(args.m2m))
    return app.exec_()
if __name__=='__main__':sys.exit(main())
