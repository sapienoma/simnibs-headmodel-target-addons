本次補充：程式自訂日誌、進度、耗時與錯誤提示以英文顯示，不隨介面語言切換；保留既有語言設定，新使用者預設英文。第三方輸出及使用者檔案路徑保留原文。

此獨立 Cz 目錄開 Start_Cz_Tool.vbs；DICOM 建模需另外使用 Builder 套件。

封裝修訂 2 — 新電腦使用說明
程式版本維持 Builder 1.80.2／Cz tool 2.4.2；本次為英文檔名與換機設定整理。

1. 每台 Windows 10/11 電腦各自安裝 SimNIBS 4.6，使用內附 simnibs_env\python.exe。
   Builder 另需 dcm2niix.exe，可放在 C:\dcm2niix.exe，或在介面選取實際位置。
   本 ZIP 不包含 SimNIBS、dcm2niix、Python 環境或模型權重。
2. 完整解壓縮至可讀取的資料夾，例如 C:\SimNIBS_Tools 或 D:\Tools\SimNIBS_Tools。
   不要在 ZIP 內直接啟動，也不要只複製單一 VBS。啟動器使用相對路徑並處理路徑中的空格。
3. 建模開 Start_Builder.vbs；測距開 Start_Cz_Tool.vbs。套件根目錄及各獨立工具內均有對應入口。
   scalp_repair\Start_Scalp_Repair.vbs 可獨立開補頂視窗；launch_hidden.vbs 保留為替代入口。
4. 啟動器依序查找環境變數 SIMNIBS_PYTHON、前次設定、Program Files、C:\SimNIBS-4.6、
   當前使用者目錄下的 SimNIBS-4.6，以及 PATH 中的 simnibs_python。找不到有效環境時會請您選檔。
   請選本機 SimNIBS 安裝目錄下的 simnibs_env\python.exe；程式會確認可匯入 simnibs 並記住路徑。
5. Builder 內選本機 DICOM、輸出根目錄與 dcm2niix.exe。
   初始建議為 C:\SimNIBS_Data\DICOM、C:\SimNIBS_Data\Projects、C:\dcm2niix.exe，皆可修改。
   若無法寫入 C:\，改選有權限的使用者資料夾或其他磁碟。下一次會帶入上次設定。
   Cz 工具由使用者選完整 m2m，不預載個案；介面仍可切換繁體中文／English。
6. 首次使用頭皮修補時，在子工具按安裝依賴；每台電腦分別安裝，可能需要網路。
   已有 reviewed 工作可直接執行⑤，切面留白、接縫 4 mm、輸出選新的空白資料夾。
   檢查接縫及 EEG 後，重開原始 m2m 即可切換原始／混合模型。

設定與換機
共享路徑：%LOCALAPPDATA%\SimNIBS_HeadBuilder\settings.json。
補頂設定與依賴：%LOCALAPPDATA%\SimNIBS_ScalpRepair；Cz 最近資料夾等設定使用當前帳號 Qt QSettings。
散布程式時不要把 AppData、登錄設定、MRI、個案模型或 Python 環境一起打包。
在新電腦重新安裝依賴與選擇本機路徑，不需修改原始碼。同一電腦搬動程式資料夾仍可用相對路徑啟動。
個案資料需另外搬移完整 m2m，包括 repair_assets、EEG、toMNI；混合模型綁定在 m2m 內使用相對路徑。
修補工作 manifest 仍可能保存 MRI 的絕對路徑；換機後來源不存在時，需重新選取或建立對應工作。
請勿把新個案輸出存進準備散布的程式目錄。

排錯
VBS 啟動隱藏 CMD；若失敗，用 start_builder.bat／start_cz_tool.bat 查看日誌。
啟動日誌位於 %TEMP% 的 SimNIBS_HeadBuilder_startup.log、SimNIBS_TargetTool_startup.log、
SimNIBS_ScalpRepair_startup.log；補頂作業日誌在 %LOCALAPPDATA%\SimNIBS_ScalpRepair\last_run.log。
若電腦政策停用 VBS，可用 BAT，或請管理者確認指令碼支援；BAT 為可見命令視窗的排錯入口。
舊 Python 路徑無效時會略過並尋找其他環境；請勿選一般 Python 或不含 SimNIBS 的 Conda。
需清除共享路徑時，先關閉工具，將 settings.json 改名 settings.backup.json；不會刪除個案。
如不再使用環境變數覆寫，也請清除 SIMNIBS_PYTHON。

