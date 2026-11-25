# API 鐩爣濂戠害绱㈠紩

涓€鍙ヨ瘽锛氭湰鐩綍浠?17 绡囨枃浠跺畾涔夊叓涓嫭绔嬪伐鍏风殑 API銆佸叕鍏遍壌鏉冧笌閿欒鍖呯粶銆佺粺涓€杩愯/涓嬭浇銆佸瓨鍌ㄥ鍏ュ鍑哄強灞曠ず绠＄悊绔偣锛屼换浣曞伐鍏烽兘鍙洿鎺ュ嚟杈撳叆鏂囦欢鐙珛楠屾敹銆?
瀹炵幇鐘舵€侊細閮ㄥ垎銆€鏈熸锛氫竴鏈?
浜ゆ崲鏂囦欢鍗曚竴鏉冨▉涓?[../file-contracts.md](../file-contracts.md) 搂3.1鈥撀?.9锛涙湰鏂囧彧瑙勫畾鍏叡 HTTP 鍙ｅ緞锛屽悇绡囨槸鍏蜂綋绔偣濂戠害銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗瀵艰埅銆佸叕鍏遍壌鏉冦€佸搷搴斿寘缁溿€佷笟鍔＄爜銆佹椂闂存牸寮忋€佺粺涓€ run/job/杈撳嚭鐩綍銆佸畨鍏ㄤ笌閰嶇疆鍘熷垯銆?- 鍏釜宸ュ叿鍒嗗埆涓?storage銆乧ollect銆乧lean銆乼rain銆乸redict銆乪valuate銆乪xplain銆乴ocalization锛涘湪绾跨粍鍚堟紨绀哄彧鏄彲閫夎皟鐢ㄦ柟寮忋€?- 灞曠ず璇荤鐐瑰彧璇诲凡瀵煎叆鏁版嵁锛屾ā鍨?閰嶇疆/job 绠＄悊绔偣鍙壙鎷呭悇鑷鐞嗚亴璐ｏ紝鍧囦笉浠ｆ浛鏂囦欢杩愯銆?- 鏈枃涓嶉噸澶嶅畾涔変氦鎹㈠垪锛屼笉澧炲姞绗竷绉?job kind锛屼笉鎶婃暟鎹簱銆侀〉闈㈡垨鍏朵粬妯″潡鍦ㄧ嚎鐘舵€佷綔涓轰笟鍔¤繍琛屽墠缃€?
## 2. 绔偣濂戠害锛?7 缁勭储寮?
| # | 鏂囨。 | 鍒嗙粍 | 鐩爣绔偣 | 瀹炵幇鐘舵€?|
|---|---|---|---|---|
| 1 | [README.md](README.md) | 鍏叡濂戠害 | 閴存潈銆佸寘缁溿€侀敊璇爜銆乺un/job/杈撳嚭鍏叡瑙勫垯 | 閮ㄥ垎 |
| 2 | [storage.md](storage.md) | 宸ュ叿 1锛氬瓨鍌?| `POST /api/storage/import`锛沗GET /api/storage/export?table=&format=`锛沗GET /api/storage/outputs/{job_id}/{name}` | 閮ㄥ垎 |
| 3 | [collect.md](collect.md) | 宸ュ叿 2锛氭敹闆?| `POST /api/collect/run`锛圙it 浠撳簱 / 鍏紑鏁版嵁闆嗭級锛沗GET /api/collect/preview/{job_id}`锛沗GET /api/collect/outputs/{job_id}/{name}`锛沗POST /api/collect/resave/{job_id}` | 鐩爣濂戠害锛堟棫瀹炵幇寰呮敼閫狅級 |
| 4 | [clean.md](clean.md) | 宸ュ叿 3锛氭竻娲?| `POST /api/clean/run`锛沗GET /api/clean/operations`锛沗GET /api/clean/preview/{job_id}`锛沗GET /api/clean/outputs/{job_id}/{name}` | 鐩爣濂戠害锛堟棫瀹炵幇寰呮敼閫狅級 |
| 5 | [train.md](train.md) | 宸ュ叿 4锛氳缁?| `POST /api/train/run`锛沗GET /api/algorithms`锛沗GET /api/train/outputs/{job_id}/{name}`锛堟ā鍨嬪寘涓?train_testset锛?| 鐩爣濂戠害锛堟棫瀹炵幇寰呮敼閫狅級 |
| 6 | [predict.md](predict.md) | 宸ュ叿 5锛氶娴?| `POST /api/predict/run`锛沗POST /api/predict`锛沗GET /api/predict/outputs/{job_id}/{name}` | 宸插疄鐜?|
| 7 | [models.md](models.md) | 妯″瀷绠＄悊 | `GET /api/models`锛沗GET /api/models/status`锛沗POST /api/models/{name}/load`銆乣unload`銆乣reload`锛沗PUT /api/models/default` | 宸插疄鐜?|
| 8 | [evaluate.md](evaluate.md) | 宸ュ叿 6锛氳瘎浼?| `POST /api/evaluate/run`锛沗GET /api/evaluate/metrics`锛沗GET /api/evaluate/outputs/{job_id}/{name}` | 宸插疄鐜?|
| 9 | [figures.md](figures.md) | 鍥句欢璇诲彇 | `GET /api/figures`锛涢壌鏉?`/static/**` 鎴栧彈鎺ц緭鍑?URL | 閮ㄥ垎 |
| 10 | [explain.md](explain.md) | 宸ュ叿 7锛氳В閲?| `POST /api/explain/run`锛沗POST /api/explain`锛沗GET /api/explain/techniques`锛沗GET /api/explain/outputs/{job_id}/{name}` | 宸插疄鐜?|
| 11 | [source.md](source.md) | 宸ュ叿 8锛氬畾浣嶄笌婧愮爜 | `POST /api/localize/run`锛沗GET /api/localize/outputs/{job_id}/{name}`锛沗GET /api/source/tree`銆乣GET /api/source/file` | 宸插疄鐜帮紙鏃犲彲闈犱慨澶嶈ˉ涓佹椂鍙氦浠樺缓璁級 |
| 12 | [commits.md](commits.md) | 鎻愪氦璇诲彇 | `GET /api/commits`锛沗GET /api/commits/{commit_hash}` | 閮ㄥ垎 |
| 13 | [trends.md](trends.md) | 瓒嬪娍璇诲彇 | `GET /api/trends` | 閮ㄥ垎 |
| 14 | [datasets.md](datasets.md) | 鏁版嵁闆嗚鍙栦笌瀵煎嚭 | `GET /api/datasets`銆乣/{id}`銆乣/{id}/commits`銆乣/{id}/export`锛沗GET /api/datasets/outputs/{job_id}/{name}` | 鏈疄鐜?|
| 15 | [config.md](config.md) | 閰嶇疆绠＄悊 | `GET/PUT /api/config`锛沗PUT/DELETE /api/config/{key}` | 閮ㄥ垎 |
| 16 | [jobs.md](jobs.md) | 浠诲姟绠＄悊 | `GET /api/jobs`锛沗GET /api/jobs/{id}`锛沗POST /api/jobs/{id}/retry`銆乣cancel` | 閮ㄥ垎 |
| 17 | [health.md](health.md) | 鍋ュ悍鎺㈤拡 | `GET /api/health`銆乣/api/health/live`銆乣/api/health/ready` | 閮ㄥ垎 |

### 鍏叡璇锋眰涓庡搷搴?
- **閴存潈**锛氭墍鏈?`/api/**`銆乣/static/**`銆佸浘鐗囦笌杈撳嚭涓嬭浇閮借姹?`X-API-Key`锛涙湇鍔＄鏈厤缃护鐗屾椂 fail closed銆傚墠绔彇鍥句娇鐢ㄥ甫閴存潈 fetch 杞?ObjectURL銆?- **JSON 鍖呯粶**锛氭垚鍔?`{code:0,message:"ok",data:{...}}`锛涘け璐?`{code,message,data:null}`銆傛枃浠舵祦涓嶈蛋 JSON 鍖呯粶锛屼絾娴佸紑濮嬪墠鐨勬牎楠岄敊璇粛璧板寘缁溿€?- **涓氬姟鐮?*锛氫粎 `40001`锛圚TTP 400锛夈€乣40100`锛?01锛夈€乣40400`锛?04锛夈€乣50000`锛?00锛夛紱鎴愬姛 code=0銆?0000 message 鍥哄畾 `internal error`锛屼笉鍥炴樉鍫嗘爤銆丼QL銆佽繛鎺ヤ覆鎴栫粷瀵硅矾寰勩€?- **鏃堕棿**锛氬搷搴?UTC ISO 8601 `Z`锛涙椂闂磋寖鍥翠袱绔棴鍖洪棿锛宻tart 绾棩鏈熶负褰撳ぉ璧风偣锛宔nd 绾棩鏈熸墿灞曡嚦褰撳ぉ缁堢偣銆?- **妯″瀷閫夋嫨**锛氭墍鏈夐渶瑕佹ā鍨嬬殑 run / 鏌ヨ鍏ュ彛蹇呴』鏄惧紡浼?`model_name` 鎴栦笂浼?`model_package.zip`锛屾湭鎸囧畾杩斿洖 40001锛涗笉璁鹃粯璁ゆā鍨嬶紝涔熶笉鍋氱増鏈簭闅愬紡鍥為€€銆傛ā鍨嬪寘鍔犺浇鍓嶅繀椤绘牎楠?checksum 涓庣壒寰佸垪瀹姐€?
### 缁熶竴 run 涓庝笅杞?
涓冧釜璁＄畻鍨?run 鍧囦负 `POST /api/{collect,clean,train,predict,evaluate,explain,localize}/run`锛?
- 璇锋眰 `multipart/form-data`锛屾枃浠跺瓧娈?`files[]`锛岄厤缃瓧娈?`config`锛圝SON part锛夛紱collect 鐨?`config.source_type` 蹇呴』鏄?`git_repo` 鎴?`public_dataset`锛屼笉浼犱粨搴撶幆澧冨彉閲忋€?- 琛ㄦ牸鎺ュ彈 CSV/XLSX锛涗笂浼犳牎楠屽ぇ灏忋€佹墿灞曞悕涓庨瓟鏁般€佸垪 schema銆丆SV 鍏紡娉ㄥ叆锛孼IP 杩樻牎楠岃矾寰勭┛瓒婁笌瑙ｅ帇澶у皬銆傝矾寰勯檺瀹氬厑璁告牴鐩綍锛屾枃浠跺悕涓嶅緱鎷兼帴 shell銆?- 灏忔枃浠跺悓姝ユ墽琛屽苟杩斿洖 `{job_id,status:"success",outputs[],...}`锛涘ぇ鏂囦欢杩斿洖 `{job_id,status:"queued"}`銆傞櫎 localize 澶栵紝鍚屾涔熻惤 job 缁堟€侊紝寮傛钀戒簲鎬併€?- 杈撳嚭缁熶竴涓嬭浇 `GET /api/{module}/outputs/{job_id}/{name}`锛沶ame 鍙兘鏄?manifest 鐧昏鐨勫熀纭€鏂囦欢鍚嶏紝绂佹璺緞绌胯秺銆?- localize 鍚屾涓轰富銆佷笉鏂板 kind锛岃秴澶ц緭鍏ヨ繑鍥?40001 骞惰姹傚垎鎵癸紱鍏?job_id 浠呬綔杈撳嚭鎵规鏍囪瘑銆?
### 浜х墿搴撻€夋嫨涓庝笂浼犵瓑浠?
浜х墿搴撶储寮曞凡浜や粯鐨勬枃浠讹紝涓嶇瓑鍚屼簬 `dataset` 灞曠ず鍙拌处锛屼篃涓嶈姹傛枃浠跺厛缁?storage 瀵煎叆銆俢lean/train/predict/evaluate/explain/localize 鐨勬枃浠堕€夋嫨閬靛惊鍚屼竴娴佺▼锛?
1. 閫氳繃 `GET /api/jobs?kind=<kind>` 鍒嗛〉鏌ヨ鏉ユ簮浠诲姟锛屼粠 `output_ref_json` 璇诲彇宸茬櫥璁颁骇鐗╋紱浠呮樉绀虹鍚堟湰妯″潡杈撳叆绫诲瀷涓斿凡瀹屾垚浜や粯鐨勬枃浠躲€傞儴鍒嗗け璐ヤ换鍔′腑宸叉垚鍔熶氦浠樼殑瀛愰」浠嶅彲閫夋嫨锛屼笉鑳藉彧鍑换鍔℃€荤姸鎬佸垽瀹氭枃浠跺彲鐢ㄣ€?2. 閫夋嫨缁撴灉鍦ㄩ〉闈㈠唴淇濆瓨 `{module,job_id,name,sha256,size_bytes}`锛沗job_id` 浣跨敤杈撳嚭寮曠敤涓殑鎵规鏍囪瘑锛宍name` 浣跨敤宸茬櫥璁板熀纭€鏂囦欢鍚嶏紝涓嶆嫾鎺ユ湇鍔″櫒璺緞鎴栫寽娴嬫枃浠跺悕銆?3. 缁?`GET /api/{module}/outputs/{job_id}/{name}` 涓嬭浇鎵€閫夋枃浠跺強鍏跺凡鐧昏 manifest锛屽叏閮ㄦ惡甯?`X-API-Key`銆俶anifest 鐨?`outputs[]` 蹇呴』鍖呭惈璇ユ枃浠跺悕鍙婄浉鍚?SHA256锛涙枃浠朵笉鍙笅杞芥垨 checksum 涓嶇鏃剁鐢ㄨ繍琛屽苟鎻愮ず閲嶆柊閫夋嫨銆?4. 鎶婁笅杞藉唴瀹规瀯閫犳垚 File/Blob锛屼互 `files[]` 鎻愪氦缁欑洰鏍?`run`锛岄厤缃粛鏀?`config` JSON part锛涘凡鏈変即闅?manifest 涓€骞朵綔涓鸿緟鍔╂枃浠舵彁浜ゃ€俽un 涓嶆柊澧炴枃浠跺紩鐢ㄥ弬鏁帮紝涓嶆帴鍙楁湇鍔″櫒缁濆璺緞锛屼篃涓嶉€氳繃 `dataset_id` 璇诲彇杩欎簺浜х墿銆?5. 鏈嶅姟绔噸鏂版牎楠屾枃浠躲€乵anifest 涓?checksum锛沵anifest 杈呭姪鏂囦欢涓嶈鍏ユā鍧楄瀹氱殑涓昏〃鎴栨ā鍨嬪寘鏁伴噺銆傜洿鎺ヤ笂浼犳病鏈夋潵婧?manifest 鐨勫閮ㄦ枃浠朵粛鎸夋ā鍧楄緭鍏ュ绾︽牎楠岋紱閫夋嫨浜х墿搴撴枃浠朵笌鐩存帴涓婁紶鐩稿悓鏂囦欢搴斿緱鍒扮瓑浠蜂笟鍔¤緭鍑恒€?
| 寰呴€夎緭鍏?| 鏉ユ簮 job kind | 涓嬭浇绔偣鐨?module |
|---|---|---|
| collected_commits | `collect` | `collect` |
| clean_dataset | `clean` | `clean` |
| model_package | `train` | `train` |
| predictions | `predict_batch` | `predict` |
| explanations | `explain` | `explain` |

`kind=predict` 涓嶅悎娉曪紝棰勬祴浠诲姟浣跨敤 `predict_batch`銆傛病鏈夊搴斿巻鍙蹭骇鐗╃殑鏂囦欢鍙洿鎺ヤ笂浼狅紱鐪熸爣绛炬潵鑷祴璇曢泦骞剁粡 predict 閫忎紶锛屼笉鍐嶆湁鐙珛 labels 涓婁紶銆俙dataset_id` 鍜屽凡鐧昏 `model_name` 淇濈暀涓虹嫭绔嬩究鍒╅€夐」锛氬墠鑰呴€夋嫨宸插鍏ユ暟鎹紝鍚庤€呴€夋嫨鐧昏妯″瀷锛涘畠浠笉鏄骇鐗╂枃浠跺紩鐢紝璧?`files[]` 鐨勪骇鐗╅€夋嫨璺緞涓嶅悓鏃舵彁浜?`dataset_id`銆?
## 3. 杈撳叆濂戠害

- 妯″潡涓昏緭鍏ユ槸鏂囦欢鍜屾樉寮?config锛沗dataset_id` 鍙敤浜庨€夋嫨宸插鍏ユ枃浠剁殑渚垮埄杈撳叆锛屾樉寮忎笂浼犱紭鍏堛€?- 鏂囦欢 schema 蹇呴』閫愮瘒寮曠敤 file-contracts 搂3.1鈥撀?.8锛屼笉鍦?API 鏂囨。鍙﹂€犲垪鍚嶃€佸埆鍚嶆垨绉佹湁瀹借〃銆?- 鎵€鏈夎〃鏍艰В鏋愬悗褰掍竴璁板綍缁撴瀯锛涚己鍒椼€侀敊绫诲瀷銆侀潪娉?hash/鏃堕棿/姒傜巼銆佸叕寮忔敞鍏ャ€佽秴闄愭垨浼€犳牸寮忚繑鍥?40001锛屼笉浜у崐鎴愬搧銆?- `is_bug_inducing` 鏈墦鏍囦繚鎸佺┖鍊硷紱鏉垮潡 2 涓嶄骇鍑?Kamei 14 缁村拰 `is_test`銆係ZZ 璇嶉杈圭晫 `\b(fix|bug|patch)` 涓?`szz_v1/szz_lite` 浠呯害鏉?collect 鐨?Git 浠撳簱妯″紡锛涘叕寮€鏁版嵁闆嗕笉鎵ц SZZ銆侹amei 14 缁翠笌 70/30 鍒囧垎鐢卞悗缁澘鍧楅噸鏂板畾涔夈€?
## 4. 杈撳嚭濂戠害

- 鏂囦欢鍛藉悕缁熶竴 `<module>_<artifact>_<job_id>.<ext>`锛涗富浜х墿鍚屽悕 manifest 涓?`<module>_<artifact>_<job_id>.manifest.json`锛屾墍鏈夎緭鍑虹櫥璁板悕绉般€佸ぇ灏忓拰 checksum銆?- 琛ㄦ牸榛樿 CSV锛圲TF-8 BOM锛夛紝鍙厤 `format=xlsx`锛沊LSX 鍗?sheet锛宮anifest 涓嶈繘鍏?sheet銆傜┖鏍囩涓庣己棰勬祴淇濇寔绌哄€笺€?- manifest 蹇呬即骞朵弗鏍奸噰鐢?[../file-contracts.md](../file-contracts.md) 搂3.9锛?
```json
{
  "schema_version": "1.0",
  "module": "train",
  "job_id": "j-8f21",
  "inputs": [{"name": "clean_dataset_j-a1b2.csv", "sha256": "鈥?, "rows": 25183}],
  "config": {"algos": ["rf", "xgb"], "seed": 42, "split": {"mode": "random", "ratio": 0.7}},
  "outputs": [{"name": "model_package.zip", "sha256": "鈥?}],
  "code_version": "3e72854",
  "created_at": "2026-11-21T12:00:00Z"
}
```

- 鍙鏌ヨ鍜岀鐞嗙鐐硅嫢涓嶇敓鎴愭枃浠讹紝鏄庣‘涓嶄骇 manifest锛沞xport/run 浜х敓鐨勬枃浠朵笉寰楃己灏?manifest銆?
## 5. 鍙厤缃」

- 鍏ㄥ眬鍗曟簮 user_config锛歚decision_threshold / risk_high_threshold / risk_mid_threshold / default_dataset / default_xai / metrics_selected / primary_metric / effort_enabled / page_prefs`锛涗笉璁?`default_model`锛屾ā鍨嬫瘡娆℃樉寮忛€夋嫨銆?- 妯″潡鍛藉悕绌洪棿锛歚collect.allow_roots`銆乣collect.protocol_whitelist`銆乣clean.chain_templates`銆乣train.templates`銆乣predict.batch_size/cache_ttl/retry_max`銆乣explain.cache_ttl/compare_enabled`銆乣localization.weights/top_n/file_size_max/suggestion_sources`銆?- `.env` 浠呮彁渚涘嚭鍘傞粯璁ゅ拰閮ㄧ讲鏁忔劅椤癸紱瀵嗛挜涓嶅叆搴撱€傜敤鎴烽厤缃啓鍏ョ珛鍗崇敓鏁堬紝杩涚▼鎴栧鍣ㄩ噸鍚悗鎭㈠銆?- 12 琛ㄤ负 `commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit`锛岃亴璐ｆ槸灞曠ず瀵煎叆銆侀厤缃€佷换鍔＄姸鎬佷笌璧勪骇鐧昏銆?
## 6. 鐘舵€佹寔涔呭寲

- job kind 浠?`collect / clean / train / predict_batch / evaluate / explain`锛涚姸鎬佷粎 `queued / running / success / failed / cancelled`銆?- 鍚?kind 浜掓枼閫氳繃 job 琛ㄦ潯浠舵洿鏂帮紱閲嶅惎閬楃暀 running 缃?failed锛屼繚鐣欒繘搴︿笌鑴辨晱鏃ュ織锛屽彲 retry/cancel銆?- 鎵€鏈?run/export 鏂囦欢钀?`temp/outputs/<job_id>/`锛岃鐩綍蹇呴』 gitignore锛沵anifest 涓庢枃浠?checksum 鏄笅杞藉拰澶嶇幇渚濇嵁銆?- 妯″瀷浜や粯涓?搂3.3 model_package.zip锛沵odel_artifact 鏄彲閫夌櫥璁板睍绀鸿矾寰勶紝model 琛岀敱宸ヤ欢娲剧敓锛屾枃浠跺姞杞戒笉瑕佹眰鍏堝叆搴撱€?
## 7. 楠屾敹

鍚勭瘒 fixtures 浣嶄簬 `tests/fixtures/files/<module>/`锛屽潎鍚甯搞€佽竟鐣屻€侀潪娉曚笁绫伙紝骞跺悓鏃堕獙璇?CLI/API 绛変环锛堟ā鍧楁彁渚?CLI 鏃讹級銆?
- **姝ｅ父**锛氬彧涓婁紶璇ユā鍧楄緭鍏ュ嵆寰楀埌鏉冨▉ schema 杈撳嚭銆乵anifest 鍜屽彲閴存潈涓嬭浇锛屼笉瑕佹眰鍏朵粬宸ュ叿鎴栨暟鎹簱鍏堟湁鏁版嵁銆?- **杈圭晫**锛氱┖鎬併€佺┖鏍囩銆佺増鏈?闃堝€?缂撳瓨鍙樺寲銆佷换鍔￠噸鍚€佺己鍥俱€侀儴鍒嗗け璐ュ潎鏈夋槑纭涔夛紝涓嶅～閫?0 鎴栭潤榛樼┖缁撴灉銆?- **闈炴硶**锛歴chema銆侀瓟鏁般€乧hecksum銆佽矾寰勩€侀厤缃拰閴存潈閿欒鍙娇鐢ㄥ叕鍏变笟鍔＄爜锛屼笖涓嶄骇鍗婃垚鍝併€?- 璺ㄦā鍧楁祴璇曞彧楠岃瘉鏂囦欢 schema 鍏煎锛涜瘎浼伴粯璁?0.5 涓庡巻鍙?`model_metrics.csv` 瀵瑰簲鍊奸€愬€间竴鑷达紙瀹瑰樊 1e-6锛夛紝effort-aware/effort-unaware 涓ょ被鍥惧潎楠屾敹銆?
## 8. 杈圭晫

妯″潡闂翠緷璧栦粎涓轰氦鎹㈡枃浠?schema 涓庣増鏈吋瀹癸紝鑰岄潪涓婃父鏈嶅姟鎴栨暟鎹簱鍓嶇疆銆俻redict 涓嶈皟鐢?explain/localize锛岃鎯呭睍绀哄彲骞惰缂栨帓锛汼ZZ 鍒ゆ嵁鍗曟簮鍦?collect锛屾寚鏍囧叕寮忓崟婧愬湪 `data_model/evaluation/metrics.py`銆俿torage銆乧ommits銆乼rends銆乫igures銆乨atasets 鎻愪緵鍙€夊睍绀洪潰锛屼笉鑳藉弽鍚戞垚涓虹嫭绔嬭繍琛岀殑蹇呰鏉′欢銆?