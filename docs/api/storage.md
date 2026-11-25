# 鏁版嵁搴撳瓨鍌ㄤ笌瀵煎叆瀵煎嚭 API锛坰torage锛?
涓€鍙ヨ瘽锛氭妸绗﹀悎鏉冨▉ schema 鐨勪氦鎹㈡枃浠舵寜鍐呭鑷姩璇嗗埆骞跺箓绛?upsert 鍒?12 琛紝鍚屾椂鎸夎〃瀵煎嚭 CSV/XLSX 涓?manifest锛屾壙鎷呭睍绀哄鍏ャ€侀厤缃拰璧勪骇鐧昏鑰岄潪妯″潡闂存暟鎹紶閫掋€?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
W2 宸插疄鐜版枃浠跺鍏ャ€佹ā鍨嬪寘/PNG 鐧昏銆?2 琛ㄥ鍑哄拰浜х墿涓嬭浇銆傛ā鍨嬪寘鍙仛缁撴瀯/checksum 鏍￠獙涓庝笉閫忔槑鐧昏锛屼笉鎵ц鏉冮噸锛涘凡鍔犺浇妯″瀷绂佹琚柊鍖呴噸鏍囷紝鍚庣画鍔犺浇绠＄悊鐢?W6 瀹屾垚銆?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.1鈥撀?.9锛涜〃瀛楁浠?[../database/README.md](../database/README.md) 涓庡悇琛ㄦ枃妗ｄ负鍑嗐€?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗 `commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit` 12 琛ㄧ殑瀵煎叆銆佸鍑恒€佸睍绀烘煡璇㈡敮鎸佷笌璧勪骇鐧昏銆?- 瀵煎叆鎸夋枃浠?schema 鑷姩璇嗗埆鐩爣锛屼笉瑕佹眰璋冪敤鏂规寚瀹氳〃锛涜嚜鐒堕敭骞傜瓑 upsert锛岄噸澶嶅鍏ヤ笉浜х敓閲嶅琛屻€?- 閰嶇疆鍜?job 鐘舵€佷粛鎸佷箙鍖栵紱妯″瀷鍖呯櫥璁板悗娲剧敓 model 琛岋紝鏂囦欢鏈綋缁х画钀借緭鍑虹洰褰曘€?- 涓嶈礋璐ｉ噰闆嗐€佹竻娲椼€佽缁冦€侀娴嬨€佽瘎浼般€佽В閲婃垨瀹氫綅璁＄畻锛屼篃涓嶈姹備换浣曟ā鍧楀厛瀵煎叆鎵嶈兘杩愯銆?
## 2. 绔偣濂戠害

### GET /api/storage/tables

鍝嶅簲 `{items:[{name,columns,filters}]}`锛岃〃涓庡垪鍙栬嚜鐪熷疄 12 琛ㄥ畾涔夛紱鍓嶇浠ヨ鍏冩暟鎹覆鏌撳彲鐢ㄨ〃鍙婇€傜敤绛涢€夛紝涓嶅彟閫犵櫧鍚嶅崟銆傛墍鏈夌鐐瑰惈涓嬭浇鍧囪姹?X-API-Key锛屼笂浼犻壌鏉冨拰璇锋眰鎬诲ぇ灏忓湪 multipart 瑙ｆ瀽鍓嶆牎楠屻€?
### POST /api/storage/import

鍚屾 `multipart/form-data`锛歚files[]` 涓婁紶涓€涓垨澶氫釜浜ゆ崲鏂囦欢锛宍config` 涓哄彲閫?JSON part銆?
| config 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `dataset_id` | 鍚?| 瀵煎叆 collected_commits / clean_dataset 鏃跺叧鑱旀棦鏈?dataset锛涗笉瀛樺湪杩斿洖 40400 |
| `create_dataset` | 鍚?| `{name,repo_source,branch,head_hash}`锛岄渶瑕佹柊鏁版嵁闆嗘椂涓?collected_commits / clean_dataset 鍚屼紶 |
| `model_artifact_status` | 鍚?| 妯″瀷鍖呯櫥璁板垵濮嬬姸鎬侊紝浠呭厑璁?`available` / `retired`锛岄粯璁?available |
| `register_figures` | 鍚?| 榛樿 true锛沞valuate 鍥惧強 manifest 鍙櫥璁?model_figure |