英文檔名
Start_Builder.vbs、Start_Cz_Tool.vbs、Start_Scalp_Repair.vbs：對應啟動入口。
Targets_and_Methods.html：Cz 靶點與方法說明；Getting_Started.html：中英文首次安裝說明。
README.txt／README_EN.txt：詳細中英文工作流程。既有 review.html、hybrid_report.html、
results.html、charm_report.html 已為英文，沿用原名。頭皮定位覆蓋仍不改寫體積 FEM。


----- DETAILED WORKFLOW -----

SimNIBS Cz distance tool v2.4.2
混合頭皮 v1.80.2 的操作
原始 T1／m2m 頭皮選項保留。按「建立混合頭皮…」，載入已完成的修補 manifest，
再按「⑤ 建立混合頭皮＋重算 EEG…」。選原 m2m 完整頭部 FEM、已檢查的補頂 PLY／MSH，
及同個案的四基準點 CSV。預設以原 m2m 標準 cap 提供基準點，仍需核對解剖。
程式保留裁切線以下原始頂點與完整三角面，只新建局部接縫與頭頂補片。
自動切面會在頭頂區嘗試可用高度；手動 RAS Z 不會被自動改動。
通過接縫檢查後在混合表面重新計算 EEG；不能直接沿用舊修補表面的 Cz／EEG。
勾選加入原 m2m 配對後，重開原 m2m，第二項顯示「混合頭皮＋重算 EEG」。
第一項「原始 T1／m2m 頭皮＋原始 EEG」仍可隨時切回；兩種模式同步切換 EEG。
舊完整修補表面仍可相容載入，選項維持「修補頭皮＋新 EEG」。
請檢查 hybrid_report.html、hybrid_preview.png 與 hybrid_seam.geo；接縫不等於自動補回導電體積。
詳見 MANUAL_MASK_WORKFLOW.txt / MANUAL_MASK_WORKFLOW_EN.txt。

新增雙向頭皮模型切換（Suite / Builder v1.80.2，Cz tool v2.3.0）
在 SimNIBS 的 Cz 面板，於「頭皮模型」選單選：
  原始頭皮＋原始 EEG：使用原 m2m 的詳細頭皮面與標準 EEG cap。
  修補頭皮＋新 EEG：使用已匯入的修補表面與配對的新 EEG cap。
已匯入一次配對後，可反覆切換，不必重複匯入；尚無配對時修補選項停用。
每個 m2m 記住自己的選擇，獨立啟動仍保持空白，不自動開啟個案。
切換同步更新 GUI 頭皮、點選／法向、TMS 定位表面、測距來源與 EEG。
舊 Current Position、路徑及測量結果會清空，須重新雙擊頭皮或計算 MNI。
既有 TMS 表格位置不會自動改成新的 EEG 位點；切換後須重新核對位置、角度與距離。
灰質及求解用的四面體 FEM 不因切換改變；修補定位模式的 TES 限制仍保留。
面板列出兩表面的三角面數與平均唯一邊長（mm），方便比較網格細緻度。
這些不是 MRI 原始解析度：切成更多小三角面不會增加原始影像未提供的解剖資訊。


修正說明 v1.7.1 / Cz v2.2.1（2026-10-19）
- 修正頭皮擷取：只讀 tag 1005 的三角面，不把其他組織表面一起選入。
- 修補定位表面的小孤立碎片，只有在總面積 <=50 mm² 且 <=全部面積的 0.1% 時，
  才從「新匯入副本」移除；不移動、焊接頂點或連接斷裂表面。較大分離部分仍停止並報錯。
- 清理後所有 EEG 點仍須距保留頭皮 <=3 mm；必要標記仍須遠離開口 >=5 mm。
  若 EEG 點落在被移除的碎片上，匯入會停止，不會忽略該 EEG 點。
- 原始 MSH、遮罩、EEG 與 FEM 不變，原 FEM 的參考表面可有多個分量，不做刪除。
- 清理數量與面積寫入 repair_binding.json 的 validation.surface_cleanup，成功時顯示提醒。
- 已重算 EEG 的工作直接重試匯入同一組 scalp_surface_ONLY.msh + EEG10-10_recomputed.csv。
  不需重跑 DICOM、配準、CHARM 或先重算 EEG；若仍失敗，新錯誤會包含檔案與面積資訊。
以上面積與距離門檻是程式檢查設定，不是臨床精準度標準。

SimNIBS Tools Suite v1.80.2 | Windows 10/11 / SimNIBS 4.6
英文說明：README_EN.txt。內附 VERSION.json 與 VALIDATION.json。

