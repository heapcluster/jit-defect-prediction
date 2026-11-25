# 鏁版嵁搴撳瓨鍌ㄤ笌閰嶇疆涓績锛堝姛鑳?1锛?
瀹炵幇鐘舵€侊細閮ㄥ垎銆€鏈熸锛氫竴鏈?
## 涓€鍙ヨ瘽姒傝堪

鐙珛鐨勫瓨鍌ㄤ笌閰嶇疆宸ュ叿锛氳礋璐?12 琛ㄧ殑灞曠ず瀵煎叆涓庢寜琛ㄥ鍑恒€佺敤鎴烽厤缃€佷换鍔＄姸鎬佸拰璧勪骇鐧昏锛屼笉涓哄叾浠栨ā鍧楁壙鎷呬笟鍔¤绠楋紝涔熶笉鍏呭綋妯″潡闂存暟鎹€荤嚎銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

**璐熻矗**锛?
- 缁存姢 `commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit` 12 琛紱琛ㄧ粨鏋勭湡婧愪负 [`../../infra/schema.sql`](../../infra/schema.sql)锛屽瓧娈靛绾﹁ [`../database/README.md`](../database/README.md)銆?- 鎸変氦鎹㈡枃浠?schema 鑷姩璇嗗埆瀵煎叆鐩爣锛屾寜鑷劧閿箓绛?upsert锛涙寜鍗曡〃瀵煎嚭 CSV/XLSX锛屼緵灞曠ず椤佃鍙栦笌绂荤嚎浜ゆ帴銆?- 鎻愪緵鍏ㄥ眬閿笌妯″潡鍛藉悕绌洪棿閿殑璇诲彇銆佸崟閿洿鏂般€佹壒閲忔洿鏂般€佸垹闄ゅ拰鎭㈠榛樿鍊硷紱閰嶇疆鍐欏叆鍚庣珛鍗崇敓鏁堝苟鍦ㄩ噸鍚悗鎭㈠銆?- 鎻愪緵鏁版嵁闆嗐€佹ā鍨嬪伐浠躲€佺畻娉曘€佷换鍔＄姸鎬佺瓑璧勪骇鏌ヨ锛屼互鍙婄┖搴撳垵濮嬪寲銆佹棫搴撳崌绾у拰閲嶅鎵ц杩佺Щ銆?- 缁熶竴浠撳簱鎺ュ彛涓?ORM 璁块棶瑙勫垯锛岄伩鍏嶄笟鍔℃ā鍧楁暎鍐?SQL銆?
**涓嶈礋璐?*锛?
- 閲囬泦銆佹竻娲椼€佽缁冦€侀娴嬨€佽瘎浼般€佽В閲娿€佸畾浣嶄笌淇寤鸿绛夎绠椼€?- 鏇垮叾浠栨ā鍧椾繚瀛樺敮涓€浜や粯鐗╋紱妯″潡浜や粯浠ユ枃浠朵笌 manifest 涓哄噯锛屽鍏ュ簱鍙槸鍙€夊睍绀哄姩浣溿€?- 澶嶆潅缁勭粐鏉冮檺銆佸绉熸埛銆佹ā鍨嬫潈閲嶅湪绾跨紪杈戞垨瀹屾暣璐﹀彿浜у搧锛涘嚟璇佹槑鏂囦笉鍏ュ簱銆?
## 2 鐙珛杩愯鍏ュ彛

```bash
python infra/setup_mysql.py
python infra/migrate.py --database jit_demo
python -m app.cli storage import --file clean_dataset.csv
python -m app.cli storage export --table prediction --format csv --out ./out
python -m app.cli config get
python -m app.cli config put decision_threshold 0.3
```

