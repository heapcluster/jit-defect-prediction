# 棰勬祴缁撴灉瑙ｉ噴 API锛坋xplain锛?
涓€鍙ヨ瘽锛氱嫭绔嬫秷璐规ā鍨嬪寘涓庡緟瑙ｉ噴鎻愪氦鐨勭壒寰佽锛屾寜鎵€閫?SHAP/LIME 绛夋妧鏈緭鍑虹粺涓€璐＄尞缁撴瀯锛沺redictions 鏂囦欢浠呯敤浜庡彲閫夌殑鐗堟湰涓庤寖鍥存牳瀵癸紝涓嶆敮鎸佺殑缁勫悎浠ユ槑纭?reason_code 浜や粯銆?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.1銆伮?.3銆伮?.4銆伮?.7銆伮?.9锛涘叕鍏卞彛寰勮 [README.md](README.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗瑙ｉ噴鍣ㄦ敞鍐屻€佹ā鍨嬫棌涓庢妧鏈€傞厤銆佸崟鏉″強鏂囦欢鎵归噺瑙ｉ噴銆佺紦瀛樸€佸鎶€鏈瘮杈冨拰缁熶竴鏂囦欢浜や粯銆?- 涓€鏈熻嚦灏戞敮鎸?SHAP 涓?LIME锛涙敮鎸佹€х敱绠楁硶鏃忎笌鎶€鏈煩闃靛喅瀹氾紝涓嶉檺瀹氭煇涓€妯″瀷绾裤€?- 涓嶈礋璐ｉ娴嬫墦鍒嗐€侀噸璁€佹寚鏍囪绠楁垨琛岀骇瀹氫綅锛涜В閲婁笉寰楁敼鍙?risk_score 涓?predicted_label銆?- predict 鏈嶅姟涓嶈皟鐢ㄦ湰妯″潡锛涜鎯呴〉鐙珛璋冪敤 `/api/explain`锛岄噸鏂伴娴嬫垚鍔熷悗鍙﹁鍒锋柊瑙ｉ噴锛涜В閲婂け璐ヤ笉褰卞搷棰勬祴灞曠ず銆?- 椤甸潰灞備綔涓衡懁棰勬祴鐨勫瓙椤碉紝鍙粠棰勬祴缁撴灉/鎻愪氦璇︽儏甯﹀叆 commit/model锛涙帴鍙ｆ湰韬嫭绔嬶紝涓嶄緷璧栤懁鍦ㄧ嚎銆?
W8 瀹炵幇鍖呮嫭甯︾鍙?SHAP銆佺湡瀹?LIME 灞€閮ㄤ唬鐞嗐€佸弬鏁版敞鍐岃〃銆佹彁浜?妯″瀷/鐗瑰緛/鍙傛暟/浠ｇ爜 checksum 缂撳瓨鍙婄嫭绔?CLI銆傜嚎鎬?SHAP 杈撳嚭灏哄害涓?log_odds锛屾爲 SHAP 涓?tree_raw锛汱IME 涓?local_probability_coefficient锛屼笉鑳芥妸涓ょ鎶€鏈殑鏁板€肩洿鎺ョ浉鍔犳垨姣旇緝缁濆澶у皬銆傛湭鎻愪緵鐪熷疄鑳屾櫙鏁版嵁鏃讹紝绾挎€?SHAP 浣跨敤闆跺弬鑰冿紝LIME 浣跨敤闆跺€煎拰姝ｈ礋鍗曚綅鍊煎悎鎴愬弬鑰冨苟鏄庣‘鎻愮ず锛屼笉鍐掔О鐪熷疄璁粌鍒嗗竷銆?
## 2. 绔偣濂戠害

### GET /api/explain/techniques

鏌ヨ鍙傛暟鍧囧彲閫夛細`line`銆乣model_name`銆傚搷搴?`data`锛?
| 瀛楁 | 鍚箟 |
|---|---|
| `techniques[]` | `{key,name,description,params_schema[]}`锛屼竴鏈熷惈 shap/lime |
| `compatibility[]` | `{family,technique,supported,reason_code}` |
| `default_technique` | `user_config.default_xai` |
| `compare_enabled` | `explain.compare_enabled` 褰撳墠鍊?|

闈炴硶 line/model_name 鍒嗗埆杩斿洖 40001/40400銆?
### POST /api/explain

鍗曟潯鍚屾 JSON锛屼緵璇︽儏缂栨帓锛涘彧璇诲凡瀛橀娴嬩笌宸插姞杞芥ā鍨嬶紝涓嶈皟鐢?predict 鏈嶅姟銆?
| 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `commit_hash` | 鏄?| 宸插瓨鍦ㄩ娴嬩笌鐗瑰緛杈撳叆鐨勬彁浜?|
| `model_name` | 鏄?| 蹇呴』鏄惧紡鎸囧畾宸插姞杞芥ā鍨嬶紱涓嶈榛樿鍊兼垨鍥為€€ |
| `technique` | 鍚?| 缂虹渷璇?default_xai |
| `params` | 鍚?| 鎸夋妧鏈?schema 鏍￠獙锛屽閲囨牱鏁般€佽儗鏅泦澶у皬銆乼op_n |

鍝嶅簲 `data` 涓?`{commit_hash,model_name,technique,model_version,feature_version,items[],reason_code,message}`锛沬tems 鍏冪礌涓?搂3.7 鐨勭壒寰佽础鐚瓧娈典竴鑷淬€備笉鏀寔缁勫悎蹇呴』甯?reason_code锛屼笉寰楅潤榛樿繑鍥炵┖鏁扮粍銆?
### POST /api/explain/run

`multipart/form-data`锛氫富杈撳叆涓哄惈寰呰В閲婃彁浜ょ壒寰佽鐨?commits/cleaned 琛ㄦ牸涓庢ā鍨嬶紱`files[]` 蹇呴』鍚壒寰佽〃锛屾ā鍨嬪彲鐢变笂浼?`model_package.zip` 鎴栧凡鍔犺浇妯″瀷鎻愪緵锛涘凡鐧昏浣嗘湭鍔犺浇鐨勬ā鍨嬮』鍏堝湪妯″瀷绠＄悊涓樉寮忓姞杞姐€俻redictions 琛ㄦ牸浠呬负鍙€夌殑妯″瀷鐗堟湰涓庢彁浜よ寖鍥存牳瀵规枃浠讹紝涓嶈兘浣滀负杩愯鍓嶇疆锛涘彧涓婁紶妯″瀷鍖呬笌鐗瑰緛琛ㄥ嵆鍙В閲娿€備骇鐗╅€夋嫨涓庝即闅?manifest 鎻愪氦閬靛惊 [鍏叡娴佺▼](README.md#浜х墿搴撻€夋嫨涓庝笂浼犵瓑浠?锛岄厤缃斁 `config` JSON part銆備笉瓒呰繃 20 鏉℃彁浜ゅ悓姝ユ墽琛岋紝鍏朵粬杈撳叆鍒涘缓 `kind=explain` job銆傚悎璁′笂浼犱笌褰掍竴鍖栭噸璇曞揩鐓у潎闄愬埗 64MiB锛涜緭鍏ユ枃浠惰嚦澶?6 涓笖鍚嶇О鍘婚噸銆?
| config 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `dataset_id` | 鍚?| 宸插鍏ヨ緭鍏ユ枃浠剁殑渚垮埄閫夋嫨锛涙樉寮忎笂浼犱紭鍏?|
| `model_name` | 鍚?| 鏈笂浼犳ā鍨嬪寘鏃跺繀椤绘樉寮忔寚瀹氬凡鍔犺浇妯″瀷 |
| `techniques[]` | 鏄?| 闈炵┖鎶€鏈暟缁勶紱姣旇緝鏃堕渶 `explain.compare_enabled=true` |
| `params` | 鍚?| `{technique:{param:value}}` |
| `top_n` | 鍚?| 姣忚姣忔妧鏈緭鍑虹殑鏈€澶х壒寰佹暟锛屾鏁存暟 |
| `cache_ttl` | 鍚?| 缂虹渷璇?`explain.cache_ttl`锛? 绂佺敤缂撳瓨 |
| `commit_hashes[]` | 鍚?| 闈炵┖鍘婚噸灏忓啓鍝堝笇锛屽繀椤诲湪杈撳叆鐗瑰緛琛ㄨ寖鍥村唴 |
| `format` | 鍚?| `csv` / `xlsx`锛岄粯璁?`csv` |

鍚屾鍝嶅簲 `{job_id,status:"success",outputs[],summary}`锛涘紓姝?`{job_id,status:"queued"}`銆俿ummary 鍚緭鍏ユ牱鏈暟銆佹垚鍔熻В閲婃暟銆佹妧鏈垪琛ㄤ笌 reason_code 璁℃暟锛屼笉浠ラ娴嬫枃浠跺瓨鍦ㄤ笌鍚﹀喅瀹氳緭鍏ヨ鏁般€?
### GET /api/explain/outputs/{job_id}/{name}

涓嬭浇 explanations 鎴?manifest銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 鎶€鏈垨鍙傛暟闈炴硶銆佺粍鍚堜笉鏀寔銆佺壒寰?妯″瀷/棰勬祴涓嶅尮閰嶃€佸悓 kind 鍐茬獊銆侀潪娉曟枃浠跺悕 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key` |
| 40400 | 404 | 鎻愪氦銆佹ā鍨嬨€佸彲閫?dataset銆乯ob 鎴栬緭鍑轰笉瀛樺湪 |
| 50000 | 500 | 鏈鏈熸湇鍔￠敊璇紱杩愯鏈熷け璐ュ啓鑴辨晱 job 鏃ュ織 |

## 3. 杈撳叆濂戠害

鍙€?predictions 鏍稿鏂囦欢閫愬瓧閲囩敤 搂3.4锛涙湭鎻愪緵鏃跺彧渚濇嵁妯″瀷鍖呬笌鐗瑰緛琛ㄤ腑鐨勬彁浜よ寖鍥存墽琛岃В閲婏細

| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40) | 鏄?| 鎻愪氦 |
| model_name | string | 鏄?| 妯″瀷 |
| risk_score | float [0,1] | 鏄?| 姒傜巼锛? 浣嶅皬鏁帮級 |
| predicted_label | int 0/1 | 鏄?| 鎸?decision_threshold 鐨勪簩鍒嗙被鏍囩 |
| decision_threshold | float | 鏄?| 鏈鍒ゅ畾闃堝€?|
| model_version / feature_version | string | 鏄?| 鐗堟湰鍏冧俊鎭?|
| predicted_at | datetime | 鏄?| 棰勬祴鏃堕棿 |
| is_bug_inducing | int 绌哄彲 | 鍚?| 閫忎紶鐪熸爣绛撅紙渚夸簬 evaluate 鍗曟枃浠惰緭鍏ワ級 |

