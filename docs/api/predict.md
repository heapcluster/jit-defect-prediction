# 妯″瀷棰勬祴 API锛坧redict锛?
涓€鍙ヨ瘽锛氱嫭绔嬪姞杞芥ā鍨嬪寘鎴栧凡鍔犺浇妯″瀷锛屽鍗曟彁浜ゆ垨琛ㄦ牸鎵规杈撳嚭椋庨櫓姒傜巼銆佸垽瀹氭爣绛惧拰鐗堟湰淇℃伅锛屽苟浜や粯缁熶竴 `predictions.csv`锛屼笉鍦ㄩ娴嬫湇鍔″唴鐢熸垚瑙ｉ噴鎴栧畾浣嶃€?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.1銆伮?.2銆伮?.3銆伮?.4銆伮?.9锛涙ā鍨嬬鐞嗚 [models.md](models.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗妯″瀷鍖呮牎楠屻€佺壒寰佸垪瀹芥牎楠屻€佸崟鏉″嵆鏃堕娴嬨€佹枃浠舵壒閲忛娴嬨€侀槇鍊煎垽瀹氥€佺粨鏋滃箓绛夊拰棰勬祴鏂囦欢浜や粯銆?- 鍗曟潯璇︽儏鍙€夋嫨娌跨敤搴撲腑缁撴灉鎴栫珛鍗抽噸鏂拌绠楋紱鎵归噺鏂囦欢杩愯涓嶄緷璧栧簱涓凡鏈夐娴嬨€?- 涓嶈礋璐ｈ缁冦€佹€ц兘璇勪及銆乆AI 鎴栬绾у畾浣嶃€傚搷搴斾笉鍖呭惈 `explanation`锛岄娴嬫湇鍔＄姝㈣皟鐢ㄨВ閲婃垨瀹氫綅鏈嶅姟锛涜鎯呴〉鍙苟琛岀紪鎺?`/api/explain` 涓?`/api/localize/run`銆?- 涓嶉殣寮忔妸鎵归噺鏂囦欢缁撴灉瀵煎叆灞曠ず琛紱闇€瑕佹椂鐢辫皟鐢ㄦ柟鍙﹁皟 storage銆?
> W8 宸茬Щ闄ゅ崟鏉￠娴嬬殑 explanation 鍜岄娴嬪唴閮ㄧ殑 SHAP 璋冪敤锛岃鎯呴〉缁?`/api/explain` 鍗曠嫭璇诲彇瑙ｉ噴锛沠eatures/summary 浠嶄负鐜版湁璇︽儏灞曠ず瀛楁銆俻rediction 宸茶惤 `model_version / feature_version` 涓ゅ彲绌哄垪锛氬崟鏉℃部鐢ㄥ簱涓粨鏋滄椂鎸夎鍐呯増鏈笌褰撳墠妯″瀷/鐗瑰緛鐗堟湰瀵规瘮杩斿洖鐪熷疄 `stale`锛屽巻鍙?NULL 鐗堟湰琛岃涓鸿繃鏈燂紝`force_recompute` 閲嶇畻骞跺埛鏂扮増鏈€傛壒閲?run 宸蹭氦浠?搂3.4 鏂囦欢 + summary + manifest锛屾敮鎸?expert / semantic 涓ょ嚎锛堣 搂3锛夛紱妯″瀷绠＄悊 status/load/unload/reload/default 瑙?[models.md](models.md)銆?
## 2. 绔偣濂戠害

### POST /api/predict

鍗曟潯 JSON 璇锋眰锛屼緵鎻愪氦璇︽儏缂栨帓锛?
| 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `commit_hash` | 鏄?| 40 浣?hex锛屽綊涓€鍖栦负灏忓啓 |
| `model_name` | 鏄?| 蹇呴』鏄惧紡鎸囧畾宸插姞杞芥ā鍨嬶紱涓嶈榛樿鍊兼垨鍥為€€瑙勫垯 |
| `decision_threshold` | 鍚?| 寮€鍖洪棿 (0,1)锛岀己鐪佽鍏ㄥ眬閰嶇疆 |
| `force_recompute` | 鍚?| 榛樿 `false`锛氬悓妯″瀷涓庣壒寰佺増鏈湁鍙敤搴撲腑缁撴灉鍒欐部鐢紱`true` 绔嬪嵆閲嶆柊璁＄畻 |

鍝嶅簲 `data`锛?
| 瀛楁 | 鍚箟 |
|---|---|
| `commit_hash` / `model_name` | 鎻愪氦涓庡疄闄呮ā鍨?|
| `risk_score` | [0,1] 姒傜巼 |
| `predicted_label` | 鎸夋湰娆?decision_threshold 寰楀埌鐨?0/1 |
| `decision_threshold` | 瀹為檯鍒ゅ畾闃堝€?|
| `risk_level` | 鎸?risk_high_threshold / risk_mid_threshold 寰楀埌鐨?high/mid/low |
| `model_version` / `feature_version` | 鐗堟湰杩芥函 |
| `predicted_at` | 鏈缁撴灉鏃堕棿锛孶TC `Z` |
| `result_source` | `stored` / `computed`锛屾槑纭部鐢ㄦ垨閲嶇畻 |
| `stale` | 妯″瀷鎴栫壒寰佺増鏈彉鍖栧鑷存棫缁撴灉杩囨湡鏃朵负 true |

璇锋眰绂佹澶氫綑瀛楁銆傛棤 `explanation`銆佸畾浣嶃€佷慨澶嶅缓璁瓧娈碉紱搴撲腑娌跨敤涔熶笉寰椾吉瑁呮垚鏂拌绠楁椂闂淬€?
### POST /api/predict/run

`multipart/form-data`锛歚files[]` 鎺ユ敹涓€涓?`collected_commits` / `clean_dataset` 琛ㄦ牸锛圕SV/XLSX锛夛紝浠ュ強鍙€変竴涓?`model_package.zip`锛沗config` JSON part銆傚皬鏂囦欢鍚屾锛屽ぇ鏂囦欢鍒涘缓 `kind=predict_batch` job銆?
| config 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `dataset_id` | 鍚?| 宸插鍏ヨ緭鍏ヨ〃鐨勪究鍒╅€夋嫨锛涗笌涓婁紶琛ㄦ牸浜岄€変竴 |
| `model_name` | 鍚?| 浣跨敤宸插姞杞芥垨宸茬櫥璁版ā鍨嬶紱涓婁紶妯″瀷鍖呮椂鍙渷鐣?|
| `decision_threshold` | 鍚?| 缂虹渷璇?`user_config.decision_threshold` |
| `batch_size` | 鍚?| 姝ｆ暣鏁帮紝缂虹渷璇?`predict.batch_size` |
| `force_recompute` | 鍚?| 榛樿 true锛堟枃浠惰繍琛屽缁堟寜杈撳叆璁＄畻锛夛紱false 浠呭鍙€夊簱杈撳叆鍏佽澶嶇敤鍚岀増鏈粨鏋?|
| `format` | 鍚?| `csv` / `xlsx`锛岄粯璁?`csv` |

妯″瀷瑙ｆ瀽椤哄簭锛氭樉寮忎笂浼犳ā鍨嬪寘 鈫?鏄惧紡 `model_name`锛涗袱鑰呯殕鏃犺繑鍥?40001锛屼笉璁鹃粯璁ゅ€兼垨鐗堟湰搴忓洖閫€銆傚悓姝ュ搷搴?`{job_id,status:"success",outputs[],summary}`锛涘紓姝?`{job_id,status:"queued"}`銆俿ummary 鍚€绘暟銆佹垚鍔熸暟銆佸け璐ユ暟銆佸疄闄呮ā鍨嬩笌闃堝€硷紱閫愯澶辫触涓嶅緱琚啓鎴愰闄?0銆?
### GET /api/predict/outputs/{job_id}/{name}

涓嬭浇 predictions 鎴?manifest锛涢壌鏉冧笌鏂囦欢鍚嶉檺鍒跺悓鍏叡濂戠害銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 澶氫綑瀛楁銆侀潪娉曢槇鍊笺€佹ā鍨?鐗瑰緛涓嶅吋瀹广€乧hecksum 澶辫触銆佽緭鍏?schema 闈炴硶銆佺┖鐩爣銆佸悓 kind 鍐茬獊 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key` |
| 40400 | 404 | 鎻愪氦銆佹ā鍨嬨€佸彲閫?dataset銆乯ob 鎴栬緭鍑轰笉瀛樺湪 |
| 50000 | 500 | 鏈鏈熸湇鍔￠敊璇紱鎵归噺杩愯鏈熷け璐ュ啓鑴辨晱 job 鏃ュ織 |

## 3. 杈撳叆濂戠害

妯″瀷鍖呴€愬瓧閲囩敤 搂3.3锛?
> zip 鍐呭惈锛氭潈閲嶆枃浠跺潎涓?`.pkl`锛坄expert`=Kamei 14 缁淬€乣semantic`=鍐荤粨澶?CodeBERT 768 缁达級銆乣feature_order.txt`銆乣feature_schema.json`銆乣model_meta.json`锛坢odel_name/line/algo/feature_set/version_key/feature_version/trained_at/瓒呭弬蹇収/鍒掑垎 mode/绉嶅瓙锛夈€乣checksum.sha256`銆俙fused` / `e2e` 鍙婂叾 safetensors 浜х墿宸插彇娑堛€俻redict/explain MUST 鏍￠獙 checksum 涓庣壒寰佸垪瀹藉悗鍐嶅姞杞姐€?
琛ㄦ牸閲囩敤 搂3.2 `clean_dataset`锛涜瘎浼板満鏅噰鐢?搂3.3 `train_testset`锛堟瘡琛屽甫鐪熸爣绛撅紝schema 涓?搂3.2 閫愬垪涓€鑷达級銆傝緭鍏ュ垪濂戠害锛埪?.2锛夛細

| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40 hex) | 鏄?| 鎻愪氦鏍囪瘑锛堝皬鍐欙級 |
| repo_name | string | 鏄?| 浠撳簱鍚嶆垨鏁版嵁闆嗗悕 |
| repo_url | string | 鍚?| 鏉ユ簮 URL |
| author_name / author_email | string | 鍚?| 浣滆€?|
| committed_at | datetime | 鍚?| 鎻愪氦鏃堕棿 UTC |
| message | string | 鍚?| 鎻愪氦淇℃伅 |
| parent_hash | string(40) | 鍚?| 鐖舵彁浜?|
| is_bug_inducing | int 绌哄彲 | 鏄?| 缂洪櫡鏍囩 1/0/绌猴紱璇勪及鍦烘櫙 MUST 闈炵┖ |
| label_method | string | 鍚?| 鏍囩鏂规硶 |
| label_source | string | 鏄?| `git_szz` / `public_dataset` |
| labeled_at | datetime | 鍚?| 鎵撴爣鏃堕棿 |
| fix_commit_hash | string(40) | 鍚?| SZZ 鍥炴函淇鎻愪氦 |
| source_type | string | 鏄?| `git_repo` / `public_dataset` |

