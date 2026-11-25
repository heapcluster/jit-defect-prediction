# 棰勬祴缁撴灉瑙ｉ噴锛堝姛鑳?7锛?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
## 涓€鍙ヨ瘽姒傝堪

鐙珛鐨?XAI 宸ュ叿锛氶€氳繃瑙ｉ噴鍣ㄦ敞鍐岃〃涓烘寚瀹氭ā鍨嬪寘涓庤緭鍏ユ牱鏈敓鎴愯嚦灏?SHAP銆丩IME 涓ょ缁熶竴缁撴瀯瑙ｉ噴锛屼笉鏀寔鐨勭粍鍚堢敤 `reason_code` 琛屾槑纭氦浠樿€岄潪闈欓粯缂鸿銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

**璐熻矗**锛?
- 寤虹珛 XAI 瑙ｉ噴鍣ㄦ敞鍐岃〃涓庘€滄ā鍨嬫棌 脳 鎶€鏈€濆吋瀹圭煩闃碉紝涓€鏈熻嚦灏戝疄鐜板苟楠岃瘉 SHAP 鍜?LIME銆?- 鎺ユ敹妯″瀷鍖呭拰鐗瑰緛杈撳叆锛屾寜鎵€閫夋妧鏈笌鍙傛暟璁＄畻鐗瑰緛鍘熷€笺€佽础鐚€佹柟鍚戙€佹帓鍚嶅拰鐗堟湰淇℃伅銆?- 鎻愪緵缁熶竴瑙ｉ噴鏂囦欢銆佹妧鏈垏鎹€佺紦瀛樺拰鍙€夊鎶€鏈瘮杈冿紱鑰楁椂浠诲姟杩涘叆缁熶竴 job 鐢熷懡鍛ㄦ湡銆?- 瀵逛笉鏀寔鐨勬ā鍨嬫棌銆佽緭鍏ュ舰鎬佹垨鎶€鏈繑鍥炴槑纭師鍥犵爜涓庤鏄庯紝淇濊瘉姣忎釜璇锋眰鏍锋湰閮芥湁缁撴灉鎴栧師鍥犺褰曘€?
**涓嶈礋璐?*锛?
- 璁粌銆侀娴嬨€佷慨鏀规鐜囨垨鏍囩銆佽绾у畾浣嶃€佷慨澶嶅缓璁拰 CI 闃绘柇銆?- 鎶婅В閲婇檺鍒跺湪 expert 绾胯€屼笉缁欏吋瀹圭煩闃碉紝鎴栧湪棰勬祴鏈嶅姟鍐呴儴闅愬紡鎵ц瑙ｉ噴銆?- 璁╁叿浣?SHAP/LIME 瀹炵幇鎴愪负 localization 鐨勭洿鎺ヤ緷璧栥€?
## 2 鐙珛杩愯鍏ュ彛

```bash
python -m app.cli explain techniques
python -m app.cli explain run \
  --model-package model_package.zip --input clean_dataset.csv \
  --technique shap --params shap.json --out ./out
python -m app.cli explain run \
  --model-package model_package.zip --input clean_dataset.csv \
  --technique lime --compare shap --out ./out
```

