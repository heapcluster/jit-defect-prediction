# 妯″瀷璁粌 API锛坱rain锛?
涓€鍙ヨ瘽锛氱嫭绔嬫帴鏀?`clean_dataset.csv`銆佹ā鍨嬬嚎涓庣畻娉曢厤缃紝鍦ㄨ缁冮樁娈?*鍐呴儴**鐢熸垚妯″瀷鐗瑰緛骞舵寜鐢ㄦ埛閰嶇疆鐨勫垝鍒嗘柟寮忥紙`random` 榛樿 / `time_order`锛夎缁冧竴涓垨澶氫釜妯″瀷锛屼氦浠樺甫鐗瑰緛椤哄簭銆乣feature_schema.json`銆佸厓鏁版嵁涓?checksum 鐨?`.pkl` 鏉冮噸 `model_package.zip` 涓庡甫鐪熸爣绛剧殑娴嬭瘯闆嗐€?
瀹炵幇鐘舵€侊細鐩爣濂戠害锛堟棫瀹炵幇寰呮敼閫狅級銆€鏈熸锛氫竴鏈?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.1銆伮?.2銆伮?.3銆伮?.9锛涚畻娉曡绔偣涓庡叕鍏卞彛寰勮鏈枃鍙?[README.md](README.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗璁粌閰嶇疆鏍￠獙銆佹ā鍨嬬壒寰侀€夋嫨涓庣敓鎴愩€佽缁冧晶鍙樻崲銆佸绠楁硶鎵ц涓庡け璐ラ殧绂汇€佸彲閰嶇疆鍒掑垎銆佹祴璇曢泦浜у嚭銆佹ā鍨嬪伐浠舵墦鍖呭拰鍙€夎祫浜х櫥璁般€?- 绠楁硶鍏冩暟鎹潵鑷?`algorithm` 琛ㄦ垨鐙珛鍐呯疆娉ㄥ唽蹇収锛汬TTP 琛ㄥ崟閫氳繃 `/api/algorithms` 鑾峰彇锛屼笉纭紪鐮佽秴鍙?schema銆?- 涓嶈礋璐ｉ噰闆嗐€佹竻娲椼€佸湪绾块娴嬨€佽В閲婃垨鎬ц兘璇勪及锛汚UC/F1 绛夋寚鏍囦笌澶氭ā鍨嬫瘮杈冨綊鏉垮潡 鈶ワ紝鏈ā鍧楀彧浜у嚭妯″瀷鍖呬笌甯︾湡鏍囩鐨勬祴璇曢泦銆?- 鏂囦欢宸ヤ欢鏄氦浠樹富璺緞锛沗model_artifact` 鐧昏鍜屾淳鐢?`model` 琛屾槸鍙€夊睍绀鸿矾寰勶紝涓嶆槸棰勬祴鍔犺浇鐨勫墠缃€?
## 2. 绔偣濂戠害

### GET /api/algorithms

鏌ヨ鍙傛暟锛歚line=expert|semantic`锛堝彲閫夛級銆乣enabled_only=0|1`锛堥粯璁?0锛夈€傚搷搴?`data.algorithms[]`锛?
| 瀛楁 | 鍚箟 |
|---|---|
| `line` / `algo` / `family` | 妯″瀷绾裤€佺畻娉曟爣璇嗕笌绠楁硶鏃?|
| `enabled` / `description` | 鍚敤鐘舵€佷笌璇存槑 |
| `hyperparams_schema[]` | `{name,type,default,min,max,choices,description}` |
| `input_requirements` | 鍐呴儴鐗瑰緛鐢熸垚瑕佹眰璇存槑锛圞amei 14 缁?/ CodeBERT 768 缁达級 |

鏈煡 line 鎴栭潪娉?enabled_only 杩斿洖 40001銆?
### POST /api/train/run

