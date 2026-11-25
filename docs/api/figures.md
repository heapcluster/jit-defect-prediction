# 妯″瀷鍥句欢鏌ヨ API锛坒igures锛?
涓€鍙ヨ瘽锛氬彧璇诲垪鍑鸿瘎浼拌繍琛屼骇鐢熷苟缁?storage 鐧昏鐨勬ā鍨嬪浘浠跺強鍙敤鐘舵€侊紝鎸夐壌鏉?URL 渚涢〉闈㈠彇鍥撅紝涓嶅湪鏌ヨ鏃惰绠楁寚鏍囨垨缁樺浘銆?
瀹炵幇鐘舵€侊細閮ㄥ垎銆€鏈熸锛氫竴鏈?
W2 宸叉敮鎸佸凡鐧昏杈撳嚭鍥句欢鐨勯壌鏉冧笅杞?URL 涓?checksum 鍙敤鎬ч獙璇侊紱鏂版壒娆′笉瀚佹帴鏃ч潤鎬佹寚鏍囥€傚畬鏁磋瘎浼版寚鏍囩殑鍚屾壒娆℃姇褰遍殢 W7 鎺ュ叆锛屽皻鏈疄鐜伴儴鍒嗕笉浣滈€氳繃璇佹嵁銆?
鍥炬枃浠?schema 涓庣被鍨嬪紩鐢?[../file-contracts.md](../file-contracts.md) 搂3.6锛宮anifest 寮曠敤 搂3.9锛涜瘎浼颁骇鐗╄ [evaluate.md](evaluate.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗鎸?model_name 杩斿洖 model_figure 涓櫥璁扮殑鍥剧被鍨嬨€佹爣棰樸€侀壌鏉?URL銆乧hecksum 鍜岀己鍥剧姸鎬併€?- 鏀寔 roc/pr/confusion/calibration/effort/feat_importance锛沞ffort-aware 涓?effort-unaware 涓ょ被鍥惧潎鍙櫥璁般€?- 涓嶈礋璐ｈ鍙栭潤鎬佹寚鏍囪〃鍏呭綋璇勪及锛屼笉璐熻矗閲嶇畻鎸囨爣銆侀娴嬨€佽缁冩垨鐢熸垚鏂板浘锛涙寚鏍囨暟鍊肩敱 evaluate 杈撳嚭鎻愪緵銆?
## 2. 绔偣濂戠害

### GET /api/figures

| 鍙傛暟 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `model_name` | 鏄?| 宸茬櫥璁版ā鍨?|
| `figure_type` | 鍚?| `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance` |
| `job_id` | 鍚?| 閫夋嫨宸茬櫥璁扮殑 evaluate 杈撳嚭鎵规锛涚己鐪佸彇璇ユā鍨嬫渶鏂扮櫥璁颁笖 manifest 瀹屾暣鐨勬壒娆?|

鍝嶅簲 `data`锛?
| 瀛楁 | 鍚箟 |
|---|---|
| `model_name` / `line` / `source_job_id` | 妯″瀷銆佹ā鍨嬬嚎涓庨€夊畾鐨?evaluate 鎵规 |
| `metrics[]` | 鍙璇ユ壒娆?evaluate_metrics 涓妯″瀷鐨?搂3.6 闀胯〃琛岋紱鏂囦欢涓嶅彲鐢ㄥ垯涓虹┖骞剁敱 metrics_unavailable 璇存槑 |
| `metrics_unavailable` | 鎸囨爣鏂囦欢缂哄け銆乧hecksum 涓嶇鎴栨壒娆℃棤姝ゆā鍨嬫椂鐨勫師鍥狅紝鏃犻棶棰樹负 null |
| `figures[]` | 纾佺洏鏍￠獙瀛樺湪鐨勫浘锛屾寜涓婅堪绫诲瀷鍥哄畾椤哄簭 |
| `figures[].figure_type` | 鍏被涔嬩竴锛沞ffort 椤瑰彟鍚?effort_kind |
| `figures[].effort_kind` | `aware` / `unaware`锛岄潪 effort 涓?null |
| `figures[].title` / `file_path` / `checksum_sha256` | 鏍囬銆侀壌鏉?URL 涓庢牎楠屽€?|
| `figures[].source_job_id` | 浜х敓璇ュ浘鐨?evaluate job |
| `missing[]` | 鏈夌櫥璁颁絾鏂囦欢鎴?checksum 鏍￠獙澶辫触鐨勯」鍙婂師鍥?|

`file_path` 鍙负 `/static/figures/...` 鎴栧彈鎺ц緭鍑轰笅杞?URL锛涗袱绉嶈矾寰勯兘瑕佹眰 X-API-Key銆俶etrics 鐨勯€愬瓧娈电粨鏋勫彧鑳芥槸 搂3.6 鐨?`model_name,line,metric,value,threshold,n,pos_rate,dataset_version,model_version,computed_at`锛屼粠鍚屼竴鎵规宸茬敓鎴愭枃浠跺彧璇绘姇褰憋紝鏈帴鍙ｄ笉閲嶇畻銆傛贩娣嗘暟鎹粠瀵瑰簲 evaluate 杈撳嚭鍙栧緱銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 缂?model_name銆乫igure_type 闈炴硶鎴栨湭鐭ュ弬鏁?|
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key`锛屽寘鎷?`/static` 鍙栧浘 |
| 40400 | 404 | 妯″瀷涓嶅瓨鍦ㄦ垨娌℃湁浠讳綍鍥句欢鐧昏 |
| 50000 | 500 | 鏈鏈熻鍙栭敊璇紱鍙鏈熺己鍥捐繘鍏?missing锛屼笉浣滀负 50000 |

## 3. 杈撳叆濂戠害

鏃犱笂浼犳枃浠躲€傛煡璇㈠彧鎺ュ彈妯″瀷銆佸浘绫诲瀷鍜屽彲閫?evaluate job_id锛涘浘涓?metrics 蹇呴』鏉ヨ嚜 搂3.6 evaluate 杈撳嚭鍙?搂3.9 manifest锛岀粡 storage 鏍￠獙鐧昏銆傜櫥璁拌矾寰勯檺瀹氬湪鍏佽闈欐€佹牴鎴?`temp/outputs` 鍐咃紝鎷掔粷缁濆浠绘剰澶栭儴璺緞涓?`..`銆?
搂3.6 瀵瑰浘鐨勯€愬瓧瀹氫箟涓猴細**鈥滃浘 png锛歳oc/pr/confusion/calibration/effort/feat_importance锛坋ffort 涓ょ被璇剧▼纭姹傦級銆傗€?* 鏂囦欢鏍煎紡闇€鏍￠獙 PNG 榄旀暟銆佸ぇ灏忓拰 checksum锛孲VG 鎴栦吉閫?PNG 涓嶅緱鍐掑厖銆?
## 4. 杈撳嚭濂戠害

GET 浠呰緭鍑?JSON 鍥句欢绱㈠紩涓庡凡鐢熸垚 metrics 鐨勫彧璇绘姇褰憋紝涓嶇敓鎴愭柊鍥俱€丆SV 鎴?manifest锛屼笉鍒涘缓杈撳嚭鐩綍銆傚浘銆乵etrics 涓庡叾鍘?evaluate manifest 浠嶇敱浜х敓瀹冧滑鐨勮緭鍑虹洰褰曟彁渚涳紱鏈帴鍙ｄ笉澶嶅埗銆侀噸鍛藉悕鎴栦慨鏀规枃浠躲€?
缂哄浘鏃?figures 涓嶅寘鍚笉鍙敤 URL锛宮issing 缁欏嚭鍘熷洜锛沜hecksum 鏀瑰彉瑙嗕负涓嶅彲鐢ㄣ€傞〉闈娇鐢ㄥ甫 X-API-Key 鐨?fetch 鑾峰彇浜岃繘鍒跺苟杞?ObjectURL锛屼笉鑳戒负 img 鏍囩鍏抽棴閴存潈銆?
## 5. 鍙厤缃」

- model_name銆乫igure_type 涓?job_id 涓烘煡璇㈤€夐」锛沞ffort_enabled 鎺у埗璇勪及鏄惁浜х敓 effort-aware 缁撴灉锛屼絾 figures 涓嶉殣钘忓凡鐧昏鍘嗗彶鍥俱€?- 闈欐€佹牴銆佽緭鍑烘牴鍜屽ぇ灏忛檺鍒跺睘浜庨儴缃插畨鍏ㄧ瓥鐣ワ紱闃堝€间笌鎸囨爣閰嶇疆鐢?evaluate 浣跨敤锛宖igures 涓嶅彟璁捐绠楅厤缃€?- `.env` 浠呮彁渚涘嚭鍘傝矾寰勯粯璁わ紝涓嶅厑璁搁€氳繃鏌ヨ鎸囧畾浠绘剰鏂囦欢绯荤粺璺緞銆?
## 6. 鐘舵€佹寔涔呭寲

- model_figure 鎸佷箙鐧昏妯″瀷銆佸浘绫诲瀷銆佽矾寰勫拰鏉ユ簮锛涙簮鏂囦欢浣嶄簬 `temp/outputs/<job_id>/`锛坓itignore锛夋垨鍙楁帶闈欐€佹牴銆?- 鍙鏌ヨ涓嶅垱寤?job銆佷笉鏀瑰浘銆佷笉鏀规寚鏍囷紱鏈嶅姟閲嶅惎鍚庣櫥璁颁粛鍦紝鏂囦欢缂哄け鎹疄杩涘叆 missing銆?- 鏂?evaluate 浜х墿缁?storage 鐧昏鍚庡彲鏃犻渶閲嶅惎鏌ヨ锛涙棫鐧昏涓嶈鐩栦笉鍚屾潵婧?job 鐨勫璁′俊鎭€?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/figures/`锛屽寘鍚悎娉?PNG銆佺己澶辨枃浠躲€乧hecksum 鏀瑰彉鍜屼吉閫犳牸寮忥紝浠ュ強瀵瑰簲 搂3.9 manifest銆?
- **姝ｅ父**锛氬悇鍥剧被鍨嬩笌 effort 涓ょ被鎸夊浐瀹氶『搴忚繑鍥烇紝URL 甯﹂壌鏉冨彲鍙栵紝source_job_id/checksum 涓庣櫥璁颁竴鑷淬€?- **杈圭晫**锛氭煇妯″瀷鍙湁閮ㄥ垎鍥俱€佹棤 effort-aware銆乫eat_importance 涓嶅彲鐢ㄣ€佹枃浠惰鍒犻櫎鍧囬€氳繃 figures/missing 鏄庣‘琛ㄨ揪銆?- **闈炴硶**锛氱己妯″瀷鍙傛暟銆侀潪娉曠被鍨嬨€佷吉閫?PNG銆佽矾寰勮秺鐣屻€佹棤/閿?API Key 杩斿洖 40001/40100/40400锛涗笉瑙﹀彂璇勪及璁＄畻銆?- 鍝嶅簲鏃犵鏈夋寚鏍囨潵婧愶紱鏀圭敤鎴烽槇鍊间笉浼氬鑷存湰鎺ュ彛缁樺浘锛屾柊鐨勫浘鍙兘鏉ヨ嚜 evaluate run銆?
## 8. 杈圭晫

figures 鏄瘎浼颁骇鐗╃殑灞曠ず绱㈠紩锛屼笉鏄瘎浼拌绠楀叆鍙ｃ€俥valuate 鍙緷 搂3.4 鏂囦欢锛堝惈閫忎紶鐪熸爣绛撅級鐙珛杩愯锛宻torage 鐧昏涓哄彲閫夊睍绀鸿矾寰勶紱鏁版嵁搴撴垨 figures 鏈嶅姟鍧囦笉鏄瘎浼板拰鍏朵粬妯″潡杩愯鍓嶇疆銆?