寰呰В閲婃彁浜ゆ潵鑷?搂3.1 `collected_commits` 鎴?搂3.2 `clean_dataset`锛屼袱琛ㄥ潎涓烘彁浜ゅ厓淇℃伅 + 鏍囩 + 鍩虹娲剧敓鍒楋紝**涓嶅惈 Kamei 14 缁淬€佽涔夊悜閲忔垨 `is_test`**銆俥xpert 鐨勬ā鍨嬭緭鍏ョ壒寰佺敱璁粌闃舵鍐呴儴鐢熸垚骞跺浐鍖栬繘妯″瀷鍖呯殑 `feature_order.txt` / `feature_schema.json`锛涘姞杞芥ā鍨嬪寘鍚庢寜鍖呭唴鐗瑰緛椤哄簭锛屼粠缁戝畾浠撳簱鐨勮鎻愪氦蹇収鐜扮畻 14 缁达紙涓庤缁冧晶鍚屼竴鎶藉彇鍣級锛屼笉浠庝笂浼犺〃鏍艰鍙栫壒寰佸垪銆俿emantic 绾挎寜 `commit_hash` 鍙栭璁＄畻 `semantic_embeddings.npz`锛堝喕缁撳ご CodeBERT 768 缁达級锛岀己澶变笖鏈夋湰鍦板喕缁撶紪鐮佸櫒鏃跺湪绾跨紪鐮侊紝浠嶄笉鍙敤杩斿洖 40001锛屼笉缂栭€犲悜閲忋€傝姹備笂浼犲惈 14 缁?/ `is_test` 鍒楃殑鏂囦欢灞炰簬宸插簾姝㈠彛寰勶紝鎸夋湭鐭ュ垪鎷掔粷銆備粎鎻愪緵鍙€?predictions 鏃舵墠鎸?hash 鏍稿鎻愪氦鑼冨洿涓庢ā鍨嬬増鏈紱鏈彁渚涙椂浠ヨ緭鍏ヨ〃涓殑鎻愪氦涓鸿В閲婂璞°€偮?.1 鐨勫浐瀹氬绾︿负锛?
| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40 hex) | 鏄?| 鎻愪氦鏍囪瘑锛堝皬鍐欙級 |
| repo_name | string | 鏄?| 浠撳簱鍚嶆垨鏁版嵁闆嗗悕 |
| repo_url | string | 鍚?| 浠撳簱 URL 鎴栨暟鎹泦鏉ユ簮 |
| author_name / author_email | string | 鍚?| 浣滆€?|
| committed_at | datetime | 鍚?| 鎻愪氦鏃堕棿锛孶TC ISO 8601 |
| message | string | 鍚?| 鎻愪氦淇℃伅 |
| parent_hash | string(40) | 鍚?| 鐖舵彁浜?|
| is_bug_inducing | int 绌哄彲 | 鏄?| 缂洪櫡鏍囩 1/0/绌猴紱璇勪及鍦烘櫙闈炵┖ |
| label_method | string | 鍚?| `szz_v1` / `szz_lite` / `third_party` |
| label_source | string | 鏄?| `git_szz` / `public_dataset` |
| labeled_at | datetime | 鍚?| 鎵撴爣鏃堕棿 |
| fix_commit_hash | string(40) | 鍚?| SZZ 鍥炴函淇鎻愪氦 |
| source_type | string | 鏄?| `git_repo` / `public_dataset` |

