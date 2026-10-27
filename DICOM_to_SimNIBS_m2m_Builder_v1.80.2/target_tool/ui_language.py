# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Small offline zh-TW / English catalog shared by the two desktop tools."""
import json,os,re
from pathlib import Path
BASE=Path(__file__).resolve().parent
PREF=(Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.config')))/'SimNIBS_Tools'/'language.json')
CATALOG=json.loads((BASE/'translations_en.json').read_text(encoding='utf-8'))
try:LANG=json.loads(PREF.read_text(encoding='utf-8')).get('language','en')
except (OSError,ValueError):LANG='en'
if LANG not in ('zh-TW','en'):LANG='en'
_reverse={}
_pattern=re.compile('|'.join(re.escape(k) for k in sorted(CATALOG,key=len,reverse=True)))

class Localized(str):
    def format(self,*args,**kwargs):
        rendered=super().format(*args,**kwargs)
        original=_reverse.get(str(self),str(self)).format(*args,**kwargs)
        _reverse[rendered]=original
        return Localized(rendered)

def tr(text):
    text=str(text)
    if LANG!='en':return Localized(text)
    out=_pattern.sub(lambda m:CATALOG[m.group()],text)
    out=out.translate(str.maketrans({'：':': ', '；':'; ', '（':' (', '）':')', '，':', ', '。':'.', '／':'/'}))
    _reverse[out]=text
    return Localized(out)

def set_language(value):
    global LANG
    LANG=value if value in ('en','zh-TW') else 'zh-TW'
    try:
        PREF.parent.mkdir(parents=True,exist_ok=True)
        tmp=PREF.with_suffix('.tmp');tmp.write_text(json.dumps({'language':LANG}),encoding='utf-8');tmp.replace(PREF)
    except OSError:pass

def source(text):return _reverse.get(str(text),str(text))

def qt_translate(root):
    from PyQt5 import QtWidgets
    for w in [root,*root.findChildren(QtWidgets.QWidget)]:
        props=[]
        if isinstance(w,(QtWidgets.QLabel,QtWidgets.QAbstractButton)):props.append(('text',w.text,w.setText))
        if isinstance(w,QtWidgets.QLineEdit):props.append(('placeholderText',w.placeholderText,w.setPlaceholderText))
        if isinstance(w,QtWidgets.QGroupBox):props.append(('title',w.title,w.setTitle))
        if w.windowTitle():props.append(('windowTitle',w.windowTitle,w.setWindowTitle))
        if w.toolTip():props.append(('toolTip',w.toolTip,w.setToolTip))
        for name,get,setter in props:
            current=get();previous=w.property('_i18n_last_'+name)
            raw=w.property('_i18n_source_'+name) if current==previous else source(current)
            raw=raw if raw is not None else current;rendered=str(tr(raw));setter(rendered)
            w.setProperty('_i18n_source_'+name,raw);w.setProperty('_i18n_last_'+name,rendered)
        if isinstance(w,QtWidgets.QTabWidget):
            for i in range(w.count()):
                page=w.widget(i);raw=page.property('_tab_source') or source(w.tabText(i));page.setProperty('_tab_source',raw);w.setTabText(i,tr(raw))
        if isinstance(w,QtWidgets.QComboBox) and w.objectName()!='languageSelector':
            for i in range(w.count()):
                raw=w.itemData(i,QtWidgets.QApplication.instance()._language_source_role) or source(w.itemText(i))
                w.setItemData(i,raw,QtWidgets.QApplication.instance()._language_source_role);w.setItemText(i,tr(raw))
        if isinstance(w,QtWidgets.QTableWidget):
            for i in range(w.columnCount()):
                item=w.horizontalHeaderItem(i)
                if item:item.setText(tr(source(item.text())))
            for i in range(w.rowCount()):
                for j in (1,4):
                    item=w.item(i,j)
                    if item:item.setText(tr(source(item.text())))

def install_qt(root,layout,callback=None):
    from PyQt5 import QtCore,QtWidgets
    QtWidgets.QApplication.instance()._language_source_role=QtCore.Qt.UserRole+71
    combo=QtWidgets.QComboBox();combo.setObjectName('languageSelector');combo.addItem('繁體中文','zh-TW');combo.addItem('English','en');combo.setCurrentIndex(1 if LANG=='en' else 0)
    row=QtWidgets.QHBoxLayout();row.addStretch();row.addWidget(QtWidgets.QLabel('Language / 語言'));row.addWidget(combo);layout.insertLayout(0,row)
    def change():
        set_language(combo.currentData());qt_translate(root)
        if callback:callback()
    combo.currentIndexChanged.connect(change);qt_translate(root)
    return combo

def tk_translate(root):
    def visit(w):
        for child in w.winfo_children():visit(child)
        try:
            current=w.cget('text')
            if current:
                raw=getattr(w,'_i18n_source',None) if current==getattr(w,'_i18n_last',None) else source(current)
                w._i18n_source=raw or current;w._i18n_last=str(tr(w._i18n_source));w.configure(text=w._i18n_last)
        except Exception:pass
    visit(root)
