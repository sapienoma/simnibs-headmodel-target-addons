本次補充：程式自訂日誌、進度、耗時與錯誤提示以英文顯示，不隨介面語言切換；保留既有語言設定，新使用者預設英文。第三方輸出及使用者檔案路徑保留原文。

Portable launch: Start_Scalp_Repair.vbs
First-time setup: read ../Getting_Started.html. Select the installed SimNIBS Python if prompted.
首次使用請先閱讀上層 Getting_Started.html，並於本機安裝修補依賴。

混合頭皮修補 v1.80.2 / Hybrid scalp repair v1.80.2

本子工具先產生配準與外輪廓草稿，供人工檢查，再把補片局部接到原始 m2m 頭皮。
最終預設流程：載入 manifest → 匯出 REVIEWED → ⑤ 建立混合頭皮＋重算 EEG。
原始 m2m 顶點與完整保留區三角面不變；只有裁切交界、接縫帶及補頂區使用新網格。
完整說明在上一層 README.txt / README_EN.txt。

Load previous work → review/export mask → Build hybrid scalp + recompute EEG.
Select original full m2m FEM, reviewed donor PLY/MSH and same-subject anatomical fiducials.
The final localization mesh preserves original lower scalp geometry and uses a newly triangulated seam plus donor cap.
A volume FEM is not created by this surface workflow. The original T1/m2m scalp remains selectable.

Registration/mask packages remain isolated under %LOCALAPPDATA%\SimNIBS_ScalpRepair\deps_<Python version>.
Hybrid mesh and EEG steps run in the original SimNIBS Python, without those private dependencies.
