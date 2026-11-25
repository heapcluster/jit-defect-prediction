# 妯″瀷棰勬祴锛堝姛鑳?5锛?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
## 涓€鍙ヨ瘽姒傝堪

鐙珛鐨勯娴嬪伐鍏凤細鍔犺浇鎸囧畾 `model_package.zip`锛屽鍗曟彁浜ゃ€佷笂浼犳枃浠舵垨鍙€夋暟鎹泦鎵ц椋庨櫓棰勬祴锛屼氦浠樼粺涓€ `predictions.csv`锛屽苟鎻愪緵 load/unload/reload/default 鍥涢」妯″瀷绠＄悊鎿嶄綔銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

**璐熻矗**锛?
- 鏍￠獙骞跺姞杞芥ā鍨嬪寘锛屾瀯閫犱笌妯″瀷绾垮尮閰嶇殑鐗瑰緛锛岃緭鍑洪闄╂鐜囥€佷簩鍒嗙被鏍囩銆侀闄╃瓑绾у拰瀹屾暣鐗堟湰淇℃伅銆?- 鍗曟潯鍚屾棰勬祴锛屼互鍙婃壒閲?鏂囦欢/鍙€夋暟鎹泦鐨勫紓姝ラ娴嬶紱鎵归噺浠诲姟鎻愪緵杩涘害銆佹垚鍔熷け璐ヨ鏁般€侀噸璇曞拰涓嬭浇銆?- 鎻愪緵妯″瀷鍔犺浇銆佸嵏杞姐€侀噸杞姐€佽榛樿鍥涗釜鐙珛鎿嶄綔锛屾煡璇㈠彲鐢ㄣ€佸姞杞戒腑銆佸姞杞藉け璐ャ€佸凡鍗歌浇绛夌姸鎬併€?- 绠＄悊鎵归噺澶у皬銆佺紦瀛樹笌閲嶈瘯閰嶇疆锛涙ā鍨嬬敱姣忔杩愯鏄惧紡閫夋嫨锛涙敮鎸侀娴嬪箓绛夈€佽繃鏈熸爣璁板拰鏄惧紡閲嶆柊璁＄畻銆?
**涓嶈礋璐?*锛?
- 璁粌鎴栬皟鍙傘€佹€ц兘璇勪及銆乆AI 瑙ｉ噴銆佽绾у畾浣嶃€佷慨澶嶅缓璁拰鏁版嵁閲囬泦銆?- 鍦?predict 鏈嶅姟鍐呰皟鐢ㄨВ閲婃垨瀹氫綅锛涙彁浜よ鎯呭彧浣滀负澶栭儴缂栨帓鏂瑰苟琛岃皟鐢ㄥ悇鐙珛宸ュ叿銆?- 鐢ㄥ墠绔父閲忔垨妯″瀷鐗堟湰鍙烽殣寮忓喅瀹氭ā鍨嬶紝鎴栨妸棰勬祴姒傜巼鏀瑰啓鎴愮粡杩囬槇鍊煎鐞嗙殑鏁板€笺€?
## 2 鐙珛杩愯鍏ュ彛

```bash
python -m app.cli predict run \
  --model-package model_package.zip --input clean_dataset.csv \
  --threshold 0.5 --out ./out
python -m app.cli predict one --commit <hash> --model rf_v1
python -m app.cli models load --package model_package.zip
python -m app.cli models set-selection --name rf_v1
```