| 鍏ュ彛 | 鍛戒护 / 绔偣 | 濂戠害 |
|---|---|---|
| CLI | `explain techniques/run` | 妯″瀷鍖呫€佽緭鍏ユ枃浠跺拰鎶€鏈悕鍗冲彲杩愯锛屼笌 API 鍏辩敤瑙ｉ噴鍣ㄦ敞鍐岃〃 |
| 娉ㄥ唽琛?API | `GET /api/explain/techniques` | 杩斿洖鎶€鏈€佸弬鏁?schema銆佸吋瀹圭煩闃靛拰榛樿鎶€鏈?|
| 鍗曟潯 API | `POST /api/explain` | 璇︽儏缂栨帓鍚屾瑙ｉ噴鍗曟潯鎻愪氦锛涘彧璇诲凡瀛樿緭鍏ヤ笌宸插姞杞芥ā鍨嬶紝涓嶄骇浜ゆ崲鏂囦欢 |
| 浠诲姟 API | `POST /api/explain/run` | multipart 涓婁紶妯″瀷鍖呬笌杈撳叆鏂囦欢锛屽崟鏍锋湰鎴栨壒閲忓潎杩斿洖鍙窡韪殑 `job_id` |
| 浠诲姟绠＄悊 | `GET /api/jobs/{id}`銆乣POST /api/jobs/{id}/retry\|cancel` | `kind=explain` 鐨勪簲鎬併€佽繘搴︺€佹棩蹇椼€佸彇娑堜笌閲嶈瘯 |
| 涓嬭浇 | `GET /api/explain/outputs/{job_id}/{name}` | 涓嬭浇 explanations銆佹瘮杈冪粨鏋滀笌 manifest |

鎵€鏈?HTTP 绔偣锛堝惈涓嬭浇锛夊繀椤讳娇鐢?`X-API-Key`銆傛彁浜よ鎯呴渶瑕佽В閲婃椂锛岀敱璇︽儏缂栨帓骞惰璋冪敤 predict 涓庢湰妯″潡锛沺redict 鍝嶅簲涓嶅惈 explanation锛宲redict 鏈嶅姟涓嶅緱璋冪敤鏈ā鍧椼€?
## 3 杈撳叆濂戠害

- 妯″瀷杈撳叆閬靛惊 [`../file-contracts.md`](../file-contracts.md) 搂3.3 `model_package.zip`锛屽姞杞藉墠鏍￠獙 checksum銆佹ā鍨嬪厓淇℃伅銆佺壒寰侀『搴忓拰鍒楀銆?- 寰呰В閲婃彁浜ょ敱 搂3.2 `clean_dataset.csv` 鎴?搂3.1 `collected_commits.csv` 鎻愪緵锛涗袱琛ㄤ笉鍚?14 缁?/ `is_test`锛宔xpert 鐨勭壒寰佹寜妯″瀷鍖?`feature_order.txt` 浠庣粦瀹氫粨搴撶幇绠楋紝semantic 鐢ㄩ璁＄畻鍚戦噺鎴栧喕缁撳ご鍦ㄧ嚎缂栫爜銆傛ā鍨嬪寘涓庢彁浜よ〃灏辨槸涓昏緭鍏ャ€偮?.4 `predictions.csv` 浠呬负鍙€夌増鏈笌鑼冨洿鏍稿杈撳叆锛屼笉鎻愪緵瀹冧篃蹇呴』鑳藉畬鎴愯В閲婏紝涓嶈姹?predict 鏈嶅姟鍦ㄧ嚎銆?- 鏈ā鍧楅厤缃寘鎷?`technique`銆佹妧鏈笓灞?`params`銆乣feature_version`銆乣top_n`銆乣compare_techniques[]` 鍜岀紦瀛樼瓥鐣ワ紱缂虹渷鎶€鏈鍙?`user_config.default_xai`銆?- 娉ㄥ唽琛ㄧ粨鍚堢櫥璁扮畻娉曟爣璇嗕笌瀹為檯宸插姞杞芥ā鍨嬭瘑鍒?tree/linear/tabular/text锛歋HAP 鏀寔鏍?绾挎€э紝LIME 鏀寔琛ㄦ牸姒傜巼妯″瀷锛屾枃鏈垨缂哄皯杈撳叆褰㈡€佺殑妯″瀷鏄庣‘缁欏師鍥犮€傜畻娉曞簱鐨勭矖绮掑害 family 涓嶅啋鍏呭叿浣撹В閲婂櫒閫傞厤璇佹嵁锛涗笉浼氭倓鎮勬崲鎶€鏈€?- 杈撳叆缂哄皯妯″瀷鎵€闇€鐗瑰緛銆佺増鏈笉绗︽垨鍒楀涓嶇鏃舵槑纭け璐ワ紱涓嶈兘閫氳繃濉?0銆佹埅鏂垨閲嶆帓鍒楃寽娴嬪吋瀹广€?
## 4 杈撳嚭濂戠害