`multipart/form-data`锛歚files[]` 涓婁紶涓€涓?搂3.2 `clean_dataset` 琛ㄦ牸锛沗config` 涓?JSON part銆?*涓嶆帴鍙?* `feature_file` 绛夊閮ㄧ壒寰佹枃浠讹紝涔熶笉鎺ュ彈 `repo_source` 閰嶇疆銆備富琛?鈮?000 琛屼笖绠楁硶鍧囧睘 `{lr,nb,dt,knn,rf,et}` 鏃跺悓姝ヨ繑鍥炵粓鎬侊紝鍚﹀垯鍒涘缓 `kind=train` 寮傛 job銆?
| config 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `dataset_id` | 鍚?| 宸插鍏ヨ〃鏍肩殑渚垮埄閫夋嫨锛涗笌涓婁紶鏂囦欢浜岄€変竴 |
| `line` | 鏄?| `expert` / `semantic`锛堜粎涓ょ嚎锛?|
| `feature_set` | 鏄?| 涓?line 鍏煎锛歚expert`鈫抈kamei14`锛圞amei 14 缁达級锛沗semantic`鈫抈codebert768`锛堝喕缁撳ご CodeBERT 768 缁达級 |
| `feature_transform` | 鍚?| 璁粌渚у彉鎹細`log_transform` / `standardize` / `categorical_encode` / `feature_select`锛屽彧鍦ㄨ缁冮泦鎷熷悎 |
| `algos[]` | 鏄?| 闈炵┖绠楁硶鏁扮粍锛涢€愰」鏍￠獙涓?`(line, feature_set)` 鐨勭粍鍚?|
| `hyperparams` | 鍚?| `{algo:{param:value}}`锛屾寜 algorithms schema 鏍￠獙 |
| `template_name` | 鍚?| 寮曠敤 `train.templates` 涓ā鏉匡紱鏄惧紡閰嶇疆浼樺厛 |
| `split` | 鍚?| `{mode:"random", ratio:0.7}`锛堥粯璁わ級鎴?`{mode:"time_order", ratio:0.7, time_boundary:"..."}`锛涗袱绉嶆ā寮忓潎鍏佽鐢ㄦ埛閰嶇疆 |
| `seed` | 鍚?| 榛樿 42锛沗random` 妯″紡鎸?seed 鍥哄畾鍒掑垎 |
| `decision_threshold` | 鍚?| 缂虹渷璇?`user_config.decision_threshold`锛涜缁冧笉璁＄畻鎬ц兘鎸囨爣锛岄槇鍊煎垽瀹氬綊 predict/evaluate |
| `register` | 鍚?| 榛樿 `false`锛涗负 true 鏃舵牎楠屾垚鍔熷悗鐧昏 model_artifact 骞舵淳鐢?model 琛?|
| `auto_load` | 鍚?| 榛樿 `false`锛涙槸鍚﹀姞杞藉埌杩愯鏃讹紝涓嶆敼鍙樺綋鍓嶉€夋嫨 |

鍚屾鍝嶅簲 `data`锛歚{job_id,status:"success",outputs[],models[],testset}`锛涘紓姝ヨ繑鍥?`{job_id,status:"queued"}`銆俙models[]` 姣忛」涓?`{algo,model_name,version_key,feature_version,status,error}`锛涘崟绠楁硶澶辫触涓嶆姽鎺夊叾浠栫畻娉曡緭鍑猴紝鏈ā鍧椾笉杩斿洖 metrics銆俙testset` 涓哄垏鍒嗗嚭鐨勬祴璇曢泦鏂囦欢鍚嶏紙搂3.3 `train_testset`锛夛紝渚涙澘鍧?鈶?浣滀负棰勬祴杈撳叆銆?
### GET /api/train/outputs/{job_id}/{name}

涓嬭浇鎸囧畾宸ヤ欢鎴?manifest锛屾枃浠跺悕蹇呴』鍦?job 杈撳嚭鐧昏涓€?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 琛ㄦ牸/瓒呭弬/绠楁硶缁勫悎闈炴硶銆佸垝鍒?mode 鎴栨瘮渚嬮潪娉曘€乣time_order` 杈圭晫鏂█澶辫触銆佺壒寰佷笉鍏煎銆佸悓 kind 鍐茬獊銆侀潪娉曚笅杞藉悕 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key` |
| 40400 | 404 | 鍙€?dataset銆佹ā鏉裤€乯ob 鎴栬緭鍑轰笉瀛樺湪 |
| 50000 | 500 | 鏈鏈熸湇鍔￠敊璇紱鍗曠畻娉曞紓甯稿悓鏃惰鍏ュ叾瀛愰」鐘舵€?|

## 3. 杈撳叆濂戠害