| 鍏ュ彛 | 鍛戒护 / 绔偣 | 濂戠害 |
|---|---|---|
| CLI | `storage import/export`銆乣config get/put/delete`銆佸缓搴撲笌杩佺Щ鍛戒护 | 鍙劚绂?Web 鍗曠嫭鎵ц锛屼笌 API 璋冪敤鍚屼竴鏈嶅姟 |
| 瀵煎叆 API | `POST /api/storage/import` | multipart 涓婁紶浠讳竴鍙楁敮鎸佺殑浜ゆ崲鏂囦欢锛屽悓姝ヨ繑鍥炶瘑鍒粨鏋溿€乽psert 缁熻涓庢搷浣滄爣璇?|
| 瀵煎嚭 API | `GET /api/storage/export?table=<table>&format=csv\|xlsx` | 浠呮寜琛ㄥ鍑猴紝鏀寔璇ヨ〃宸插０鏄庣殑绛涢€変笌鍒嗛〉 |
| 閰嶇疆 API | `GET/PUT /api/config`銆乣PUT/DELETE /api/config/{key}` | 鍗曢敭涓庢壒閲忚鍐欙紱鎵归噺鏇存柊鍘熷瓙鐢熸晥 |
| 鏌ヨ API | `/api/datasets`銆乣/api/models`銆乣/api/algorithms`銆乣/api/jobs` 鏃?| 鍙璧勪骇涓庝换鍔＄姸鎬?|
| Web | 鏁版嵁绠＄悊涓庤缃〉 | 浠呮槸瀵煎叆銆佸鍑恒€侀厤缃笌璧勪骇灞曠ず鍏ュ彛 |

鎵€鏈?HTTP 绔偣锛堝惈瀵煎嚭涓嬭浇锛夊繀椤讳娇鐢?`X-API-Key`锛涙暟鎹簱鍙ｄ护銆丄PI Key銆丩LM Key 绛夊嚟璇佸彧浠庡畨鍏ㄧ幆澧冩敞鍏ワ紝涓嶅啓鍏ラ厤缃〃銆佹棩蹇楁垨瀵煎嚭鏂囦欢銆?
## 3 杈撳叆濂戠害

- 璺ㄦā鍧楁枃浠跺彧鎺ュ彈 [`../file-contracts.md`](../file-contracts.md) 搂3.1鈥?.8 宸插畾涔夌殑 schema锛毬?.1 `collected_commits.csv`銆伮?.2 `clean_dataset.csv`銆伮?.3 `model_package.zip` 涓?`train_testset.csv`銆伮?.4 `predictions.csv`銆伮?.6 鎸囨爣/娣锋穯/鎶ュ憡涓庡浘銆伮?.7 `explanations.csv`銆伮?.8 瀹氫綅/寤鸿/琛ヤ竵棰勮锛沵anifest 閬靛惊 搂3.9銆傛棫 搂3.5 `labels.csv` 宸插簾姝紝涓嶅啀浣滀负瀵煎叆绫诲瀷銆侰SV/XLSX 鐨勭紪鐮併€佺┖鍊煎拰瀹夊叏瑙勫垯閬靛惊 搂1锛屼笉鍙﹁鍒楀悕銆?- 瀵煎叆鍣ㄤ緷鎹垪闆嗗悎銆佸伐浠跺唴瀹逛笌 manifest 璇嗗埆绫诲瀷鍜岀洰鏍囪〃锛涙棤娉曡瘑鍒€乻chema 缂哄垪銆佺被鍨嬮敊璇€乧hecksum 涓嶇鎴栧紩鐢ㄥ璞＄己澶辨椂鏄庣‘鎷掔粷锛屼笉鐚滄祴鏄犲皠銆佷笉浜у崐鎵瑰啓鍏ャ€?- 鏈夎〃璇箟鐨勬枃浠舵寜涓嬪垪瑙勫垯瀵煎叆锛涙病鏈夊搴旇〃璇箟鐨勮В閲娿€佸畾浣嶃€佸缓璁拰鎶ュ憡鏂囦欢浠嶄互鍘熸枃浠朵氦浠橈紝涓嶅己琛屽鍏ュ叾浠栬〃銆?
| 杈撳叆 | 鐩爣涓庡箓绛夊彛寰?|
|---|---|
| 搂3.1 / 搂3.2 琛ㄦ牸 | `commit`銆乣commit_feature` 鎸夋彁浜よ嚜鐒堕敭 upsert锛涙彁渚涙暟鎹泦鍏冩暟鎹椂鍚屾椂鐧昏 `dataset`銆乣dataset_commit` |
| 搂3.3 妯″瀷鍖?| 鏍￠獙鍚庣櫥璁?`model_artifact`锛屽苟娲剧敓 upsert `model` |
| 搂3.3 娴嬭瘯闆?| `train_testset` 鎸夋彁浜よ嚜鐒堕敭鐧昏 `dataset_commit`锛屾瘡琛屽甫鐪熸爣绛?|
| 搂3.4 琛ㄦ牸 | `prediction` 鎸夋彁浜や笌妯″瀷鑷劧閿?upsert锛涙爣绛鹃€忎紶鑷?搂3.3 娴嬭瘯闆嗭紝鏈墦鏍囦繚鎸?NULL |
| 搂3.6 鍥惧舰涓庢姤鍛婄储寮?| `model_figure` 鎸夋ā鍨嬩笌鍥剧被鍨?upsert锛涙暟鍊兼枃浠舵湰韬繚鐣欎负浜や粯鏂囦欢 |
| 閰嶇疆涓庤祫浜у厓鏁版嵁 | `user`銆乣user_config`銆乣algorithm`銆乣dataset`銆乣model_artifact` 鐨勬樉寮忕鐞嗚緭鍏ワ紝鎸夊悇琛ㄥ绾︽牎楠?|

- 鏃?`labels.csv` 宸插簾姝細鏍囩闅?predictions 閫忎紶锛屼笉鐙珛涓婁紶鏍囩鏂囦欢銆傚閿垨鐧昏寮曠敤涓嶆弧瓒虫椂杩斿洖鍙瘖鏂敊璇€?- 瀵煎嚭杈撳叆鏄?12 琛ㄤ箣涓€鐨勮〃鍚嶃€佹牸寮忎笌绛涢€夋潯浠讹紱绂佹浠绘剰 SQL銆佷换鎰忚〃鍚嶅拰璺ㄨ〃鎷兼帴瀵煎嚭銆?
## 4 杈撳嚭濂戠害

| 杈撳嚭 | 鏂囦欢 / 缁撴灉 |
|---|---|
| 瀵煎叆鍥炴墽 | `storage_import_<job_id>.json`锛氳瘑鍒?schema銆佺洰鏍囪〃銆佹彃鍏?鏇存柊/璺宠繃/澶辫触璁℃暟銆佸啿绐佷笌閿欒鍘熷洜 |
| 鎸夎〃瀵煎嚭 | `storage_export_<table>_<job_id>.csv`锛屽彲閫夊悓鍚?`.xlsx`锛涘鍑哄垪涓虹洰鏍囪〃 DDL 鍒楋紝涓嶅啋鍏?搂3.1鈥?.8 浜ゆ崲 schema |
| 閰嶇疆蹇収 | API/CLI 杩斿洖鐢熸晥閿€笺€佹潵婧愬拰鏇存柊鏃堕棿锛涘彲瀵煎嚭鑴辨晱閰嶇疆蹇収锛岀粷涓嶅寘鍚嚟璇?|
| 璧勪骇涓庝换鍔℃煡璇?| 鏁版嵁闆嗐€佹ā鍨嬪伐浠躲€佺畻娉曞拰鍏被浠诲姟鐘舵€侊紝涓庢暟鎹簱璁板綍涓€鑷?|
| 杩佺Щ缁撴灉 | 鍒濆鍖?鍗囩骇/閲嶅鎵ц鐘舵€併€佺粨鏋勬牎楠屼笌鍙鏃ュ織 |
| manifest | 姣忎釜瀵煎嚭鎴栧鍏ュ洖鎵у潎浼?`storage_<artifact>_<job_id>.manifest.json`锛岃褰曡緭鍏ヨ緭鍑?checksum銆侀厤缃笌浠ｇ爜鐗堟湰锛岄伒寰?搂3.9 |

鍛藉悕缁熶竴涓?`<module>_<artifact>_<job_id>.<ext>`锛涜繖閲岀殑 `job_id` 鏄悓姝ュ鍏?瀵煎嚭鎿嶄綔鍏宠仈鍙凤紝涓嶆柊澧炵涓冪浠诲姟 kind銆備笅杞戒娇鐢?`GET /api/storage/outputs/{job_id}/{name}`锛涜〃瀵煎嚭鏂囦欢娴佷篃鍙洿鎺ョ敱 export 绔偣杩斿洖銆?
## 5 鍙厤缃」

鍏ㄥ眬閿殑鍞竴鎸佷箙鍖栨潵婧愭槸 `user_config`锛涜鍙栭『搴忎负褰撳墠鐢ㄦ埛琛?鈫?`global` 琛?鈫?閰嶇疆鏈嶅姟鍐呭嚭鍘傞粯璁ゅ€硷紝鍓嶇鍜屼笟鍔℃ā鍧椾笉寰楀彟寤烘潈濞佸壇鏈€?
| 鍏ㄥ眬閿?| 榛樿涓庣害鏉?|
|---|---|
| `decision_threshold` | 0.5锛屽紑鍖洪棿 (0,1) |
| `risk_high_threshold` / `risk_mid_threshold` | 0.5 / 0.2锛屽潎鍦?(0,1)锛屼笖 mid < high |
| `default_dataset` | 鍙负绌猴紱闈炵┖鏃堕』鎸囧悜宸茬櫥璁版暟鎹泦锛涗笉璁?`default_model` |
| `default_xai` | `shap`锛岄』灞炰簬瑙ｉ噴鍣ㄦ敞鍐岃〃 |
| `metrics_selected` / `primary_metric` / `effort_enabled` | 鍏」鍩虹鎸囨爣 / `auc` / `true`锛涗富鎸囨爣椤诲睘浜庡凡閫夋寚鏍?|
| `page_prefs` | 鐧藉悕鍗曞璞?|

妯″潡鍛藉悕绌洪棿閿悓鏍疯惤鍏?`user_config`锛歚collect.allow_roots`銆乣collect.protocol_whitelist`銆乣clean.chain_templates`銆乣train.templates`銆乣predict.batch_size`銆乣predict.cache_ttl`銆乣predict.retry_max`銆乣explain.cache_ttl`銆乣explain.compare_enabled`銆乣localization.weights`銆乣localization.top_n`銆乣localization.file_size_max`銆乣localization.suggestion_sources`銆備簩鏈?extension 鐨勬姤鍛娿€侀棬绂併€佸け璐ョ瓥鐣ュ拰浜嬩欢閿篃鎸夎妯″潡 搂5 钀藉叆鍚屼竴閰嶇疆涓績銆傛湭鐭ラ敭銆佺被鍨嬮敊璇€佽秺鐣屽€间笌璺ㄩ敭绾︽潫杩濆弽鍧囨嫆缁濓紱鎭㈠榛樿鍊奸€氳繃鍒犻櫎鐢ㄦ埛瑕嗙洊瀹炵幇銆?
## 6 鐘舵€佹寔涔呭寲