妯″瀷鎵€闇€浠撳簱鏉ユ簮鐢?`collect.allow_roots` 鐧藉悕鍗曞唴鐨勬湰鍦颁粨搴撴彁渚涳紱CLI 闇€鏄惧紡 `--repo` / `--allow-root`锛孒TTP 杩愯鐢遍厤缃腑蹇冪粦瀹氫粨搴撹矾寰勩€傜己鍙浠撳簱鎴栨彁浜や笉鍙揪鏃跺墠缃嫆缁濓紙40001锛夛紝涓嶇寽娴嬬壒寰併€佷笉濉?0銆?
妯″瀷鍖呴€愬瓧閲囩敤 搂3.3锛?
> zip 鍐呭惈锛氭潈閲嶆枃浠跺潎涓?`.pkl`锛坄expert`=Kamei 14 缁淬€乣semantic`=鍐荤粨澶?CodeBERT 768 缁达級銆乣feature_order.txt`銆乣feature_schema.json`銆乣model_meta.json`锛坢odel_name/line/algo/feature_set/version_key/feature_version/trained_at/瓒呭弬蹇収/鍒掑垎 mode/绉嶅瓙锛夈€乣checksum.sha256`銆俙fused` / `e2e` 鍙婂叾 safetensors 浜х墿宸插彇娑堛€俻redict/explain MUST 鏍￠獙 checksum 涓庣壒寰佸垪瀹藉悗鍐嶅姞杞姐€?
涓婁紶鎵ц澶у皬銆佹墿灞曞悕榄旀暟銆乻chema銆乑IP 璺緞绌胯秺銆乧hecksum 鍜屽叕寮忔敞鍏ユ牎楠屻€傛ā鍨嬪寘涓庣壒寰佽〃蹇呴』鍏煎锛涗粎鍦ㄦ彁渚?predictions 鏃堕澶栨牳瀵瑰叾妯″瀷鐗堟湰銆佺壒寰佺増鏈笌鎻愪氦鑼冨洿锛屼笉涓€鑷磋繑鍥?40001銆傛湭鎻愪緵 predictions 涓嶇畻缂哄皯杈撳叆锛屼笉鐚滄祴瀵归綈銆?
## 4. 杈撳嚭濂戠害

涓绘枃浠?`explain_explanations_<job_id>.csv`锛堟垨 `.xlsx`锛夛紝manifest `explain_explanations_<job_id>.manifest.json`銆偮?.7 閫愬瓧瑙勫畾锛?
> `commit_hash,model_name,technique,feature,raw_value,contribution,direction,rank,label,model_version,feature_version`锛涗笉鏀寔缁勫悎浜?`reason_code` 琛岋紙feature 绌恒€乧ontribution 绌恒€乺eason_code 闈炵┖锛夛紝MUST NOT 闈欓粯缂鸿銆?
- 澶氭妧鏈粨鏋滃啓鍏ュ悓涓€闀胯〃锛屼互 technique 鍖哄垎锛涙瘡鎻愪氦姣忔妧鏈寜 rank 鎺掑簭锛宑ontribution 淇濈暀绗﹀彿锛宒irection 鑷冲皯鍖哄垎 increase/decrease銆?- 涓嶆敮鎸佺殑缁勫悎蹇呴』淇濈暀 reason_code 琛岋紝涓嶈兘浠ョ己灏戣緭鍑轰唬鏇胯鏄庯紱鍚堟硶绌虹壒寰佷笌涓嶆敮鎸佷笉寰楁贩娣嗐€?- CSV UTF-8 BOM銆乆LSX 鍗?sheet锛屼袱鏍煎紡鍧囦氦浠橈紱瑙ｉ噴涓昏〃閲囩敤 搂3.7 鐨?11 鍒楀苟鍥哄畾澧炲姞 reason_code锛堟垚鍔熻涓虹┖锛夈€俢omparison JSON 鍙﹀甫 base_value銆乷utput_space銆佽鏄庛€侀€愭彁浜?鎶€鏈粨鏋滐紱summary 缁熻 input_rows銆乻uccess_count锛堟彁浜?脳 鎶€鏈級銆乺eason_counts 鍜?cache_hits銆傝础鐚浘灞曠ず棣栦釜鎴愬姛鎻愪氦/鎶€鏈紝瀹屾暣缁撴灉瑙佷富琛ㄤ笌 comparison銆?- manifest 涓ユ牸閲囩敤 搂3.9锛屾瘡涓熀纭€浜х墿鍚?stem 涓€浠斤紝CSV/XLSX 鍏辩敤锛涜褰曡緭鍏?妯″瀷 checksum銆佹妧鏈弬鏁般€佺紦瀛橀厤缃拰杈撳嚭 checksum銆?- 鍗曟潯 POST 鍙繑鍥?JSON锛屼笉浜х敓浜ゆ崲鏂囦欢锛涙壒閲?run 蹇呴』浜や粯涓昏〃涓?manifest銆?
## 5. 鍙厤缃」

- 鍏ㄥ眬 `default_xai`锛涘懡鍚嶇┖闂?`explain.cache_ttl`銆乣explain.compare_enabled`銆?- 鍗曟杩愯锛氭妧鏈暟缁勩€侀€愭妧鏈弬鏁般€乼op_n銆佺紦瀛?TTL銆佽緭鍑烘牸寮忥紱鎶€鏈粯璁ゅ€间笌姣旇緝寮€鍏抽噸鍚仮澶嶃€?- 缂撳瓨閿嚦灏戝寘鍚?commit_hash銆佹ā鍨嬬増鏈€佺壒寰佺増鏈€佹妧鏈拰鍙傛暟鎽樿锛涙ā鍨嬫垨鐗瑰緛鍙樺寲蹇呴』澶辨晥銆?- `.env` 浠呮彁渚涘嚭鍘傞粯璁わ紱鎶€鏈竻鍗曠敱娉ㄥ唽琛ㄧ粰鍑猴紝涓嶅湪鍓嶇鍐欐銆?
## 6. 鐘舵€佹寔涔呭寲