涓婁紶琛ㄦ牸鍙噰鐢?搂3.2 `clean_dataset`锛?
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
| label_method | string | 鍚?| 鏍囩鏂规硶 |
| label_source | string | 鏄?| `git_szz` / `public_dataset` |
| labeled_at | datetime | 鍚?| 鎵撴爣鏃堕棿 |
| fix_commit_hash | string(40) | 鍚?| SZZ 鍥炴函淇鎻愪氦 |
| source_type | string | 鏄?| `git_repo` / `public_dataset` |

`clean_dataset` 涓嶅惈妯″瀷鐗瑰緛闆嗐€佽缁冩祴璇曞垝鍒嗗拰璁粌渚у彉鎹㈢粨鏋溿€傝缁冮樁娈垫寜 `feature_set` **鍐呴儴鐢熸垚**妯″瀷鐗瑰緛锛歚kamei14` 鐢辫缁冩ā鍧楁牴鎹暟鎹泦缁戝畾鏉ユ簮/鎻愪氦鍙樻洿璁＄畻 Kamei 14 缁达紝`codebert768` 鐢辫缁冩ā鍧椾娇鐢ㄦ暟鎹泦缁戝畾鐨勪粨搴撳揩鐓?鎻愪氦鏂囨湰缁忓喕缁撳ご CodeBERT 缂栫爜涓?768 缁淬€俙repo_source` / `feature_file` 涓嶆槸 API 瀛楁鎴栦笂浼犳枃浠讹紱鍐呴儴鏉ユ簮缂哄け鎴栫紪鐮佸け璐ユ椂鍓嶇疆杩斿洖 40001锛屼笉浼€犲悜閲忋€?
涓婁紶鎵ц澶у皬銆佹墿灞曞悕榄旀暟銆佸垪 schema銆佺被鍨嬨€佸叕寮忔敞鍏ヤ笌绌烘爣绛炬鏌ャ€傝缁冧粎浣跨敤宸叉墦鏍囪璁＄畻鐩戠潱鐩爣锛屾湭鎵撴爣 `is_bug_inducing` 涓嶅緱褰撲綔 0銆傚垝鍒嗘柟寮忕敤鎴峰彲閰嶇疆锛歚split.mode=random`锛堥粯璁わ紝鎸?`seed` 鍥哄畾闅忔満鍒掑垎锛夋垨 `split.mode=time_order`锛堟椂闂村簭锛屼繚鐣欍€屾祴璇曢泦鏈€鏃╂椂闂村繀椤绘櫄浜庤缁冮泦鏈€鏅氭椂闂淬€嶆柇瑷€锛夛紱榛樿姣斾緥 0.7銆傞潪娉?mode銆佹瘮渚嬭秺鐣屾垨 `time_order` 鏂█澶辫触杩斿洖 40001锛涢殢鏈哄垝鍒嗕笉鍐嶈涓洪潪娉曘€俙feature_transform` 鍙湪璁粌闆嗘嫙鍚?scaler/encoder锛屽苟闅忔ā鍨嬪寘鍥哄寲銆?
## 4. 杈撳嚭濂戠害