鍝嶅簲 `data`锛歚{items[],summary}`銆傛瘡涓枃浠堕」涓?`{name,schema,target_tables[],status,inserted,updated,unchanged,rejected,errors[]}`锛泂ummary 姹囨€诲悇鐘舵€佹暟銆傚崟鏂囦欢澶辫触涓嶅奖鍝嶅叾浠栧悎娉曟枃浠讹紝浣嗗悓涓€鏂囦欢鐨勫琛ㄥ啓鍏ュ繀椤诲湪涓€涓簨鍔″唴瀹屾垚銆?
鑷姩璇嗗埆瑙勫垯锛?
| 杈撳叆 | 鏉冨▉ schema | 鐩爣涓庣害鏉?|
|---|---|---|
| collected_commits / clean_dataset | 搂3.1銆伮?.2 | dataset + dataset_commit锛涗笉鍐?commit_feature |
| train_testset | 搂3.3 | 娴嬭瘯闆嗭紝鎸夋彁浜よ嚜鐒堕敭鐧昏 dataset_commit锛涙瘡琛屽甫鐪熸爣绛?|
| predictions | 搂3.4 | prediction锛屾寜 `(commit_hash,model_name)` upsert锛沗is_bug_inducing` 閫忎紶鐪熸爣绛?|
| model_package | 搂3.3 | 鏍￠獙鍚庣櫥璁?model_artifact 骞舵淳鐢?model锛沜hecksum 涓嶇鎷掔粷 |
| evaluate 鍥惧強 manifest | 搂3.6銆伮?.9 | 鎸夋ā鍨嬩笌 figure_type 鐧昏 model_figure锛岃矾寰勫彧鎸囧厑璁歌緭鍑烘牴鍐呮枃浠?|
| metrics/confusion/report銆乪xplanations銆乴ocalization/suggestions/patch | 搂3.6鈥撀?.8 | 12 琛ㄦ棤瀵瑰簲缁撴灉琛紝杩斿洖 40001 `unsupported_storage_schema`锛屼笉鍋囪瀵煎叆 |

### GET /api/storage/export

鏌ヨ鍙傛暟锛歚table=<12琛ㄤ箣涓€>`锛堝繀濉級銆乣format=csv|xlsx`锛堥粯璁?csv锛夛紱鍙€?`dataset_id/model_name/start_time/end_time/limit` 鍙帴鍙楄琛ㄩ€傜敤鐨勭瓫閫夛紝鏈煡銆侀噸澶嶆垨涓嶉€傜敤鍙傛暟鎷掔粷銆傚悓姝ヨ繑鍥?`data:{job_id,table,format,outputs[],manifest_name,columns,preview,row_count,total}`锛沺review 鏈€澶?0琛岋紝limit 璇锋眰鐢熸垚棰勮鎵规锛屽畬鏁翠笅杞介噸鏂拌姹備笉甯?limit銆俲ob_id 鍙綔瀵煎嚭鎵规鏍囪瘑锛屼笉鏂板 job kind銆俹utputs 鍚富琛ㄤ笌 manifest 鐨勫悕绉般€佸瓧鑺傛暟鍙?checksum銆?
### GET /api/storage/outputs/{job_id}/{name}