妯″瀷鐗瑰緛涓嶅湪杈撳叆琛ㄤ腑锛岀敱璁粌闃舵鐢熸垚骞跺浐鍖栬繘妯″瀷鍖呫€俍IP 杩橀』鏍￠獙璺緞绌胯秺銆佹枃浠舵暟閲忓拰瑙ｅ帇澶у皬锛涜〃鏍兼墽琛屽ぇ灏忋€佹墿灞曞悕榄旀暟銆乻chema銆佸叕寮忔敞鍏ユ牎楠屻€備换浣曟枃浠跺悕涓嶅緱鎷兼帴 shell銆傜壒寰侀『搴忎弗鏍兼寜鍖呭唴 `feature_order.txt`锛岀姝㈡寜瀛楀吀搴忕寽娴嬨€?
**鐪熸爣绛鹃€忎紶**锛氳緭鍏ヨ鐨?`is_bug_inducing` MUST 鍘熸牱鍐欏叆 搂3.4 `predictions.csv` 鍚屽悕鍒椼€傝瘎浼板満鏅紙杈撳叆 `train_testset`锛夌湡鏍囩蹇呴潪绌猴紝缂烘爣绛惧湪 predict 鍓嶇疆鎷掔粷锛涢娴嬫柊鎻愪氦鍦烘櫙鍏佽鏍囩绌猴紝浣嗙粨鏋滀笉渚涙€ц兘璇勪及銆?
鎸夋ā鍨嬬嚎鐨勬壒閲忚緭鍏ュ彛寰勶細