| 杈撳嚭 | 鏂囦欢涓庡唴瀹?|
|---|---|
| 缁熶竴瑙ｉ噴 | `explain_explanations_<job_id>.csv`锛屽彲閫?`.xlsx`锛涢€愯涓ユ牸閬靛惊 搂3.7 explanations schema |
| 鎶€鏈瘮杈?| `explain_comparison_<job_id>.json`锛氬悓涓€杈撳叆鍦ㄤ笉鍚屾妧鏈笅鐨勭粨鏋滃紩鐢ㄣ€佸弬鏁板拰鐘舵€侊紝渚涘苟鎺掑睍绀?|
| 杩愯鎽樿 | `explain_summary_<job_id>.json`锛氭牱鏈暟銆佹垚鍔熸暟銆佷笉鏀寔鏁般€佺紦瀛樺懡涓€佹妧鏈笌鐗堟湰缁熻 |
| manifest | 姣忎釜浜х墿浼村悓鍚?`explain_<artifact>_<job_id>.manifest.json`锛屾弧瓒?搂3.9锛岃褰曟ā鍨?杈撳叆 checksum銆佹妧鏈弬鏁颁笌浠ｇ爜鐗堟湰 |

鍛藉悕缁熶竴涓?`<module>_<artifact>_<job_id>.<ext>`銆備笉鏀寔鐨勭粍鍚堝繀椤绘寜 搂3.7 浜?`reason_code` 琛岋細feature 涓?contribution 鐣欑┖銆乺eason_code 闈炵┖锛屽苟闄勫彲灞曠ず璇存槑锛涗笉寰楅潤榛樼己琛屾垨鍙粰绌虹櫧鍖哄煙銆傛墍鏈夋敮鎸佺殑鎶€鏈叡鐢ㄥ悓涓€缁撴瀯銆佹帓搴忓拰鏂瑰悜璇箟锛岃В閲婅繃绋嬪彧璇伙紝涓嶆敼鍙橀娴嬬粨鏋溿€?
## 5 鍙厤缃」

| 閰嶇疆 | 鏉ユ簮 | 榛樿 / 绾︽潫 |
|---|---|---|
| `default_xai` | `user_config` 鍏ㄥ眬閿?| 榛樿 `shap`锛岄』灞炰簬娉ㄥ唽琛紝閲嶅惎鎭㈠ |
| SHAP/LIME 鍙傛暟 | run 閰嶇疆 + 鎶€鏈?schema | 鑳屾櫙闆嗐€侀噰鏍锋暟绛夋寜娉ㄥ唽琛ㄦ牎楠屽苟鍏ュ揩鐓?|
| `explain.cache_ttl` | `user_config` 鍛藉悕绌洪棿閿?| 闈炶礋鏃堕暱锛涙ā鍨?鐗瑰緛/鎶€鏈弬鏁板彉鍖栦娇缂撳瓨澶辨晥 |
| `explain.compare_enabled` | `user_config` 鍛藉悕绌洪棿閿?| HTTP 澶氭妧鏈瘮杈冮粯璁?false锛屾樉寮忓紑鍚紱CLI 鐨?--compare 鏄湰娆＄嫭绔嬭繍琛岀殑鏄庣‘閫夋嫨 |
| 灞曠ず鐗瑰緛鏁伴噺 | run `top_n` 鎴?`page_prefs` | 榛樿 8锛屽彧褰卞搷灞曠ず锛屼笉鎴柇浜や粯鏂囦欢涓殑鍘熷洜琛?|

## 6 鐘舵€佹寔涔呭寲