涓嬭浇瀵煎嚭涓昏〃鎴?manifest锛涘彧鍏佽瀵煎嚭鎵规鐧昏鐨勫熀纭€鏂囦欢鍚嶃€?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | schema 鏃犳硶璇嗗埆銆佸垪/绫诲瀷闈炴硶銆佽嚜鐒堕敭鍐茬獊銆佹棤鐩爣琛ㄣ€乧hecksum 澶辫触銆侀潪娉?table/format銆佸叕寮忔敞鍏?|
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key`锛屽寘鎷鍑轰笅杞?|
| 40400 | 404 | dataset銆佸鍑烘壒娆℃垨鏂囦欢涓嶅瓨鍦?|
| 50000 | 500 | 鏁版嵁搴撴垨鏈鏈熸湇鍔￠敊璇紱浜嬪姟鍥炴粴锛屼笉鍥炴樉 SQL/杩炴帴涓?|

## 3. 杈撳叆濂戠害

鎵€鏈変氦鎹㈠垪鍙帴鍙?[../file-contracts.md](../file-contracts.md) 搂3.1鈥撀?.8锛屼笉鑳介€氳繃澧炲姞鍒悕缁曡繃璇嗗埆銆傚叧閿?schema 閫愬瓧寮曠敤濡備笅銆?
搂3.1 collected_commits锛?
| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40 hex) | 鏄?| 鎻愪氦鏍囪瘑锛堝皬鍐欙級 |
| repo_name | string | 鏄?| 浠撳簱鍚嶆垨鏁版嵁闆嗗悕 |
| repo_url | string | 鍚?| 鏉ユ簮 URL |
| author_name / author_email | string | 鍚?| 浣滆€?|
| committed_at | datetime | 鍚?| 鎻愪氦鏃堕棿 UTC |
| message | string | 鍚?| 鎻愪氦淇℃伅 |
| parent_hash | string(40) | 鍚?| 鐖舵彁浜?|
| is_bug_inducing | int 绌哄彲 | 鏄?| 缂洪櫡鏍囩 1/0/绌?|
| label_method | string | 鍚?| `szz_v1` / `szz_lite` / `third_party` |
| label_source | string | 鏄?| `git_szz` / `public_dataset` |
| labeled_at | datetime | 鍚?| 鎵撴爣鏃堕棿 |
| fix_commit_hash | string(40) | 鍚?| SZZ 鍥炴函淇鎻愪氦 |
| source_type | string | 鏄?| `git_repo` / `public_dataset` |

搂3.2 clean_dataset锛氬垪鍚?搂3.1锛屽彲杩藉姞 `derive_basic_fields` 鍩虹灞曠ず鍒楋紱涓嶅緱鍚?Kamei 14 缁存ā鍨嬬壒寰併€乣is_test` 鎴栬缁冩祴璇曞垝鍒嗐€傚繀浼?`steps_stats.json` 涓庡垪缁熻/鍒嗗竷鍥撅紝浣嗙粺璁″拰 png 涓嶆槧灏勪负鏁版嵁搴撹〃銆?
搂3.4 predictions锛?
| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40) | 鏄?| 鎻愪氦 |
| model_name | string | 鏄?| 妯″瀷 |
| risk_score | float [0,1] | 鏄?| 姒傜巼锛? 浣嶅皬鏁帮級 |
| predicted_label | int 0/1 | 鏄?| 鎸?decision_threshold 鐨勪簩鍒嗙被鏍囩 |
| decision_threshold | float | 鏄?| 鏈鍒ゅ畾闃堝€?|
| model_version / feature_version | string | 鏄?| 鐗堟湰鍏冧俊鎭?|
| predicted_at | datetime | 鏄?| 棰勬祴鏃堕棿 |
| is_bug_inducing | int 绌哄彲 | 鍚?| 閫忎紶鐪熸爣绛撅紙鏉ヨ嚜 搂3.3 `train_testset`锛屼緵 evaluate 绠楁€ц兘锛?|