- 12 琛ㄥ彧鎵挎媴灞曠ず瀵煎叆銆侀厤缃€佷换鍔＄姸鎬佸拰璧勪骇鐧昏銆俙model` 琛岀敱 `model_artifact` 娲剧敓锛沗algorithm` 鏄畻娉曚笌瓒呭弬 schema 鐨勭櫥璁版簮锛涙暟鎹泦澶氱増鏈睘浜屾湡锛屼竴鏈熶笉鏀瑰彉鏃㈡湁涓婚敭銆?- `job` 鍙寘鍚?`collect / clean / train / predict_batch / evaluate / explain` 鍏被锛岀姸鎬佸彧鍖呭惈 `queued / running / success / failed / cancelled`锛涘悓 kind 鍚屾椂鏈€澶氫竴涓?running锛屽惎鍔ㄦ椂灏嗛仐鐣?running 缃?failed 骞朵繚鐣欒繘搴︺€?- 瀵煎叆閲囩敤浜嬪姟涓庡箓绛?upsert锛涗竴鎵逛腑鏍￠獙澶辫触鏃朵笉寰楃暀涓嬩笉鍙В閲婄殑鍗婃壒鐘舵€併€傚鍑轰粠宸叉彁浜ゅ揩鐓ц鍙栵紝閲嶅瀵煎嚭鍐呭涓€鑷淬€?- 閰嶇疆鎵归噺鏇存柊鍘熷瓙鐢熸晥锛涜繘绋嬨€佸鍣ㄥ紓甯稿叧闂悗閲嶅惎锛屽叏灞€閿€佸懡鍚嶇┖闂撮敭銆佽祫浜у拰浠诲姟鐘舵€佸潎鍙仮澶嶃€?- 瀵煎叆鍥炴墽銆佸鍑烘枃浠跺拰 manifest 钀界洏 `temp/outputs/<job_id>/`锛沗temp/outputs/` 蹇呴』鏁翠綋鍔犲叆 gitignore銆傛暟鎹簱鍙繚瀛樺紩鐢ㄤ笌鍏冩暟鎹紝涓嶆浛浠ｆ枃浠朵氦浠樸€?- 寤鸿〃鐪熸簮銆佽縼绉昏剼鏈拰 ORM 蹇呴』鍚屾锛涚┖搴撳垵濮嬪寲銆佹棫搴撳崌绾с€侀噸澶嶆墽琛屽潎闇€缁撴瀯涓€鑷翠笖涓嶇牬鍧忓凡鏈夋暟鎹€?
## 7 涓庡叾浠栨ā鍧楄竟鐣?
- 鍏朵粬妯″潡鐨勭嫭绔嬭繍琛屽彧瑕佹眰浜ゆ崲鏂囦欢 schema 鍏煎锛屼笉瑕佹眰鏈ā鍧楀凡鏈夋暟鎹紱闇€瑕佸簱涓究鍒╄緭鍏ユ椂锛岀敱鍚勬ā鍧?run 绔偣鏄惧紡鎺ユ敹鍙€?`dataset_id`銆?- 灞曠ず椤佃鍙栧鍏ュ悗鐨勮〃锛涗笟鍔℃ā鍧椾笉寰楅€氳繃璇诲彇灞曠ず琛ㄦ潵浠ｆ浛鑷繁鐨勬枃浠惰緭鍏ワ紝涔熶笉寰楁妸鍏朵粬妯″潡鐨勫唴瀛樻垨鏈嶅姟瀛樻椿褰撲綔鍓嶆彁銆?- 鍘熺敱闆嗕腑鏁版嵁鍚屾椤甸潰鎵挎媴鐨勨€滃鍏ュ簱灞曠ず鈥濊亴璐ｅ綊鏈ā鍧楋紱妯″瀷鎬ц兘鏁板€笺€佸浘涓庢姤鍛婄殑璁＄畻鑱岃矗褰?evaluate锛屾湰妯″潡鍙繚瀛樺睍绀虹储寮曘€?- 鍏紑 JIT 缂洪櫡鏁版嵁闆嗕笌 Git 閲囬泦缁撴灉鍚屽彛寰勶細榛樿钀界洏骞朵繚瀛?`dataset` + `dataset_commit`锛孧UST NOT 浠呭叆搴撲笉钀界洏锛涘彛寰勮 [collect.md](collect.md) 搂3.2 涓?搂6銆?
## 8 楠屾敹鏍囧噯

fixtures 浣嶄簬 `tests/fixtures/files/storage/`锛堝悗绔笌妯″瀷绾挎祴璇曟牴鐩綍鎸?file-contracts 搂1 鏄犲皠锛夛紝蹇呴』鍖呭惈姝ｅ父銆佽竟鐣屻€侀潪娉曚笁绫伙紱鏃犻渶鍏堣繍琛屼换浣曚笟鍔℃ā鍧椼€?
- 姝ｅ父 fixture 鑳借鑷姩璇嗗埆鍒版纭洰鏍囪〃锛岄噸澶嶅鍏ユ棤閲嶅琛岋紱闈炴硶 schema銆乧hecksum銆佹湭鐭ラ厤缃敭銆佽秺鏉冧笌浠绘剰琛ㄥ鍑哄潎琚嫆缁濅笖鏃犲崐鎴愬搧銆?- CSV/XLSX 瀵煎嚭鍙墦寮€銆佷腑鏂囦笉涔辩爜銆佺瓫閫夌敓鏁堬紱瀵煎嚭鍒椾笌鐩爣琛ㄤ竴鑷达紝manifest checksum 瀹屾暣锛屽ぇ鏁版嵁閲忓垎椤靛鍑洪€氳繃銆?- 寤鸿〃涓庤縼绉诲湪绌哄簱銆佹棫搴撱€侀噸澶嶆墽琛屼笁绉嶅満鏅€氳繃锛涙帴鍙ｆ煡璇㈢殑鏁版嵁闆嗐€佹ā鍨嬪伐浠跺拰绠楁硶涓庡簱涓褰曚竴鑷淬€?- 淇濆瓨鍏ㄥ眬閿強鍏ㄩ儴鍛藉悕绌洪棿閿悗锛屽仠姝㈠苟寮傚父閲嶅惎鍚庣锛屽€间粛鍙仮澶嶏紱鎵归噺鏇存柊浠讳竴鍊奸潪娉曞垯鏁存壒涓嶅啓锛屾仮澶嶉粯璁ゅ€肩敓鏁堛€?- 鍏被浜旀€併€佸悓 kind 浜掓枼銆侀噸鍚?running 缃?failed 鍧囨湁娴嬭瘯锛涙晱鎰熶俊鎭壂鎻忚瘉鏄庨厤缃€佹棩蹇椼€佸洖鎵т笌瀵煎嚭涓嶅惈鍑瘉銆?- 鎵挎帴 TODO/01锛氬墠绔鍙栨寔涔呭寲閰嶇疆鑰岄潪鎶婂父閲忎綔涓哄敮涓€鏉ユ簮锛涜縼绉汇€侀厤缃鍐欍€侀噸鍚仮澶嶅拰璧勪骇鏌ヨ鍧囨湁鑷姩鍖栨祴璇曘€?