- 鎵归噺 run 鍚屾鍐欑粓鎬侊紝寮傛 kind=`explain` 鍐欎簲鎬侊紱鍚?kind 鏉′欢鏇存柊浜掓枼锛岄噸鍚仐鐣?running 缃?failed锛屽彲 retry/cancel銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紱job 鐧昏鎶€鏈€佷骇鐗╁拰 reason_code 缁熻銆?- 缂撳瓨涓嶆槸鍞竴缁撴灉瀛樺偍锛屾渶澶氫繚鐣?1024 椤硅繘绋嬪唴鎴愬姛缁撴灉锛涚紦瀛橀敭鍚疄闄呯壒寰佸唴瀹广€佹ā鍨嬫潈閲?checksum銆佺増鏈€佹妧鏈€佸弬鏁般€乼op_n 鍜屼唬鐮佹憳瑕併€傞噸鍚彧涓㈢紦瀛橈紝涓嶅奖鍝嶅凡浜や粯鏂囦欢銆?- 涓婁紶妯″瀷涓嶆斁鍏ュ湪绾挎敞鍐岃〃锛涙牎楠屽寘鍚庡湪鍙楅檺宸ヤ綔杩涚▼涓В閲娿€傚瓙杩涚▼浠?`-I -B` 鍚姩锛屽彲淇′緷璧栧姞杞藉畬鎴愬悗銆乸ickle 鍙嶅簭鍒楀寲涔嬪墠鏀剁揣锛歮acOS 鍙犲姞绯荤粺 sandbox-exec锛屾墍鏈夊钩鍙扮粺涓€鍚敤涓嶅彲鍗歌浇鐨?Python 瀹¤閽╁瓙锛岀櫧鍚嶅崟澶栫殑鏂囦欢璇诲彇/鍐欏叆銆佺綉缁溿€佹柊寤鸿繘绋嬩笌鍔ㄦ€佸簱鍔犺浇涓€寰嬫嫆缁濓紝鍐欏叆浠呭厑璁告湰娆′换鍔＄洰褰曪紱120 绉掑閽?90 绉?CPU锛圵indows 浠ュ閽熶笌浠诲姟缁堟绛変环绾︽潫锛?32MiB 杈撳嚭闄愬埗锛屽彇娑堢粓姝㈡暣涓繘绋嬬粍銆傚瓙杩涚▼杈撳嚭涓虹函 ASCII JSON 瑙勯伩 Windows GBK stdout锛涙棤绯荤粺娌欑鐨勫钩鍙颁笉鍐嶆嫆缁濇枃浠惰В閲婏紝浣嗙粷涓嶉€€鍥炵埗杩涚▼涓嶅彈闄?pickle銆傝秴鏃躲€佹棤鏁堣緭鍑哄拰涓嶆敮鎸佺粍鍚堝潎浜や粯 reason_code 琛屻€?- 鍗曟潯瑙ｉ噴鍙宸叉湁杈撳叆锛屽彲缂撳瓨浣嗕笉淇敼 prediction锛涙壒閲忔枃浠惰繍琛屼笉瑕佹眰鏁版嵁搴撳瓨鍦ㄣ€?
## 7. 楠屾敹