| 鍏ュ彛 | 鍛戒护 / 绔偣 | 濂戠害 |
|---|---|---|
| CLI | `predict run/one`銆乣models load/unload/reload/set-selection/status` | 鏂囦欢涓庢ā鍨嬪寘鍗冲彲鎵归噺杩愯锛涘崟鏉″拰妯″瀷绠＄悊鍏辩敤鍚屼竴瀹炵幇 |
| 鎵归噺 API | `POST /api/predict/run` | multipart 涓婁紶妯″瀷鍖呬笌杈撳叆鏂囦欢锛屾垨鎸囧畾宸茬櫥璁版ā鍨嬶紱杩斿洖 `kind=predict_batch` 鐨?`job_id` |
| 鍗曟潯 API | `POST /api/predict` | 鎺ユ敹 `commit_hash` 涓庡繀濉?`model_name`锛堜笉璁鹃粯璁ゆā鍨嬶級锛屽悓姝ヨ繑鍥烇紝渚涜鎯呯紪鎺掍繚鐣?|
| 妯″瀷绠＄悊 | `GET /api/models/status`锛沗POST /api/models/{name}/load\|unload\|reload`锛沗PUT /api/models/default` | 鍥涢」绠＄悊鍔ㄤ綔鏄惧紡瑙﹀彂锛屼笌椤甸潰鍒锋柊鏃犲叧 |
| 浠诲姟绠＄悊 | `GET /api/jobs/{id}`銆乣POST /api/jobs/{id}/retry\|cancel` | 鎵归噺杩涘害銆佹棩蹇椼€侀噸璇曞拰鍙栨秷 |
| 涓嬭浇 | `GET /api/predict/outputs/{job_id}/{name}` | 涓嬭浇 predictions銆佺粺璁′笌 manifest |

鎵€鏈?HTTP 绔偣锛堝惈妯″瀷绠＄悊涓庤緭鍑轰笅杞斤級蹇呴』浣跨敤 `X-API-Key`銆俽un 鐨勫彲閫?`dataset_id` 鍙€夋嫨宸插鍏ョ殑杈撳叆鏂囦欢锛涗笂浼犳ā鍨嬪寘鍜屾暟鎹枃浠舵椂涓嶄緷璧栬閫夐」銆?
## 3 杈撳叆濂戠害