搂3.5 `labels.csv` 宸插簾姝細鐪熸爣绛剧粺涓€鐢?搂3.3 `train_testset` 鎻愪緵骞剁敱 predict 閫忎紶杩?搂3.4 `predictions.csv`锛泂torage 涓嶅啀瀵煎叆鐙珛鏍囩鏂囦欢锛屽鍏?predictions 鏃舵寜 hash 鍚屾鍏堕€忎紶鏍囩锛屾湭鎵撴爣淇濇寔 NULL銆?
搂3.3锛?*鈥渮ip 鍐呭惈锛氭潈閲嶆枃浠跺潎涓?`.pkl`锛坄expert`=Kamei 14 缁淬€乣semantic`=鍐荤粨澶?CodeBERT 768 缁达級銆乣feature_order.txt`銆乣feature_schema.json`銆乣model_meta.json`锛坢odel_name/line/algo/feature_set/version_key/feature_version/trained_at/瓒呭弬蹇収/鍒掑垎 mode/绉嶅瓙锛夈€乣checksum.sha256`銆俙fused` / `e2e` 鍙婂叾 safetensors 浜х墿宸插彇娑堛€俻redict/explain MUST 鏍￠獙 checksum 涓庣壒寰佸垪瀹藉悗鍐嶅姞杞姐€傗€?* storage 鐧昏鍓嶅悓鏍锋牎楠?checksum銆?
瀹夊叏瑕佹眰锛氶檺鍒跺ぇ灏忋€佹墿灞曞悕涓庨瓟鏁般€乑IP 瑙ｅ帇澶у皬鍜岃矾寰勩€佸垪 schema銆佸叕寮忔敞鍏ワ紱瀛樺偍璺緞闄愬畾鍏佽杈撳嚭鏍癸紝鏂囦欢鍚嶄笉鎷兼帴 shell銆傛晱鎰熼厤缃€丄PI Key銆佸彛浠ゅ拰 LLM Key 涓嶅厑璁搁€氳繃 import 鍐欏叆 user_config銆?
## 4. 杈撳嚭濂戠害

瀵煎叆鍙繑鍥?JSON 缁熻骞跺啓鏁版嵁搴擄紝涓嶅垱寤烘柊鐨勪氦鎹㈡枃浠讹紱杈撳叆鏂囦欢鍘熸湁 manifest 涓嶅弬涓庤鐩栨牎楠屾椂涓嶅緱浼€犲鍏ュ洖鎵ф枃浠躲€?
瀵煎嚭鏂囦欢鍛藉悕锛?
| 鏂囦欢 | 鍛藉悕 | 鍐呭 |
|---|---|---|
| 琛ㄤ富鏂囦欢 | `storage_<table>_<job_id>.csv`锛屾垨 `.xlsx` | table 瀵瑰簲鏁版嵁搴撹〃濂戠害鐨勫瓧娈碉紝鎸夎〃瀹氫箟椤哄簭瀵煎嚭锛涗笉鍙﹂€犱氦鎹㈠垪鍚?|
| manifest | `storage_<table>_<job_id>.manifest.json` | 涓ユ牸閲囩敤 搂3.9锛宮odule=`storage`锛宑onfig 璁板綍 table/format锛宨nputs 璁板綍瀵煎嚭杩囨护鏉′欢锛宱utputs 璁板綍 checksum |

褰撳鍑哄唴瀹圭敤浜庢ā鍧椾氦鎹㈡椂锛屽繀椤婚€夋嫨骞舵弧瓒冲搴?搂3.x锛岃€屼笉鏄妸鏁版嵁搴撳唴閮ㄥ瓧娈垫敼鍚嶅悗鍐掑厖浜ゆ崲鏂囦欢锛歝ommit + commit_feature 鐨勭粍鍚堝鍑轰娇鐢?搂3.1锛宲rediction 鐨勪氦鎹㈠鍑轰娇鐢?搂3.4銆傚崟琛ㄥ師濮嬪鍑哄彧鐢ㄤ簬瀛樺偍绠＄悊锛屼笉瀹ｇО鍙洿鎺ヤ綔涓烘ā鍧楄緭鍏ャ€?
CSV 榛樿 UTF-8 BOM锛孹LSX 鍗?sheet锛岀┖鏍囩鍜岀己棰勬祴淇濇寔绌哄€硷紱鍏紡娉ㄥ叆杞箟銆傚鍑烘槸鍚屾鎵规锛屾棤鐙珛 job kind锛屼絾鏂囦欢浠嶈惤缁熶竴杈撳嚭鐩綍骞跺繀浼?manifest銆?
## 5. 鍙厤缃」

- storage 鏈韩娌℃湁鏂板涓氬姟璁＄畻閰嶇疆锛泃able銆乫ormat銆乨ataset 鍏宠仈鍜岃祫浜х櫥璁伴€夐」闅忚姹傜粰鍑哄苟杩涘叆瀹¤/manifest銆?- 鍏ㄥ眬鍙婃ā鍧楀懡鍚嶇┖闂撮厤缃粺涓€缁?[config.md](config.md) 璇诲啓锛沗.env` 浠呮彁渚涘嚭鍘傞粯璁ゃ€?- 鏁版嵁搴撹繛鎺ャ€丄PI Key 涓庡叾浠栧瘑閽ュ彧璧伴儴缃茬幆澧冿紝绂佹閫氳繃閰嶇疆瀵煎叆鎴栧鍑烘帴鍙ｈ鍙栥€?- 瀵煎嚭琛屼笂闄愩€佹枃浠跺ぇ灏忎笌涓婁紶闄愬埗浣跨敤缁熶竴瀹夊叏绛栫暐锛屼笉寰椾负鍗曡〃缁曡繃銆?
## 6. 鐘舵€佹寔涔呭寲