fixtures 涓?`backend/tests/test_explain_core.py`銆乣test_explain_run.py` 鍐呰仈鍚堟垚鐨?AI 鐢熸垚鏈鏍告暟鎹紝鍙劚绂?predict/localize 鏈嶅姟杩愯锛涗笉鍐掔О浜哄伐楠屾敹瀹屾垚銆?
- **姝ｅ父**锛氬彧涓婁紶妯″瀷鍖呬笌鐗瑰緛鏂囦欢銆佷笉鎻愪緵 predictions锛屽湪 SHAP 涓?LIME 涓嬪潎寰楀埌鍚屾瀯瑙ｉ噴锛屾帓搴忋€佹柟鍚戙€佸師濮嬪€间笌鐗堟湰瀹屾暣锛涘鎶€鏈暱琛ㄤ笌 manifest checksum 閫氳繃銆傚彟楠屽彲閫?predictions 鐨勭増鏈笌鑼冨洿鏍稿銆?- **杈圭晫**锛歵op_n 澶т簬鐗瑰緛鏁般€佺紦瀛樺懡涓?澶辨晥銆佹瘮杈冨紑鍏冲叧闂€侀儴鍒嗘彁浜や笉鏀寔鍧囬€愯璇存槑锛屾鐜囦笌鏍囩涓嶅彉銆?- **闈炴硶**锛氭湭鐭ユ妧鏈€佷笉鏀寔缁勫悎銆佺己鐗瑰緛琛屻€乧hecksum/鐗堟湰/鍒楀涓嶇銆佸叕寮忔敞鍏ュ潎杩斿洖 40001 鎴?搂3.7 reason_code 琛岋紝缁濅笉闈欓粯绌烘暟缁勩€?- 榛樿 XAI 閲嶅惎鎭㈠锛涘紓姝?job 閲嶅惎缃?failed锛汣LI/API 鍚?fixture 鏁板€间笌缁撴瀯涓€鑷淬€?
## 8. 杈圭晫

explain 閫氳繃 搂3.3 妯″瀷鍖呬笌 搂3.1/搂3.2 鐗瑰緛鏂囦欢鐙珛杩愯锛浡?.4 predict 鏂囦欢浠呬綔鍙€夋牳瀵癸紝骞跺悜 localization 鎻愪緵鍙€?搂3.7 鏂囦欢銆備緷璧栨槸 schema 涓庣増鏈吋瀹癸紝涓嶆槸涓婃父鏈嶅姟銆佹棦鏈夐娴嬫枃浠舵垨鏁版嵁搴撴暟鎹墠缃紱predict 涓嶅緱鍙嶅悜璋冪敤 explain銆?