- 妯″瀷杈撳叆閬靛惊 [`../file-contracts.md`](../file-contracts.md) 搂3.3 `model_package.zip`锛屽姞杞藉墠鏍￠獙 `checksum.sha256`銆乣model_meta.json`銆乣feature_order.txt` 鍜岀壒寰佸垪瀹姐€傛潈閲嶆崯鍧忋€佺増鏈笉鍏煎鎴栧垪瀹戒笉绗﹀繀椤绘嫆缁濓紝涓嶇寽娴嬬壒寰併€?- 鎵归噺涓昏緭鍏ラ伒寰?搂3.2 `clean_dataset.csv`锛岃瘎浼板満鏅敤 搂3.3 `train_testset`锛堟瘡琛屽甫鐪熸爣绛撅級锛涗笓瀹剁嚎涔熷彲鎺ユ敹 搂3.1 `collected_commits.csv`銆俿emantic 绾挎墍闇€ 768 缁村悜閲忕敱鍐荤粨澶?CodeBERT 棰勮绠楁垨鍦ㄧ嚎缂栫爜锛岄』涓庡寘鍐呯壒寰佺増鏈竴鑷达紝缂鸿緭鍏ユ椂鏄庣‘鎶ラ敊锛屼笉缂栭€犲悜閲忋€?- **璇勪及鍦烘櫙**锛氳緭鍏?`train_testset` 鏃讹紝鍏?`is_bug_inducing` 鐪熸爣绛?MUST 鍘熸牱閫忎紶杩?搂3.4 `predictions.csv`锛屼緵鏉垮潡 鈶?璁＄畻鎬ц兘锛涜緭鍏ョ己鐪熸爣绛撅紙濡傞娴嬫柊鎻愪氦锛夋椂鍏佽鏍囩鍒楃┖锛屼絾璇ョ粨鏋滀笉杩涘叆鎬ц兘璇勪及銆?- run 閰嶇疆鍖呭惈妯″瀷鏍囪瘑鎴栨ā鍨嬪寘銆乣decision_threshold`銆佺瓫閫夋潯浠躲€乣batch_size`銆乣force_recompute` 鍜岃緭鍑烘牸寮忥紱鍙€?`dataset_id` 浠呬綔渚垮埄杈撳叆銆?- 鍗曟潯 `POST /api/predict` 鐨?`commit_hash` 涓?40 浣?hex锛涘浣欏瓧娈垫嫆缁濄€傝鎯呭彲閫夋嫨鈥滄部鐢ㄥ簱涓粨鏋溾€濇垨鈥滅珛鍗抽噸鏂拌绠椻€濓紝鍚庤€呮樉寮忚缃噸绠楄涔夛紝涓嶅奖鍝嶆壒閲忔枃浠跺伐鍏枫€?- 妯″瀷蹇呴』鐢辨湰娆¤繍琛屾樉寮忔寚瀹?`model_name` 鎴栦笂浼?`model_package.zip`锛涙湭鎸囧畾杩斿洖 40001锛屼笉璁鹃粯璁ゅ€笺€佷笉鍋氱増鏈簭鍥為€€銆?
## 4 杈撳嚭濂戠害

| 杈撳嚭 | 鏂囦欢 / 鍝嶅簲 |
|---|---|
| 鎵归噺棰勬祴 | `predict_predictions_<job_id>.csv`锛屽彲閫?`.xlsx`锛泂chema 涓ユ牸閬靛惊 搂3.4锛屾鐜囦繚鐣?5 浣嶅皬鏁帮紝棰勬祴鏍囩鎸夋湰娆￠槇鍊肩敓鎴愶紱璇勪及鍦烘櫙鐨?`is_bug_inducing` 鐪熸爣绛惧師鏍烽€忎紶鑷?`train_testset` |
| 鎵归噺缁熻 | `predict_summary_<job_id>.json`锛氳緭鍏ユ暟銆佹垚鍔?澶辫触鏁般€佸疄闄呮ā鍨嬩笌鐗堟湰銆侀槇鍊笺€佺紦瀛樺懡涓€侀噸璇曞拰杩囨湡缁撴灉缁熻 |
| 鍗曟潯鍝嶅簲 | 杩斿洖鎻愪氦銆佸疄闄呮ā鍨嬨€侀闄╂鐜囥€侀娴嬫爣绛俱€侀闄╃瓑绾с€佸喅绛栭槇鍊笺€佹ā鍨?鐗瑰緛鐗堟湰銆侀娴嬫椂闂翠笌 stale 鏍囪 |
| 妯″瀷鐘舵€?| 杩斿洖宸ヤ欢鍙敤鐘舵€併€佽繍琛屾椂鍔犺浇鐘舵€併€佸綋鍓嶉€夋嫨涓庢渶杩戝姞杞介敊璇?|
| manifest | 姣忎釜鎵归噺浜х墿浼村悓鍚?`predict_<artifact>_<job_id>.manifest.json`锛屾弧瓒?搂3.9锛岃褰曟ā鍨嬪寘涓庤緭鍏?checksum銆侀厤缃拰浠ｇ爜鐗堟湰 |

鎵€鏈夋枃浠堕伒寰?`<module>_<artifact>_<job_id>.<ext>`銆俙risk_score` 濮嬬粓淇濇寔妯″瀷姒傜巼锛沗decision_threshold` 鍙奖鍝嶆爣绛撅紝`risk_high_threshold/risk_mid_threshold` 鍙奖鍝嶅睍绀虹瓑绾с€俻redict 鍝嶅簲涓庢枃浠跺潎涓嶅惈 explanation锛屼篃涓嶅洜瑙ｉ噴鎴栧畾浣嶄笉鍙敤鑰屽け璐ャ€?
## 5 鍙厤缃」

| 閰嶇疆 | 鏉ユ簮 | 榛樿 / 绾︽潫 |
|---|---|---|
| `decision_threshold` | `user_config` 鍏ㄥ眬閿垨 run 瑕嗙洊 | 榛樿 0.5锛屽紑鍖洪棿 (0,1) |
| `risk_high_threshold` / `risk_mid_threshold` | `user_config` 鍏ㄥ眬閿?| 榛樿 0.5 / 0.2锛宮id < high |
| `predict.batch_size` | `user_config` 鍛藉悕绌洪棿閿?| 姝ｆ暣鏁帮紝鎺у埗鎵归噺鍒嗙墖锛岄噸鍚仮澶?|
| `predict.cache_ttl` | `user_config` 鍛藉悕绌洪棿閿?| 闈炶礋鏃堕暱锛涙ā鍨?鐗瑰緛鐗堟湰鍙樺寲浣跨紦瀛樺け鏁?|
| `predict.retry_max` | `user_config` 鍛藉悕绌洪棿閿?| 闈炶礋鏁存暟锛岄檺鍒朵换鍔￠噸璇?|
| 鑷姩鍔犺浇绛栫暐 | train 鐨?`auto_load` + 鏈ā鍧楁樉寮忕鐞?| 榛樿鎵嬪姩鎴栦竴閿姞杞斤紱涓嶄緷璧栭〉闈㈠埛鏂?|
| `default_dataset` | `user_config` 鍏ㄥ眬閿?| 浠呬綔 run 涓嬫媺榛樿閫夐」 |

## 6 鐘舵€佹寔涔呭寲

- 鎵归噺棰勬祴鍐?`job.kind=predict_batch`锛屼娇鐢ㄧ粺涓€浜旀€佸苟鎸佷箙鍖栧叆鍙傘€佽繘搴︺€侀敊璇棩蹇楀拰杈撳嚭寮曠敤锛涘悓 kind 浜掓枼锛岄噸鍚仐鐣?running 缃?failed銆?- 杈撳嚭钀界洏 `temp/outputs/<job_id>/`锛岀洰褰曟暣浣撳姞鍏?gitignore锛涗换鍔￠噸璇曟部鐢ㄩ厤缃揩鐓у拰宸叉寔涔呭寲杩涘害锛屼笉閲嶅宸插畬鎴愮殑骞傜瓑缁撴灉銆?- 鍙€夊鍏?storage 鍚庯紝`prediction` 鎸?`(commit_hash, model_name)` 骞傜瓑 upsert锛涙ā鍨嬫垨鐗瑰緛鐗堟湰鍙樺寲鍙皢鏃х粨鏋滄爣璁?stale锛屾枃浠舵湰韬粛淇濈暀鍘熺増鏈簨瀹炪€?- 妯″瀷鍔犺浇澶辫触淇濈暀鍘熷洜骞剁淮鎸佷笂涓€涓凡鍔犺浇妯″瀷锛屼笉鑷姩鍒囨崲鍒板叾浠栨ā鍨嬶紱鏂版ā鍨嬮€氳繃鏄惧紡鎿嶄綔鎴?train 瀹屾垚閫氱煡鍔犺浇锛屾棤闇€閲嶅惎銆傛ā鍨嬮噸杞戒笌鏁版嵁閲囬泦鏄笉鍚屾搷浣溿€?- `predict.*` 钀?`user_config`锛岄噸鍚仮澶嶏紱姣忔杩愯璁板綍妯″瀷鍖?checksum銆佺増鏈€侀槇鍊煎拰缂撳瓨閰嶇疆锛岀‘淇濈粨鏋滃彲杩芥函銆?
## 7 涓庡叾浠栨ā鍧楄竟鐣?
- 涓?train 閫氳繃 搂3.3 妯″瀷鍖呬笌 `train_testset` 鍏煎锛氳瘎浼板満鏅敤璁粌鍒囧嚭鐨勬祴璇曢泦棰勬祴锛涗笌 clean/collect 浠呴€氳繃 搂3.1/搂3.2 鏁版嵁鏂囦欢鍏煎銆備笂娓告湇鍔′笉鍦ㄥ満涔熷彲瀹屾垚鎵归噺棰勬祴銆?- evaluate 鍙帴鏀?搂3.4 鏂囦欢锛堥』鍚€忎紶鐨勭湡鏍囩锛夛紱explain/localization 鍙寜鍚勮嚜濂戠害浣跨敤棰勬祴鏂囦欢锛屼絾 predict 涓嶅弽鍚戣皟鐢ㄥ畠浠€?- 鎻愪氦璇︽儏闇€瑕佽В閲婃椂锛岀敱璇︽儏缂栨帓骞惰璋冪敤 predict 涓?explain锛涜В閲婂け璐ヤ笉鏀瑰啓棰勬祴鍝嶅簲銆?- 椤甸潰灞傚彲浠庨娴嬬粨鏋?椋庨櫓鍒楄〃/鎻愪氦璇︽儏璺宠浆鈶﹁В閲婁笌鈶у畾浣嶅瓙椤碉紱杩欐槸鍏ュ彛缂栨帓锛宲redict 涓嶅弽鍚戣皟鐢ㄥ畠浠紝鈶︹懅浠嶅彲鐙珛杩愯銆?
> W8 宸茬Щ闄?prediction 鍝嶅簲鐨?explanation 涓庨娴嬫湇鍔″唴閮?SHAP 璋冪敤锛岃鎯呴€氳繃 `/api/explain` 鐙珛缂栨帓锛沠eatures/summary 缁х画渚涜鎯呭睍绀恒€俻rediction 宸茶惤 `model_version / feature_version` 鍙┖鍒楋紝鍗曟潯娌跨敤搴撲腑缁撴灉鎸夎鍐呯増鏈笌褰撳墠妯″瀷/鐗瑰緛鐗堟湰瀵规瘮杩斿洖鐪熷疄 stale锛堝巻鍙?NULL 鐗堟湰瑙嗕负杩囨湡锛夛紝force_recompute 閲嶇畻鍒锋柊銆傛壒閲忔敮鎸?expert / semantic 涓ょ嚎锛堢壒寰佽〃 + precomputed/鍦ㄧ嚎缂栫爜鍚戦噺锛沗fused` / `e2e` 宸茬爫鎺夛級銆侰LI 涓?`python -m app.cli predict run/one`銆乣models load/unload/reload/set-selection/status`銆?- storage 鍙礋璐ｅ彲閫夊睍绀哄鍏ュ拰閰嶇疆/浠诲姟鎸佷箙鍖栵紱涓嶅鍏ュ簱涔熻兘涓嬭浇銆佸楠屽拰浜や粯鍏ㄩ儴棰勬祴鏂囦欢銆?
## 8 楠屾敹鏍囧噯

fixtures 浣嶄簬 `tests/fixtures/files/predict/`锛屽惈姝ｅ父銆佽竟鐣屻€侀潪娉曚笁绫绘ā鍨嬪寘鍜岃緭鍏ユ枃浠讹紱鍦ㄦ棤璁粌鏈嶅姟銆佹棤瑙ｉ噴鏈嶅姟涓斿簱绌虹殑鎯呭喌涓嬶紝CLI/API 鍧囧彲鐙珛浜у嚭 搂3.4 鏂囦欢銆?
- 鍗曟潯鍚屾杩斿洖姒傜巼銆佹爣绛俱€侀槇鍊间笌鐗堟湰锛涙壒閲忓彲閫夋嫨妯″瀷鍜岃緭鍏ユ枃浠讹紝缁撴灉鍙笅杞藉苟鍙€夊鍏ユ煡璇紝閲嶅鎵ц鏃犻噸澶嶅簱璁板綍銆?- load/unload/reload/selection 鍥涙搷浣滃垎鍒敓鏁堬紱褰撳墠閫夋嫨鍙敤浜庨〉闈㈠洖鏄俱€侀噸鍚悗鎭㈠锛屼笉鍙備笌杩愯鍏ュ彛鐨勮嚜鍔ㄥ～鍏呫€?- checksum 閿欒銆佹潈閲嶇己澶便€佺壒寰佸垪涓嶇銆佺┖杈撳叆鍧囨湁鏄庣‘閿欒锛涘姞杞藉け璐ュ洖閫€涓嶄腑鏂凡鏈夊彲鐢ㄦā鍨嬶紝妯″瀷閲嶈浇涓嶈Е鍙戞暟鎹噰闆嗐€?- 鏂拌缁冩ā鍨嬪彲鑷姩鎴栦竴閿姞杞斤紝鏃犻渶閲嶅惎锛涙ā鍨?鐗瑰緛鐗堟湰鍙樺寲鑳芥爣璁?stale锛屸€滄部鐢ㄥ簱涓粨鏋溾€濆拰鈥滅珛鍗抽噸鏂拌绠椻€濊涔夋竻鏅般€?- 鍝嶅簲涓庤緭鍑轰笉鍚?explanation锛涜嚜鍔ㄥ寲渚濊禆鏂█璇佹槑 predict 鏈嶅姟娌℃湁璋冪敤 explain/localization锛岃В閲婂け璐ヤ笉褰卞搷棰勬祴銆?- 鎵挎帴 TODO/05锛氬崟鏉°€佹壒閲忋€佹暟鎹泦棰勬祴銆佹ā鍨嬬鐞嗐€佽嚜鍔ㄥ姞杞姐€佸箓绛夈€佽繃鏈熼噸绠椾笌缁撴灉瀵煎嚭鍧囨湁娴嬭瘯锛沗predict.*` 閰嶇疆銆佷簲鎬併€佷簰鏂ュ拰閲嶅惎鎭㈠閫氳繃銆?