- 瀵煎叆浠ュ崟鏂囦欢浜嬪姟淇濊瘉澶氳〃鍘熷瓙鎬э紱鑷劧閿?upsert 骞傜瓑锛屽け璐ュ洖婊氳鏂囦欢鍏ㄩ儴鍐欏叆骞惰繑鍥炲彲璇?errors銆?- 12 琛ㄦ寔涔呬繚瀛樺睍绀烘暟鎹€佺敤鎴烽厤缃€佸叚绫?job 鍜岃祫浜э紱鏈嶅姟閲嶅惎鍚庨厤缃笌浠诲姟鐘舵€佹仮澶嶃€?- storage import/export 涓嶆柊澧?job kind锛涘鍑?job_id 鏄枃浠舵壒娆℃爣璇嗭紝涓嶈兘鐢ㄤ簬 `/api/jobs/{id}`銆?- 瀵煎嚭钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紱妯″瀷鍖呭彲鐧昏璺緞鍜?checksum锛屼絾鏉冮噸鏂囦欢鍐呭涓嶅叆搴撱€?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/storage/`锛屽寘鍚悇鏉冨▉ schema銆侀噸澶嶆壒娆′笌闈炴硶鏂囦欢锛屼笉瑕佹眰浠讳綍涓氬姟妯″潡鍏堣繍琛屻€?
- **姝ｅ父**锛歝ollected_commits銆乧lean_dataset銆乼rain_testset銆乸redictions銆佹ā鍨嬪寘鍒嗗埆鑷姩璇嗗埆鍒扮洰鏍囪〃锛涢噸澶嶅鍏?inserted/updated/unchanged 缁熻鍚堢悊锛岃鏁颁笉閲嶅锛?2 琛ㄥ潎鍙鍑哄苟甯?搂3.9 manifest銆?- **杈圭晫**锛氱┖鏍囩銆佺┖棰勬祴銆乧reate_dataset銆佸悓浜嬪姟澶氳〃鍐欏叆銆侀噸澶?model_name 鐗堟湰鍧囦繚鎸佽嚜鐒堕敭涓?NULL 璇箟锛汣SV BOM/XLSX 鍙墦寮€銆傛棫 `labels.csv` 蹇呴』琚嫆缁濓紙40001锛夛紝涓嶅緱璇嗗埆涓烘爣绛捐緭鍏ャ€?- **闈炴硶**锛氭湭鐭?schema銆佹棤鐩爣琛ㄣ€侀敊鍒椼€乧hecksum 澶辫触銆佸叕寮忔敞鍏ャ€侀潪娉?table/format銆佹晱鎰熼厤缃鍏ュ潎杩斿洖 40001锛涗簨鍔″け璐ユ棤閮ㄥ垎鍐欏叆銆?- 妯″潡鍦ㄧ┖搴撲粛鑳界嫭绔嬭繍琛岋紱瀵煎叆鍚?commits/trends 绛夊睍绀虹鐐瑰彲璇伙紱瀵煎嚭 checksum銆佸懡鍚嶅拰涓嬭浇閴存潈閫氳繃銆?
## 8. 杈圭晫

storage 鏄彲閫夊睍绀轰笌鎸佷箙鍖栧眰锛屼笉鏄ā鍧楅棿鎬荤嚎銆備笟鍔℃ā鍧楅棿浠呬緷 搂3.x 鏂囦欢 schema 鍏煎锛涙暟鎹簱鏈夋暟鎹笉鏄换浣?run 绔偣鐨勫墠缃紝dataset_id 涔熷彧鏄究鍒╅€夋嫨銆傛ā鍨嬭鐢?model_artifact 娲剧敓锛岄厤缃笌 job 鍗曟簮浠嶇敱瀵瑰簲琛ㄦ壙鎷呫€?