姣忎釜鎴愬姛绠楁硶浜や粯涓€涓嫭绔嬫ā鍨嬪寘锛涙枃浠跺悕 `train_<algo>_model_package_<job_id>.zip`锛屽悓鍚?manifest 涓?`train_<algo>_model_package_<job_id>.manifest.json`銆傚彟浜や粯鍒囧垎鍑虹殑娴嬭瘯闆?`train_testset_<job_id>.csv/xlsx`锛屽悓鍚?manifest銆?
[../file-contracts.md](../file-contracts.md) 搂3.3 閫愬瓧瑙勫畾锛?
> zip 鍐呭惈锛氭潈閲嶆枃浠跺潎涓?`.pkl`锛坋xpert=`kamei14` 14 缁淬€乻emantic=`codebert768` 768 缁达紝涓ょ嚎鍧囩敤浼犵粺鍒嗙被鍣級銆乣feature_order.txt`銆乣feature_schema.json`锛堝瓧娈靛悕/绫诲瀷/鏉ユ簮/鐗堟湰/璁粌渚у彉鎹級銆乣model_meta.json`锛坢odel_name/line/algo/feature_set/version_key/feature_version/trained_at/瓒呭弬蹇収/鍒掑垎 mode/绉嶅瓙锛夈€乣checksum.sha256`銆俻redict/explain MUST 鏍￠獙 checksum 涓庣壒寰佸垪瀹藉悗鍐嶅姞杞姐€?>
> `train_testset` schema 涓?搂3.2 `clean_dataset` 閫愬垪涓€鑷达紝姣忚 MUST 甯﹂潪绌?`is_bug_inducing` 鐪熸爣绛撅紝鏃犳爣绛捐涓嶈繘鍏ユ祴璇曢泦锛汳UST NOT 鍚?`is_test` 鎴栨ā鍨嬬壒寰佸垪銆備緵鏉垮潡 鈶?浣滀负璇勪及棰勬祴杈撳叆銆?
- 涓嶅绠楁硶娣疯涓轰竴涓棤娉曞尯鍒嗙増鏈殑鍖咃紱澶辫触绠楁硶涓嶄骇 zip锛屼篃涓嶈鐩栧凡鏈夊彲鐢ㄥ伐浠躲€?- 鏈ā鍧椾笉浜у嚭 AUC/F1 绛夋寚鏍囥€佹贩娣嗙煩闃点€佹瘮杈?JSON 鎴栧姣斿浘锛涙€ц兘璇勪及褰掓澘鍧?鈶ャ€?- manifest 涓ユ牸閲囩敤 搂3.9锛岃褰曡缁冭〃鏍?checksum銆佺畻娉曚笌瓒呭弬銆佸垝鍒?mode 涓庢瘮渚?鏃堕棿杈圭晫銆佺瀛愩€佸寘涓庢祴璇曢泦 checksum銆佷唬鐮佺増鏈€?- `model_meta.json` 鐨勫瓧娈靛悕绉颁笌椤哄簭璇箟浠?搂3.3 涓哄噯锛屼笉鍙﹂€犳ā鍨嬪厓鏁版嵁鍒椼€?- `register=true` 鏃剁櫥璁板寘璺緞銆乧hecksum銆佸ぇ灏忋€佽缁?job銆佺増鏈拰鐗瑰緛鐗堟湰锛屽苟鐢卞伐浠舵淳鐢?model 琛岋紱鐧昏澶辫触涓嶅奖鍝嶅凡浜や粯鏂囦欢锛屼絾瀛愰」鐘舵€佸繀椤昏鏄庛€俙auto_load=true` 浠呭鏈换鍔¤嚜浜х殑 expert 鏉冮噸鍋氱儹鍔犺浇锛堟牎楠岀壒寰佸垪瀹藉悗鏀惧叆杩愯鏃讹紝涓嶉噸鍚€佷笉鏀瑰彉褰撳墠閫夋嫨锛夛紱閫氱敤宸茬櫥璁板伐浠剁殑鍔犺浇绔偣灞?predict/妯″瀷绠＄悊锛圵6锛夈€傚悓鍚嶆ā鍨嬪凡鍔犺浇涓旀潈閲?checksum 涓嶅悓鏃讹紝鐧昏鎸?W2 瀹夊叏瑙勫垯鎷掔粷骞惰鍏ュ瓙椤癸紝涓嶈鐩栬繍琛屾椂銆?
## 5. 鍙厤缃」

- `train.templates`锛歚line`銆乣feature_set`銆佺畻娉曢泦鍚堛€侀€愮畻娉曡秴鍙傘€佽缁冧晶鍙樻崲銆佸垝鍒?mode/姣斾緥/杈圭晫涓庣瀛愮殑鍛藉悕妯℃澘锛岃惤 `user_config` 骞堕噸鍚仮澶嶃€?- 鍗曟杩愯锛氭ā鏉胯鐩栥€佹ā鍨嬬嚎銆佺壒寰侀泦銆佽缁冧晶鍙樻崲銆佺畻娉曘€佽秴鍙傘€佸垝鍒嗐€佺瀛愩€佺櫥璁颁笌鍔犺浇寮€鍏炽€?- 绠楁硶娓呭崟鍜岃秴鍙傜害鏉熺敱 `/api/algorithms` 鏆撮湶锛沗.env` 鍙彁渚涘嚭鍘傞粯璁わ紝涓嶈兘瑕嗙洊鐢ㄦ埛妯℃澘銆?- 榛樿鍒掑垎 `mode=random`銆乣ratio=0.7`銆佺瀛?42锛涙€ц兘鎸囨爣涓庨槇鍊奸厤缃綊鏉垮潡 鈶ワ紝涓嶅湪璁粌閰嶇疆鍐呫€?
## 6. 鐘舵€佹寔涔呭寲

- 姣忔杩愯鏈?`job_id`锛屽悓姝ュ啓缁堟€侊紝寮傛 kind=`train` 鍐欎簲鎬侊紱job 淇濆瓨閫愮畻娉曞瓙椤广€佽繘搴︺€佸叆鍙傚揩鐓у拰鑴辨晱閿欒銆?- 鍚?kind 閫氳繃琛ㄦ潯浠舵洿鏂颁簰鏂ワ紱閲嶅惎閬楃暀 running 缃?failed锛屽彲 retry/cancel锛涘凡鎴愬姛瀛愰」宸ヤ欢淇濈暀涓斿彲澶嶉獙銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紱妯″瀷鍖呬笌 manifest 鐨?checksum 鍦ㄥ啓鐩樺悗澶嶇畻銆?- `model_artifact` 鍙壙鎷呭彲閫夎祫浜х櫥璁帮紝涓嶄綔涓轰笅娓歌繍琛屽墠缃紱杩愯鏃朵笉渚濊禆璁粌杩涚▼鍐呭璞°€?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/train/`锛屼笉璋冪敤 collect銆乧lean銆乸redict 鎴?evaluation 鏈嶅姟銆?
- **姝ｅ父**锛氫袱涓畻娉曞垎鍒缃秴鍙傚悗寰楀埌涓や釜 搂3.3 鍖咃紱鏉冮噸銆乫eature_order銆乵odel_meta銆乧hecksum 瀹屾暣锛屽姞杞芥牎楠岄€氳繃锛宮anifest 鍙鐜般€?- **杈圭晫**锛氬崟绠楁硶銆佷竴涓畻娉曞け璐ヤ竴涓垚鍔熴€佸皬鏍锋湰涓ょ鍒掑垎妯″紡銆佹湭鎵撴爣琛屻€丆PU/GPU 鍙敤鎬у樊寮傚潎淇濇寔澶辫触闅旂涓斾笉瑕嗙洊鏃у伐浠躲€?- **闈炴硶**锛氱己鍒椼€佺┖绠楁硶銆侀潪娉曠粍鍚堛€佽秴鍙傝秺鐣屻€佸垝鍒?mode/姣斾緥闈炴硶銆乣time_order` 鏂█澶辫触銆佸叕寮忔敞鍏ャ€佷吉閫犲寘鎴?checksum 涓嶇杩斿洖 40001锛屼笉浜у崐鎴愬搧銆?- 鍒囧垎浜у嚭甯︾湡鏍囩鐨?`train_testset`锛堟瘡琛?`is_bug_inducing` 闈炵┖锛夛紝schema 涓?搂3.2 涓€鑷达紝鍙 predict 鐩存帴浣滀负杈撳叆锛汣LI/API 鍚?fixture 鐨勫寘鍏冩暟鎹笌娴嬭瘯闆嗕竴鑷淬€?- 鏈ā鍧椾笉杩斿洖鎴栦骇鍑烘€ц兘鎸囨爣锛涘妯″瀷姣旇緝涓庢寚鏍囨暟鍊煎湪鏉垮潡 鈶?楠屾敹銆?
## 8. 杈圭晫

璁粌瑕佹眰杈撳叆 `clean_dataset` 婊¤冻 搂3.2锛屾ā鍨嬬壒寰佺敱璁粌闃舵鍐呴儴鎸?`feature_set` 鐢熸垚锛岃緭鍑烘弧瓒?搂3.3锛堟ā鍨嬪寘 + 娴嬭瘯闆嗭級锛沗dataset_id`銆佽祫浜ц〃鍜屾ā鍨嬬鐞嗘湇鍔″潎涓哄彲閫変究鍒╂垨灞曠ず鑳藉姏銆俻redict 閫氳繃妯″瀷鍖呬笌 搂3.3 娴嬭瘯闆嗘秷璐圭粨鏋滐紝evaluate 閫氳繃 predict 鐨?搂3.4 鏂囦欢璇勪及鎬ц兘锛涜缁冧笉璋冪敤瀹冧滑锛屼篃涓嶈绠楁寚鏍囥€?