- **expert**锛氫竴涓?搂3.1/搂3.2 鎻愪氦琛紙鎴?`dataset_id`锛夋彁渚涙彁浜ゆ爣璇嗭紱14 缁寸壒寰佺敱妯″瀷鍖?`feature_order.txt` 椹卞姩銆佷粠缁戝畾浠撳簱鐨勬彁浜ゅ揩鐓х幇绠楋紙涓庤缁冧晶鍚屼竴鎶藉彇鍣級锛屼笉浠庝笂浼犺〃璇诲彇鐗瑰緛鍒椼€傜己鍙浠撳簱鎴栨彁浜や笉鍙揪杩斿洖 40001锛涗笉鎺ュ彈鏂囨湰琛ㄣ€?- **semantic**锛氫竴涓?搂3.1/搂3.2 鐗瑰緛琛ㄦ彁渚涙彁浜ゅ搱甯屼笌鐪熸爣绛撅紱768 缁磋涔夊悜閲忔寜 `commit_hash` 鍙栭璁＄畻 embedding锛坄semantic_embeddings.npz`锛屽喕缁撳ご CodeBERT锛夛紝缂哄け鏃惰嫢鏈満鏈夊喕缁撶紪鐮佸櫒鍒欎粠缁戝畾浠撳簱鍦ㄧ嚎缂栫爜锛屼粛涓嶅彲鐢ㄨ琛屾槑纭け璐ワ紙涓嶇紪閫犲悜閲忥級銆備笉鎺ユ敹鐙珛鏂囨湰琛ㄣ€?- `fused`锛?82 缁存嫾鎺ワ級涓?`e2e`锛堟枃鏈?/ 寰皟鍒嗙被澶达級涓ょ嚎宸茬爫鎺夛紝鐩稿叧妯″瀷鍖呬笌鏂囨湰琛ㄨ緭鍏ヤ笉鍐嶉€傜敤銆?- CLI `predict run` 涓?API 鍚屾簮锛歚--model-package` 鎴?`--model` 浜岄€変竴锛宍--input` 涓?搂3.1/搂3.2 鐗瑰緛琛紝涓嶆帴鍙楁枃鏈〃锛涚己杈撳叆鏄庣‘鎶ラ敊銆?
## 4. 杈撳嚭濂戠害

涓绘枃浠?`predict_predictions_<job_id>.csv`锛堟垨 `.xlsx`锛夛紝manifest `predict_predictions_<job_id>.manifest.json`銆備富琛ㄩ€愬瓧閲囩敤 搂3.4锛?
| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40) | 鏄?| 鎻愪氦 |
| model_name | string | 鏄?| 妯″瀷 |
| risk_score | float [0,1] | 鏄?| 姒傜巼锛? 浣嶅皬鏁帮級 |
| predicted_label | int 0/1 | 鏄?| 鎸?decision_threshold 鐨勪簩鍒嗙被鏍囩 |
| decision_threshold | float | 鏄?| 鏈鍒ゅ畾闃堝€?|
| model_version / feature_version | string | 鏄?| 鐗堟湰鍏冧俊鎭?|
| predicted_at | datetime | 鏄?| 棰勬祴鏃堕棿 |
| is_bug_inducing | int 绌哄彲 | 鍚?| 閫忎紶鐪熸爣绛撅紙鏉ヨ嚜 搂3.3 `train_testset`锛屼緵 evaluate 绠楁€ц兘锛涜瘎浼板満鏅繀闈炵┖锛?|

姒傜巼涓庢爣绛惧垎绂伙紝闃堝€间笉鏀瑰彉 risk_score锛涜緭鍏ョ湡鏍囩鍘熸牱閫忎紶锛屾湭鎵撴爣鐣欑┖銆侰SV UTF-8 BOM锛孹LSX 鍗?sheet锛沵anifest 涓ユ牸绗﹀悎 搂3.9锛岃褰曟ā鍨嬪寘 checksum銆佺壒寰佺増鏈€侀槇鍊笺€佽緭鍏ヤ笌杈撳嚭 checksum銆?
鍗曟潯绔偣鍙繑鍥?JSON 骞跺箓绛夊啓 prediction锛屼笉棰濆浜х敓浜ゆ崲鏂囦欢锛涙壒閲?run 蹇呴』浜х敓涓婅堪鏂囦欢涓?manifest銆?
## 5. 鍙厤缃」

- 鍏ㄥ眬锛歚decision_threshold`銆乣risk_high_threshold`銆乣risk_mid_threshold`锛涙ā鍨嬩笉璁鹃粯璁ゅ€笺€?- 鍛藉悕绌洪棿锛歚predict.batch_size`銆乣predict.cache_ttl`銆乣predict.retry_max`锛屽潎钀?`user_config` 骞堕噸鍚仮澶嶃€?- 鍗曟杩愯鍙寚瀹氭ā鍨嬪寘/妯″瀷銆侀槇鍊笺€佹壒閲忓ぇ灏忓拰杈撳嚭鏍煎紡锛涙樉寮忛槇鍊艰繘鍏?manifest锛屼笉浠庢ā鍨嬪寘鐚滄祴銆?- `.env` 浠呮彁渚涘嚭鍘傞粯璁わ紱妯″瀷閲嶈浇鏄?models 绠＄悊鍔ㄤ綔锛屼笉鐢遍娴嬭姹傞殣寮忚Е鍙戙€?
## 6. 鐘舵€佹寔涔呭寲

- 鎵归噺 run 鍚屾鍐欑粓鎬侊紝寮傛 kind=`predict_batch` 鍐欎簲鎬侊紱鍚?kind 鏉′欢鏇存柊浜掓枼锛岄噸鍚仐鐣?running 缃?failed锛屽彲 retry/cancel銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紝job 鐧昏杈撳嚭鍜屾垚鍔?澶辫触璁℃暟銆?- 鍗曟潯棰勬祴鎸?`(commit_hash,model_name)` 骞傜瓑鏇存柊锛岃褰曟ā鍨?鐗瑰緛鐗堟湰锛涙部鐢ㄧ粨鏋滆繑鍥?stored锛岄噸绠楄繑鍥?computed銆?- 鎵归噺鏂囦欢浜х墿鏄惁瀵煎叆 prediction 鐢?storage 鍐冲畾锛岄娴嬭绠楁湰韬笉瑕佹眰鏁版嵁搴撴垨 explain/localize 鍙敤銆?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/predict/`锛屽彲鍙嚟涓婁紶琛ㄦ牸涓庢ā鍨嬪寘杩愯銆?
- **姝ｅ父**锛氬崟鏉?computed/stored 涓ょ璺緞涓庢壒閲?CSV/XLSX 鍧囪繑鍥炴纭鐜囥€佹爣绛俱€侀槇鍊煎拰鐗堟湰锛浡?.4 椋庨櫓鍒?5 浣嶅皬鏁帮紝manifest checksum 鍙獙銆?- **杈圭晫**锛氶粯璁ゆā鍨嬫湭閰嶇疆銆侀槇鍊兼帴杩?0/1銆佺┖鐪熸爣绛俱€侀噸澶嶆彁浜ゃ€侀儴鍒嗚澶辫触銆佺紦瀛樿繃鏈熷潎涓嶅～閫?0锛屼笉鏀瑰彉姒傜巼璇箟銆?- **闈炴硶**锛氬浣欏崟鏉″瓧娈点€佹崯鍧?ZIP銆乧hecksum 鎴栫壒寰佸垪瀹戒笉绗︺€佽矾寰勭┛瓒娿€佺己鍒椼€佸叕寮忔敞鍏ャ€侀潪娉曢槇鍊煎潎杩斿洖 40001锛涙棤瑙ｉ噴瀛楁涓旈娴嬫湇鍔℃棤瑙ｉ噴/瀹氫綅璋冪敤銆?- 鍚屾彁浜ゅ悓妯″瀷鍐欏簱骞傜瓑锛涘ぇ鏂囦欢 job 閲嶅惎缃?failed锛汣LI/API 鍚?fixture 杈撳嚭涓€鑷淬€?
## 8. 杈圭晫

predict 涓?train 閫氳繃 搂3.3銆佷笌 clean 閫氳繃 搂3.1/搂3.2銆佷笌 evaluate/explain/localize 閫氳繃 搂3.4 鏂囦欢鍏煎銆俙dataset_id` 鍙究鍒╅€夋嫨杈撳叆锛沞xplain/localize 娑堣垂棰勬祴浜х墿锛屽弽鍚戣皟鐢ㄧ姝€?