啟動
解壓縮完整資料夾，雙擊「Start_Cz_Tool.vbs」或 launch_hidden.vbs。
啟動器使用 SimNIBS 內附 Python；優先 SIMNIBS_PYTHON、Builder 儲存的路徑、
C:\Program Files\SimNIBS-4.6\simnibs_env\python.exe、C:\SimNIBS-4.6，最後手動選擇。
start_cz_tool.bat 供排錯；隱藏啟動日誌 %TEMP%\SimNIBS_TargetTool_startup.log。
這是原生 SimNIBS GUI 加靶點面板，不會附加到另一個已開啟的 SimNIBS 程序。
上方 Language / 語言 切換繁體中文／English，記住使用者設定。
每次獨立啟動保持空白；手動「載入 m2m 模型」或按「開啟最近的 m2m」。
由 Builder 按「在 SimNIBS 開啟模型」時，僅載入該次明確選定的模型。

載入修補頭皮與新 EEG
1. 先載入完整原 m2m，保留既有皮質與四面體 FEM。
2. 按「匯入修補頭皮／EEG…」，選同一 m2m、同次重算輸出的
   scalp_surface_ONLY.msh 與 EEG10-10_recomputed.csv。
3. 確認同一個案、scanner RAS mm、表面解剖及 EEG 配對。不能混用 MNI、LPS、voxel index。
4. 匯入檢查全部 EEG 點到表面 <=3 mm、必要 Cz/Nz/Iz/LPA/RPA、tag 1005、三角面與連通性，
   必要基準點距開口邊界 >=5 mm；四基準點與 FEM 的距離亦作合理性檢查。
   這些是程式門檻，不是臨床精準度標準；不能自動證明同個案或解剖正確。
5. m2m\repair_assets\import_... 保存正規化配對（每名稱一列），repair_binding.json 保存相對路徑與雜湊。
   原 FEM 及標準 EEG CSV 保留；整個 m2m 可一起搬移。檔案內容改變需重新匯入。
6. 模型載入後自動套用已儲存配對：頭皮顯示、雙擊、法向與測距使用修補表面；Cz 使用新 EEG。
   個人 MNI 轉換仍從原 m2m\toMNI 讀取，而不是表面輸出資料夾。
7. 「頭皮模型」選單可雙向切換；不刪除已儲存配對，重新載入使用上次選擇。
   原 SimNIBS File 選單另選 cap 不會取代目前已啟用的修補配對；請用匯入入口選新的配對。

在 SimNIBS 模擬 TMS
整合 GUI 的 scalp 指向修補表面，session.eeg_cap 指向新 cap；session.fnamehead 仍是原 FEM。
原生 TMS 表格依修補頭皮計算線圈 matsimnibs（含法向、方向與距離），Run 仍在原 FEM 求解電場。
更改表面後，既有 TMS 表格的點位不會自動重新定位；請重新選新 EEG 位點與確認線圈方向。
這是修補定位、保留導電幾何；頭頂缺失的 scalp/skull/CSF 導電體積不會因此自動補回。
覆蓋模式不允許帶 TES 電極的 session 求解，因電極需要一致的體積網格。
儲存 MAT 可保留 FEM/cap/TMS 矩陣，但普通 SimNIBS 不會自行顯示修補表面；顯示請使用本程式。
如要修補後的完整 FEM，使用 Builder v1.80.2「從人工修正組織標籤重建 FEM…」，
由已檢查多組織標籤建立新模型及 EEG，再在本工具選擇新 m2m。
只有 surface-only MSH 和 EEG 不足以恢復缺失顱骨／CSF，不能直接拼接到 FEM 當成有效體積模型。

人工遮罩／EEG 修正簡介
Builder → T2 補頂 → 載入 manifest.json → 以 T1_union/T2_registered_union 檢查
scalp_envelope_DRAFT.nii.gz → 在同一 union-grid 人工編修 0/1 envelope → 載入人工修正遮罩並匯出
→ 核對 Nz/Iz/LPA/RPA scanner RAS mm → 重算 EEG → 匯入本工具。
Duplicate Iz 以 Fiducial 優先；同級座標衝突須人工確認。非流形邊清理後仍存在時修正遮罩。
基準點離表面 >5 mm 時先檢查 MRI 解剖；最近點投影只是候選，不能直接視為正確 inion。
完整流程與錯誤排除見 Builder README.txt 或同包 MANUAL_MASK_WORKFLOW.txt。

Current Position 與 MNI
選 Scalp，雙擊頭皮；自動或按鍵讀取 GUI intersect_point，不用 OCR、不讀 TMS 表格。
MNI 頁含 12 個研究位點與空白 X/Y/Z 自訂欄，單位 MNI 世界座標 mm (RAS)。
MNI → SimNIBS 非線性轉換至個人腦內點 → 最近三角頭皮點 → 三種距離。
保留原 MNI、native brain、scalp、投影距離及正反向誤差。不是最佳電場位置或個人功能 hotspot。
需要完整 toMNI；只有 .msh / CSV 無法做非線性 MNI 轉換。
位點、座標、來源及限制見 targets.json、TMS_MNI_targets.csv 與「Targets_and_Methods.html」。
群體 DLPFC、語言與吞嚥候選不保證是個人最佳治療位置；吞嚥 hotspot 需個人 TMS/MEP 定位。

