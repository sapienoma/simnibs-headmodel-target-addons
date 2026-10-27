# SPDX-License-Identifier: GPL-3.0-only
# SimNIBS Head-Model Tools Suite; license notices added 2026-10-27.
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 only.
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the accompanying LICENSE file for the full license text.
# Existing third-party copyright and license notices remain applicable.
"""Standard-library Windows GUI; scientific packages run in isolated child process."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from ui_language import tr
import json,os,queue,subprocess,sys,threading,time,webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'SimNIBS_ScalpRepair'
DEPS=DATA/('deps_'+str(sys.version_info.major)+str(sys.version_info.minor))
PREF=DATA/'settings.json'

class App(tk.Tk):
 def __init__(self,initial=None):
  super().__init__();self.title(tr('混合頭皮修補 v1.80.2 — 原始 m2m＋頭頂補片'));self.geometry('1100x880');self.proc=None;self.events=queue.Queue();self.last_output=None
  try:prefs=json.loads(PREF.read_text(encoding='utf-8'))
  except (OSError,ValueError):prefs={}
  initial=initial or {}
  self.hybrid_original=initial.get('original_msh') or prefs.get('original_msh','')
  self.vars={};self.controls=[]
  from ui_language import LANG,set_language,tk_translate,source
  languagebar=ttk.Frame(self);languagebar.pack(fill='x',padx=15,pady=4)
  ttk.Label(languagebar,text=tr('Language / 語言')).pack(side='left')
  language=tk.StringVar(value='English' if LANG=='en' else tr('繁體中文'))
  combo=ttk.Combobox(languagebar,textvariable=language,values=[tr('繁體中文'),'English'],state='readonly',width=15);combo.pack(side='left')
  def switch_language(_event=None):
   set_language('en' if language.get()=='English' else 'zh-TW');tk_translate(self);self.title(tr('混合頭皮修補 v1.80.2 — 原始 m2m＋頭頂補片'));self.status.set(tr(source(self.status.get())))
  combo.bind('<<ComboboxSelected>>',switch_language)

  ttk.Label(self,text=tr('① 安裝依賴（首次） → ② 選 T1/T2、配準與補頂草稿 → ③ 檢查／編修遮罩 → ④ 匯出已檢查表面'),wraplength=950).pack(padx=15,pady=12)
  for key,title,default,kind in [('t1','T1 axial NIfTI',initial.get('t1',''),'file'),('t2','T2 NIfTI',initial.get('t2',''),'file'),('output',tr('輸出根目錄'),initial.get('output') or prefs.get('output','C:/SimNIBS_Data/ScalpRepair'),'dir'),('t1_mask',tr('T1 外輪廓二值遮罩（可選）'),'','file'),('t2_mask',tr('T2 外輪廓二值遮罩（可選）'),'','file')]:
   row=ttk.Frame(self);row.pack(fill='x',padx=15,pady=4);ttk.Label(row,text=title,width=31).pack(side='left');var=tk.StringVar(value=default);self.vars[key]=var;e=ttk.Entry(row,textvariable=var);e.pack(side='left',fill='x',expand=True);b=ttk.Button(row,text=tr('瀏覽'),command=lambda k=key,t=kind:self.choose(k,t));b.pack(side='left');self.controls.extend([e,b])
  opts=ttk.Frame(self);opts.pack(fill='x',padx=15,pady=8)
  self.form=tk.StringVar(value='qform');ttk.Label(opts,text=tr('座標來源')).pack(side='left');c=ttk.Combobox(opts,textvariable=self.form,values=['qform','sform'],width=9,state='readonly');c.pack(side='left');self.controls.append(c)
  self.factor=tk.StringVar(value='0.5');ttk.Label(opts,text=tr('  自動外輪廓閾值倍率')).pack(side='left');e=ttk.Entry(opts,textvariable=self.factor,width=7);e.pack(side='left');self.controls.append(e)
  ttk.Label(self,text=tr('輸出為填滿頭部的外輪廓遮罩，並非 scalp 組織層。原始影像不變；不會覆寫 m2m 或產生修補後 FEM；可在確認基準點後另行重算 EEG。'),wraplength=950).pack(padx=15,pady=4)
  bar=ttk.Frame(self);bar.pack(fill='x',padx=15,pady=8)
  for title,fn in [(tr('首次安裝獨立依賴'),self.install),(tr('配準並產生草稿'),self.prepare),(tr('開啟檢查報告'),self.report),(tr('載入先前工作'),self.load_work)]:
   b=ttk.Button(bar,text=title,command=fn);b.pack(side='left',padx=3);self.controls.append(b)
  self.accept=tk.BooleanVar();c=ttk.Checkbutton(self,text=tr('我已逐切面檢查對位、外輪廓及接縫，了解此表面尚非驗證完成的定位／FEM 模型'),variable=self.accept);c.pack(anchor='w',padx=15);self.controls.append(c)
  bar=ttk.Frame(self);bar.pack(fill='x',padx=15,pady=8)
  for title,fn in [(tr('匯出已檢查草稿表面'),lambda:self.approve(False)),(tr('載入人工修正遮罩並匯出'),lambda:self.approve(True))]:
   b=ttk.Button(bar,text=title,command=fn);b.pack(side='left',padx=3);self.controls.append(b)
  self.stop=ttk.Button(bar,text=tr('停止'),command=self.cancel,state='disabled');self.stop.pack(side='right')
  eegbar=ttk.Frame(self);eegbar.pack(fill='x',padx=15,pady=5)
  self.fiducials=tk.StringVar();ttk.Label(eegbar,text=tr('同個案 EEG／四基準點 CSV')).pack(side='left');e=ttk.Entry(eegbar,textvariable=self.fiducials);e.pack(side='left',fill='x',expand=True);self.controls.append(e)
  b=ttk.Button(eegbar,text=tr('選取 CSV'),command=self.choose_fiducials);b.pack(side='left');self.controls.append(b)
  self.fid_confirm=tk.BooleanVar();self.fiducials.trace_add('write',lambda *_:self.fid_confirm.set(False));c=ttk.Checkbutton(self,text=tr('我已確認 Nz、Iz、LPA、RPA 屬於此個案，使用原 T1 的 scanner RAS mm 座標，且解剖位置正確'),variable=self.fid_confirm);c.pack(anchor='w',padx=15);self.controls.append(c)
  hybridbar=ttk.Frame(self);hybridbar.pack(fill='x',padx=15,pady=5)
  b=ttk.Button(hybridbar,text=tr('⑤ 建立混合頭皮＋重算 EEG…'),command=self.hybrid_dialog);b.pack(side='left');self.controls.append(b)
  b=ttk.Button(hybridbar,text=tr('完整修補表面 EEG（舊流程）'),command=self.recompute_eeg);b.pack(side='left',padx=8);self.controls.append(b)
  self.status=tk.StringVar(value=tr('Ready. First use requires isolated scientific dependencies; installed SimNIBS packages are retained.'));ttk.Label(self,textvariable=self.status,wraplength=950).pack(padx=15,pady=5)
  self.text=tk.Text(self,height=18,wrap='word');self.text.pack(fill='both',expand=True,padx=15,pady=5);self.text.configure(state='disabled');self.after(150,self.poll);self.protocol('WM_DELETE_WINDOW',self.close)
 def choose(self,key,kind):
  p=filedialog.askdirectory() if kind=='dir' else filedialog.askopenfilename(filetypes=[('NIfTI','*.nii *.nii.gz')])
  if p:self.vars[key].set(p)
 def run(self,args,callback,dependencies=True):
  if self.proc:return
  env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONUNBUFFERED']='1'
  if dependencies:env['PYTHONPATH']=str(DEPS)+os.pathsep+env.get('PYTHONPATH','')
  DATA.mkdir(parents=True,exist_ok=True);self.logfile=(DATA/'last_run.log').open('w',encoding='utf-8');self.started=time.monotonic();self.callback=callback;self.cancelled=False
  try:self.proc=subprocess.Popen([sys.executable,'-u',*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  except Exception as e:self.logfile.close();messagebox.showerror(tr('Startup failed'),tr(str(e)));return
  self.previous_states=[(w,w.cget('state')) for w in self.controls]
  for w in self.controls:w.configure(state='disabled')
  self.stop.configure(state='normal');self.status.set(tr('Running…'))
  p=self.proc
  def reader():
   for line in p.stdout:self.events.put(('line',line))
   self.events.put(('done',p.wait()))
  threading.Thread(target=reader,daemon=True).start()
 def poll(self):
  try:
   while True:
    kind,value=self.events.get_nowait()
    if kind=='line':
     self.text.configure(state='normal');self.text.insert('end',value);self.text.see('end');self.text.configure(state='disabled');self.logfile.write(value);self.logfile.flush()
    else:
     self.proc=None;self.logfile.close()
     for w,state in self.previous_states:w.configure(state=state)
     self.stop.configure(state='disabled');seconds=int(time.monotonic()-self.started)
     self.status.set(tr(f'Elapsed: {seconds // 3600} h {seconds % 3600 // 60} min {seconds % 60} s'))
     if value==0 and not self.cancelled:self.callback();messagebox.showinfo(tr('Completed'),self.status.get()+tr('\nReview the report; a completed draft does not establish anatomical quality.'))
     else:messagebox.showerror(tr('Not completed'),tr('Process failed or stopped. See output and ')+str(DATA/'last_run.log'))
  except queue.Empty:pass
  self.after(150,self.poll)
 def install(self):
  self.run(['-m','pip','install','--only-binary=:all:','--target',str(DEPS),'--upgrade','-r',str(ROOT/'requirements.txt')],lambda:self.status.set(tr('Dependencies installed; ready for registration.')),False)
 def prepare(self):
  try:
   for k in ['t1','t2']:
    if not Path(self.vars[k].get()).is_file():raise ValueError(tr('Select a valid ')+k+tr(' file'))
   factor=float(self.factor.get())
   if not 0<factor<2:raise ValueError(tr('Threshold factor must be between 0 and 2'))
   root=Path(self.vars['output'].get());self.last_output=root/('repair_'+time.strftime('%Y%m%d_%H%M%S'));self.accept.set(False);self.fid_confirm.set(False)
   DATA.mkdir(parents=True,exist_ok=True);PREF.write_text(json.dumps({'output':str(root),'original_msh':self.hybrid_original},ensure_ascii=False),encoding='utf-8')
   args=[str(ROOT/'repair.py'),'prepare','--t1',self.vars['t1'].get(),'--t2',self.vars['t2'].get(),'--output',str(self.last_output),'--form',self.form.get(),'--threshold-factor',str(factor)]
   for k in ['t1_mask','t2_mask']:
    if self.vars[k].get():args.extend(['--'+k.replace('_','-'),self.vars[k].get()])
   self.run(args,self.report)
  except Exception as e:messagebox.showerror(tr('Please check'),tr(str(e)))
 def report(self):
  if self.last_output and (self.last_output/'review.html').exists():webbrowser.open((self.last_output/'review.html').resolve().as_uri())
  else:messagebox.showinfo(tr('No report yet'),tr('Create a draft or load previous work first.'))
 def load_work(self):
  p=filedialog.askopenfilename(filetypes=[(tr('工作檔'),'manifest.json')])
  if p:self.last_output=Path(p).parent;self.accept.set(False);self.fid_confirm.set(False);self.report()
 def approve(self,edited):
  if not self.last_output or not self.accept.get():messagebox.showwarning(tr('Review first'),tr('Load the work, review the result and select confirmation.'));return
  args=[str(ROOT/'repair.py'),'approve','--output',str(self.last_output)]
  if edited:
   p=filedialog.askopenfilename(filetypes=[('Union-grid binary mask','*.nii *.nii.gz')])
   if not p:return
   args.extend(['--reviewed-mask',p])
  self.run(args,lambda:self.status.set(tr('REVIEWED surface exported: ')+str(self.last_output)))
 def choose_fiducials(self):
  p=filedialog.askopenfilename(filetypes=[('SimNIBS CSV','*.csv')])
  if p:self.fiducials.set(p);self.fid_confirm.set(False)
 def recompute_eeg(self):
  if not self.last_output or not self.fid_confirm.get():messagebox.showwarning(tr('Please check'),tr('Load work, export reviewed scalp and confirm the four fiducials.'));return
  if not Path(self.fiducials.get()).is_file():messagebox.showwarning(tr('Select a file'),tr('Select a CSV containing Nz, Iz, LPA and RPA.'));return
  self.run([str(ROOT/'eeg_recompute.py'),'--work',str(self.last_output),'--fiducials',self.fiducials.get()],lambda:self.status.set(tr('EEG recomputed. Review the new CSV / GEO and EEG_coordinate_changes.csv.')),dependencies=False)
 def hybrid_dialog(self):
  if self.proc:return
  dialog=tk.Toplevel(self);dialog.title(tr('混合頭皮 v1.80.2：保留原始模型，只替換頭頂'));dialog.geometry('1050x510');dialog.transient(self);dialog.grab_set()
  inputs={}
  stamp=time.strftime('%Y%m%d_%H%M%S')
  root=self.last_output or Path(self.vars['output'].get())
  donor=str(root/'scalp_surface_REVIEWED_RAS.ply') if (root/'scalp_surface_REVIEWED_RAS.ply').is_file() else ''
  original_cap=Path(self.hybrid_original).parent/'eeg_positions'/'EEG10-10_UI_Jurak_2007.csv' if self.hybrid_original else None
  default_fid=str(original_cap) if original_cap and original_cap.is_file() else self.fiducials.get()
  fields=[('original',tr('原始 m2m 頭部 MSH'),self.hybrid_original,'Gmsh'),('donor',tr('已檢查補頂 PLY／MSH'),donor,'Surface'),('fid',tr('同個案基準點／EEG CSV'),default_fid,'CSV'),('out',tr('新的混合表面輸出資料夾'),str(root/('hybrid_'+stamp)),'dir')]
  for key,label,value,kind in fields:
   row=ttk.Frame(dialog);row.pack(fill='x',padx=12,pady=5);ttk.Label(row,text=label,width=30).pack(side='left');var=tk.StringVar(value=value);inputs[key]=var;ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
   def choose(k=key,kind=kind):
    if kind=='dir':
     parent=filedialog.askdirectory(parent=dialog);path=str(Path(parent)/('hybrid_'+stamp)) if parent else ''
    else:
     filters={'Gmsh':[('Original head FEM','*.msh')],'Surface':[('Reviewed surface','*.ply *.msh')],'CSV':[('CSV','*.csv')]}[kind]
     path=filedialog.askopenfilename(parent=dialog,filetypes=filters)
    if path:inputs[k].set(path)
   ttk.Button(row,text=tr('瀏覽'),command=choose).pack(side='left')
  options=ttk.Frame(dialog);options.pack(fill='x',padx=12,pady=8);cut=tk.StringVar();width=tk.StringVar(value='4.0')
  ttk.Label(options,text=tr('原始保留上界 RAS Z（mm；留白自動）')).pack(side='left');ttk.Entry(options,textvariable=cut,width=10).pack(side='left')
  ttk.Label(options,text=tr('  接縫高度 mm')).pack(side='left');ttk.Entry(options,textvariable=width,width=8).pack(side='left')
  note=tr('裁切線以下保留原 m2m 頂點與完整三角面；只在接縫帶與頭頂使用新網格。自動切面參考原 T1 涵蓋上界；需要已載入的修補 manifest。原始四面體 FEM 不變。')
  ttk.Label(dialog,text=note,wraplength=980).pack(fill='x',padx=12,pady=6)
  ttk.Label(dialog,text=tr('檢查新接縫的共用邊、頂點扇、孔洞與自交；遠離切面的原始邊界接觸僅在周圍三角面完全保留時允許沿用。完成後仍須檢查解剖及接縫外觀。'),wraplength=980).pack(fill='x',padx=12,pady=6)
  accepted=tk.BooleanVar();ttk.Checkbutton(dialog,text=tr('已確認同個案 scanner RAS mm、原始 m2m 與已檢查補頂表面，以及四基準點解剖位置'),variable=accepted).pack(anchor='w',padx=12,pady=5)
  for key in ('original','donor','fid'):inputs[key].trace_add('write',lambda *_:accepted.set(False))
  import_pair=tk.BooleanVar(value=True);ttk.Checkbutton(dialog,text=tr('完成後加入原 m2m 的混合／原始頭皮切換選項（不改變 FEM）'),variable=import_pair).pack(anchor='w',padx=12,pady=5)
  def start():
   try:
    if not accepted.get():raise ValueError(tr('Confirm subject, coordinates and visual review first.'))
    for key in ('original','donor','fid'):
     if not Path(inputs[key].get()).is_file():raise ValueError(tr('Select a valid ')+key)
    seam=float(width.get())
    if not .5<=seam<=15:raise ValueError(tr('Transition height must be between 0.5 and 15 mm.'))
    original=Path(inputs['original'].get()).resolve();out=Path(inputs['out'].get()).resolve()
    args=[str(ROOT.parent/'hybrid_surface.py'),'--original',str(original),'--donor',inputs['donor'].get(),'--fiducials',inputs['fid'].get(),'--output',str(out),'--width',str(seam)]
    if cut.get().strip():args+=['--cut-z',str(float(cut.get()))]
    elif self.last_output:args+=['--work',str(self.last_output)]
    else:raise ValueError(tr('Load reviewed repair work for automatic cutting, or enter lower-cut RAS Z.'))
    if cut.get().strip() and self.last_output:args+=['--work',str(self.last_output)]
    if import_pair.get():args+=['--bind-m2m',str(original.parent)]
    self.hybrid_original=str(original);DATA.mkdir(parents=True,exist_ok=True)
    try:saved=json.loads(PREF.read_text(encoding='utf-8'))
    except (OSError,ValueError):saved={}
    saved['original_msh']=str(original);PREF.write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8')
    self.last_hybrid=out;dialog.destroy()
    def complete():
     self.status.set(tr('Hybrid scalp / EEG completed. Review the seam report, then reopen the original m2m to switch scalp models.'))
     if (out/'hybrid_report.html').is_file():webbrowser.open((out/'hybrid_report.html').as_uri())
    self.run(args,complete,dependencies=False)
   except Exception as e:messagebox.showerror(tr('Please check'),tr(str(e)),parent=dialog)
  ttk.Button(dialog,text=tr('建立混合表面、測試接縫並重算 EEG'),command=start).pack(anchor='e',padx=12,pady=10)
 def cancel(self):
  if self.proc:
   self.cancelled=True
   if os.name=='nt':subprocess.run(['taskkill','/PID',str(self.proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
   else:self.proc.terminate()
 def close(self):
  if self.proc:messagebox.showinfo(tr('Job running'),tr('Stop and wait for the process to exit before closing.'));return
  self.destroy()
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='T2 scalp repair GUI')
 parser.add_argument('--t1',default='');parser.add_argument('--t2',default='');parser.add_argument('--output',default='');parser.add_argument('--original-msh',default='')
 App(vars(parser.parse_args())).mainloop()
