# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Reviewed localization-asset selection shared by Builder and targeting GUI."""
from ui_language import tr
from pathlib import Path
from PyQt5 import QtCore,QtWidgets

class ImportWorker(QtCore.QThread):
    success=QtCore.pyqtSignal(object)
    failure=QtCore.pyqtSignal(str)
    def __init__(self,folder,surface,csvpath,parent=None):
        super().__init__(parent);self.args=(folder,surface,csvpath)
    def run(self):
        try:
            from repair_assets import bind
            self.success.emit(bind(*self.args))
        except Exception as e:self.failure.emit(str(e))

class RepairDialog(QtWidgets.QDialog):
    def __init__(self,parent=None,folder='',surface='',csvpath=''):
        super().__init__(parent);self.setWindowTitle(tr('匯入已檢查的頭皮與 EEG'));self.resize(850,300)
        self.worker=None;self.binding=None;layout=QtWidgets.QVBoxLayout(self)
        form=QtWidgets.QFormLayout();layout.addLayout(form);self.fields=[]
        for label,value,filter_ in [(tr('m2m 資料夾'),folder,None),(tr('修補頭皮 MSH'),surface,'Gmsh (*.msh)'),(tr('重算 EEG CSV'),csvpath,'CSV (*.csv)')]:
            row=QtWidgets.QWidget();bar=QtWidgets.QHBoxLayout(row);bar.setContentsMargins(0,0,0,0);e=QtWidgets.QLineEdit(str(value));b=QtWidgets.QPushButton(tr('瀏覽'));bar.addWidget(e);bar.addWidget(b);form.addRow(label,row);self.fields.append(e)
            def choose(_=False,e=e,filter_=filter_):
                p=QtWidgets.QFileDialog.getExistingDirectory(self,tr('m2m 資料夾'),e.text()) if filter_ is None else QtWidgets.QFileDialog.getOpenFileName(self,tr('選取檔案'),e.text(),filter_)[0]
                if p:e.setText(p)
            b.clicked.connect(choose)
        note=QtWidgets.QLabel(tr('修補表面用於 TMS 定位與測距；電場仍由既有體積 FEM 計算。原始 m2m 網格與標準 EEG CSV 保留。若需修補後 FEM，請使用多組織標籤重建功能。'));note.setWordWrap(True);layout.addWidget(note)
        self.confirm=QtWidgets.QCheckBox(tr('已確認同一個案、scanner RAS mm、表面解剖位置及新 EEG 配對正確'));layout.addWidget(self.confirm)
        for e in self.fields:e.textChanged.connect(lambda _text:self.confirm.setChecked(False))
        self.status=QtWidgets.QLabel('');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.buttons=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel);layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.start);self.buttons.rejected.connect(self.reject)
        from ui_language import qt_translate
        qt_translate(self)
    def start(self):
        if not self.confirm.isChecked():return QtWidgets.QMessageBox.warning(self,tr('Please check'),tr('Confirm subject, coordinates and visual review first.'))
        folder,surface,csvpath=[e.text().strip() for e in self.fields]
        if not Path(folder).is_dir() or not Path(surface).is_file() or not Path(csvpath).is_file():
            return QtWidgets.QMessageBox.warning(self,tr('Please check'),tr('Select valid m2m, MSH and CSV files.'))
        for e in self.fields:e.setEnabled(False)
        self.confirm.setEnabled(False);self.buttons.setEnabled(False);self.status.setText(tr('Checking all EEG points against the scalp and importing…'))
        self.worker=ImportWorker(folder,surface,csvpath,self);self.worker.success.connect(self.done_import);self.worker.failure.connect(self.failed);self.worker.start()
    def done_import(self,result):
        self.worker.wait();self.binding=result
        cleanup=result.get('validation',{}).get('surface_cleanup',{})
        if cleanup.get('triangles_removed',0):
            text=tr('Removed tiny isolated islands: {0} triangles, {1:.4f} mm². Only the import copy was cleaned; source MSH, mask and FEM are retained. All EEG points passed distance checks against the retained scalp.').format(cleanup['triangles_removed'],cleanup['area_removed_mm2'])
            QtWidgets.QMessageBox.information(self,tr('Scalp import completed'),text)
        self.accept()
    def failed(self,error):
        self.status.setText(error)
        for e in self.fields:e.setEnabled(True)
        self.confirm.setEnabled(True);self.buttons.setEnabled(True)
    def reject(self):
        if self.worker is not None and self.worker.isRunning():return
        super().reject()
    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():event.ignore()
        else:super().closeEvent(event)