三種量測的精確定義
1. Cz 先左右、再前後：左右由 LPA→RPA 定義，鼻枕方向正交化。
   第一切面通過 Cz、法向為前後軸；沿頭皮交線到目標旁矢狀面，再沿其交線至目標。
   第二切面垂直 LPA–RPA；不是依 EEG 網路逐點移動，也不一定與 MRI 矢狀面平行。
2. BEAM-style X/Y：以 Fpz–Oz 頭圍平面及 Nz–Cz–Iz 參考面定義。
   X 沿頭圍從 Fpz 向靶點側量到徑向切面足點，Y 從 Cz 沿該切面弧線至靶點。
   這是指定靶點的廣義幾何表示，不是原始 Beam F3 或 adjusted Beam F3 預測器。
   額外 F3 文獻近似參考：X≈0.1154 HC；Y≈0.2637 (NI+TT)/2，不能當成完整 Beam F3。
3. SGP／個人 CPC：參考弧 Nz→Cz→Iz，活動平面經 LPA、RPA、靶點 s，上方交點 s′。
   pNZ=Nz→s′ / Nz→Cz→Iz；pAL=LPA→s / LPA→s→RPA。
   顯示從 Nz 或 Cz 到 s′、再從 LPA/RPA 沿活動弧到靶點的 mm/cm。
   個人 Cz 不強制為參考弧 50%；此為個人幾何，非作者群體 MNI2CPC 機率映射。
三者均為指定平面與三角頭皮的交線弧長，不是自由最短測地線的 XYZ 分量。
切線不連通、基準點不符或超出涵蓋時停止該方法，不以直線距離代替。
外部 MNI2CPC 頁可手動輸入作者工具所得 pNZ/pAL（0–1，不是百分比），映射到個人幾何。
外部比例與所輸入 MNI 的對應關係需自行核對。

匯出與資料來源
JSON 包含實際 scalp MSH、EEG CSV、FEM MSH、geometry_mode、座標與三組路徑。
另存個人 scalp Electrode CSV；這已是個人空間，不要當 MNI 再轉一次。
面板顯示目前配對，避免把原始與修補結果混用。方法標記線顯示抬高 0.4 mm，不影響弧長。
程式不自動上傳個案資料；文獻網站只在你按開啟時啟動瀏覽器。

測試與限制
詳見 VALIDATION.json。本環境完成自動測試與離屏 Qt 檢查，未做 Windows/OpenGL 實機電場求解。
未提供本個案完整 toMNI，實際非線性轉換需在完整 SimNIBS 安裝確認。

v1.80.2：已用 參考個案 原始 FEM 與 reviewed 補頂表面測試
原始 tag 1005 頭皮有 6 個邊界度數為 4 的頂點，距最終切面約 108–130 mm；並非新接縫造成。
本版允許完整保留距切面至少 10 mm 的既有原始邊界接觸，但逐一驗證頂點、相鄰所有三角面、
全部原始開口邊均不變；不把這些點焊接、移動或補洞。新接縫與 donor 頭頂仍嚴格檢查。
原始表面有非流形邊、重複面、退化面或分離元件時仍拒絕；異常點接近／超過切面也拒絕。
原始 LPA/RPA 距既有邊界約 3 mm：只有在投影點落在原始表面且周圍 10 mm 所有三角面
與原始模型一致時才允許沿用。新邊界、已改變的局部網格與 Cz 不適用此例外。
因此本版不宣稱整張頭皮已成為無缺陷流形，而是驗證局部修補沒有改變既有下方邊界。
個案測試：1,283 個新接縫三角面，0 個接縫開口、0 個接縫自交、0 個接縫非流形頂點；
57,376 個完整原始下方三角面與 876 條原始邊界邊保留。
儲存的 SimNIBS EEG 演算法以網格陣列介面執行，得到 91 個點位；尚未測試 Windows 安裝版 CLI。
請載入原 manifest，切面留白、接縫 4 mm，選新的空白輸出資料夾再執行⑤。不需重跑 DICOM／配準／遮罩。
自動切面使用原 T1 方向：本例選 h=126.7683566815 mm，不是水平 RAS Z，請勿直接填入手動 Z 欄位。
錯誤診斷檔仍為 topology_diagnostics.json、topology_boundary_vertices.csv 及 hybrid_manifest.json。
體積 FEM 保持原樣，模型切換與英文介面保留。