- 瑙ｉ噴鍒涘缓 `job.kind=explain`锛屼娇鐢ㄧ粺涓€浜旀€佸苟鎸佷箙鍖栨妧鏈€佸弬鏁般€佽緭鍏ュ紩鐢ㄣ€佽繘搴﹀拰閿欒鏃ュ織锛涘悓 kind 浜掓枼锛岄噸鍚仐鐣?running 缃?failed銆?- 杈撳嚭钀界洏 `temp/outputs/<job_id>/`锛岀洰褰曟暣浣撳姞鍏?gitignore锛涘け璐ユ垨涓嶆敮鎸佸潎淇濈暀鍙瘖鏂粨鏋滐紝涓嶆妸閮ㄥ垎绌烘枃浠舵爣涓哄畬鏁存垚鍔熴€?- 缂撳瓨閿嚦灏戝寘鍚緭鍏ユ牱鏈€佹ā鍨嬪寘 checksum銆佺壒寰佺増鏈€佹妧鏈拰鍙傛暟锛涘懡涓紦瀛樹笉閲嶅璁＄畻锛岀増鏈彉鍖栦笉寰楄鍙栨棫瑙ｉ噴銆?- `default_xai`銆乣explain.cache_ttl` 鍜?`explain.compare_enabled` 钀?`user_config` 骞堕噸鍚仮澶嶏紱姣忔杩愯鍥哄寲娉ㄥ唽琛?鍏煎鐭╅樀鐗堟湰銆佹ā鍨嬩笌鐗瑰緛鐗堟湰銆?- LIME 0.2.0.1 宸查攣鐗堜簬鍞竴 environment.yml锛涘浐瀹?seed/num_samples/kernel_width 鍙噸绠椼€傜嚎鎬?SHAP 涓?log_odds锛屾爲涓?tree_raw锛孡IME 涓?local_probability_coefficient锛涗繚鐣欑鍙枫€乺ank銆乺aw_value锛屾暟鍊间笉鑳借法灏哄害鐩存帴鐩稿姞銆傛棤鐪熷疄鑳屾櫙鏃舵槑纭褰曢浂/鍚堟垚鍙傝€冦€?- 妯″瀷鍖呰В閲婂湪璺ㄥ钩鍙板彈闄愬瓙杩涚▼鍐呮墽琛岋紝涓嶅姞鍏ュ湪绾挎敞鍐岃〃锛沵acOS 鐢ㄧ郴缁?sandbox-exec锛學indows 涓庡叾瀹冨钩鍙扮敤涓嶅彲鍗歌浇鐨?Python 瀹¤閽╁瓙闄愬埗鏂囦欢璇诲啓/缃戠粶/瀛愯繘绋?鍔ㄦ€佸簱锛宲ickle 鍙湪鏀剁揣鍚庣殑瀛愯繘绋嬪唴鍙嶅簭鍒楀寲锛岀埗杩涚▼姘镐笉鎵ц鏈彈鏉冮檺琛￠噺鐨勬潈閲嶃€傛墽琛屾湁 120 绉掑閽?90 绉?CPU锛圵indows 绛変环澧欓挓绾︽潫锛?32MiB 杈撳嚭涓婇檺锛岃秴鏃躲€佹棤鏁堣緭鍑哄拰涓嶆敮鎸侀兘浜や粯鍘熷洜琛屻€?
## 7 涓庡叾浠栨ā鍧楄竟鐣?
- 涓绘彙鎵嬫槸 train 鐨?搂3.3 妯″瀷鍖呬笌 clean/collect 鐨?搂3.1/搂3.2 鐗瑰緛鏂囦欢锛沺redict 鐨?搂3.4 棰勬祴鏂囦欢鍙綔鍙€夋牳瀵广€備换浣曚笂娓告湇鍔℃垨鏃㈡湁棰勬祴鏂囦欢閮戒笉鏄В閲婅繍琛屽墠鎻愩€?- localization 鍙秷璐?搂3.7 缁熶竴瑙ｉ噴锛屼笉鐩存帴瀹炰緥鍖?SHAP/LIME锛涙湰妯″潡涓嶈皟鐢?localization銆?- 璇︽儏椤靛彲浠ュ苟琛岃皟鐢?predict 鍜?explain锛屼絾杩欐槸澶栭儴灞曠ず缂栨帓锛沺redict 鍐呴儴绂佹瑙﹀彂瑙ｉ噴锛岃В閲婂け璐ヤ篃涓嶅奖鍝嶉娴嬪搷搴斻€?- 椤甸潰灞備綔涓衡懁棰勬祴鐨勫瓙椤碉紝鍙粠棰勬祴缁撴灉/鎻愪氦璇︽儏甯﹀叆 commit/model锛涙ā鍧楁湰韬笉渚濊禆鈶ゅ湪绾匡紝浠嶅彲鐙珛涓婁紶妯″瀷鍖呬笌鐗瑰緛鏂囦欢杩愯銆?- `algorithm.family` 涓?`user_config` 灞炰簬閰嶇疆鍏冩暟鎹紱鐙珛 CLI 鍙娇鐢ㄧ浉鍚岀櫥璁颁俊鎭殑蹇収瀹屾垚鍏煎鎬ф牎楠屻€?
## 8 楠屾敹鏍囧噯

fixtures 涓烘祴璇曞唴鑱斿悎鎴愮殑 AI 鐢熸垚鏈鏍告ā鍨?鐗瑰緛/鍏煎缁勫悎锛屽惈姝ｅ父銆佽竟鐣屻€侀潪娉曚笁绫伙紱鍦ㄦ棤 predict 鏈嶅姟銆佺┖涓氬姟搴撶幆澧冧笅锛孋LI/API 鍧囧彲鐙珛鐢熸垚瑙ｉ噴鏂囦欢銆?
- 鍚屼竴鎻愪氦鍦ㄥ悓涓€鍏煎妯″瀷涓婂垎鍒繍琛?SHAP 涓?LIME锛屽潎鏈夌粺涓€缁撴瀯銆佸彲鎺掑簭涓斿惈妯″瀷/鐗瑰緛鐗堟湰鐨勭粨鏋滐紱鎶€鏈垏鎹㈠拰骞舵帓姣旇緝鐢熸晥銆?- 鑷冲皯涓€涓笉鏀寔鐨勬ā鍨嬩笌鎶€鏈粍鍚堜骇鐢?搂3.7 `reason_code` 琛岋紝feature/contribution 鐣欑┖涓旇姹傛牱鏈笉缂哄け锛沺redict 椤甸潰涓嶅彈褰卞搷銆?- checksum 閿欒銆佺壒寰佺己澶便€佸垪瀹戒笉绗︺€佹湭鐭ユ妧鏈拰鍙傛暟瓒婄晫鍧囨槑纭け璐ワ紝涓嶄吉閫犺础鐚紱杈撳叆鏂囦欢涓?manifest 鏍￠獙瀹屾暣銆?- 榛樿鎶€鏈€佺紦瀛樺拰姣旇緝閰嶇疆閲嶅惎鍚庝繚鎸侊紱缂撳瓨鍛戒腑涓嶉噸澶嶈绠楋紝妯″瀷鎴栫壒寰佺増鏈彉鍖栧悗鏃х紦瀛樹笉鍙懡涓€?- 鎵挎帴 TODO/07锛氭敞鍐岃〃銆佸吋瀹圭煩闃点€佺粺涓€缁撴瀯銆佺紦瀛樸€佸け璐ュ師鍥犮€佷富瑕佹ā鍨嬫棌鍜屾妧鏈垏鎹㈠潎鏈夋祴璇曪紱浜旀€併€佷簰鏂ャ€佸彇娑堛€侀噸璇曞拰閲嶅惎涓柇閫氳繃銆?