# 閰嶇疆涓績 API锛坈onfig锛?
涓€鍙ヨ瘽锛氫互 user_config 涓哄敮涓€杩愯鏃堕厤缃簮锛屾彁渚涘叏灞€閿拰妯″潡鍛藉悕绌洪棿閿殑璇诲彇銆佸師瀛愬啓鍏ャ€佸崟閿洿鏂颁笌鍒犻櫎鍥為€€锛屽苟淇濊瘉閲嶅惎鎭㈠銆?
瀹炵幇鐘舵€侊細閮ㄥ垎銆€鏈熸锛氫竴鏈?
鍏叡閴存潈涓庡寘缁滆 [README.md](README.md)锛涘瓨鍌ㄨ亴璐ｈ [storage.md](storage.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗閰嶇疆 schema 鏍￠獙銆佽法閿害鏉熴€佺敤鎴?global/鍑哄巶涓夌骇瑙ｆ瀽銆佺珛鍗崇敓鏁堛€佹寔涔呭寲鍜屾仮澶嶉粯璁ゃ€?- 璐熻矗鎵€鏈変細褰卞搷鏀堕泦銆佹竻娲椼€佽缁冦€侀娴嬨€佽瘎浼般€佽В閲婂拰瀹氫綅缁撴灉鐨勯厤缃叆鍙ｃ€?- 涓嶈礋璐ｄ繚瀛?API Key銆佹暟鎹簱鍙ｄ护銆丩LM Key 绛夋晱鎰熶俊鎭紝涔熶笉鎵挎媴涓氬姟璁＄畻鎴栨枃浠跺鍏ャ€?- `.env` 浠呮彁渚涘嚭鍘傞粯璁ゅ拰閮ㄧ讲鏁忔劅椤癸紝涓嶆槸鐢ㄦ埛閰嶇疆鐨勬寔涔呭寲鏉ユ簮銆?
## 2. 绔偣濂戠害

### GET /api/config

鏌ヨ鍙傛暟 `keys` 鍙€夛紝閫楀彿鍒嗛殧閿悕銆傚搷搴?`data.items[]`锛沗data.schema` 鎻愪緵閿殑 `label/value_type/group/choices`锛屼緵閰嶇疆鍖烘覆鏌擄紝閫夐」鍙栫湡瀹炵櫥璁版暟鎹€傚浐瀹?API Token 涓嶆惡甯︾敤鎴疯韩浠斤紝涓€鏈熸帴鍙ｈ鍙栥€佸啓鍏ヤ笌鍒犻櫎鍧囧綊灞?`global`锛涘唴閮ㄩ厤缃湇鍔℃敮鎸佹槑纭敤鎴峰綊灞炰笌涓夌骇鍥為€€锛屼絾涓嶆帴鍙楄皟鐢ㄦ柟浼€犺韩浠藉ご銆傞厤缃」瀛楁锛?
| 瀛楁 | 鍚箟 |
|---|---|
| `config_key` | 閰嶇疆閿?|
| `value` | JSON 瑙ｇ爜鍚庣殑鏍囬噺銆佹暟缁勬垨瀵硅薄 |
| `value_type` | `float` / `int` / `string` / `bool` / `list` / `object` |
| `source` | `user` / `global` / `factory` |
| `updated_at` | 鏈€杩戞寔涔呭寲鏃堕棿锛宖actory 鍙负 null |

### PUT /api/config

鎵归噺鍘熷瓙鏇存柊锛岃姹?`{items:[{config_key,value}]}`銆備换涓€閿湭鐭ャ€佺被鍨嬮敊璇垨璺ㄩ敭绾︽潫澶辫触锛屾暣鎵逛笉鍐欍€傚搷搴?`{items[]}` 涓哄啓鍏ュ悗鐨勭敓鏁堥厤缃€?
### PUT /api/config/{key}

璇锋眰 `{value}`锛屽搷搴?`{items:[...]}`銆傝矾寰?key 蹇呴』鍦ㄧ櫧鍚嶅崟鍐咃紱涓嶈 `default_model`锛屾棫 `models/default` 鍐欏叆鍙ｅ凡搴熸锛?0001锛夈€?
### DELETE /api/config/{key}

鍒犻櫎褰撳墠鐢ㄦ埛琛岋紝鍝嶅簲 `{config_key,deleted:true,fallback_source,value}`锛涘洖閫€ global锛屽啀鍥為€€鍑哄巶榛樿銆傜敤鎴疯涓嶅瓨鍦ㄨ繑鍥?40400銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 鏈煡閿€佹晱鎰熼敭銆佺被鍨?鑼冨洿/瀵硅薄 schema 閿欒銆佽法閿害鏉熷け璐ャ€佹壒閲忛儴鍒嗛潪娉?|
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key` |
| 40400 | 404 | 鍒犻櫎涓嶅瓨鍦ㄧ殑鐢ㄦ埛閿紝鎴栧紩鐢ㄧ殑妯″瀷/鏁版嵁闆?妯℃澘涓嶅瓨鍦?|
| 50000 | 500 | 鏈鏈熷瓨鍌ㄩ敊璇紝涓嶅洖鏄?SQL 鎴栬繛鎺ヤ俊鎭?|

## 3. 杈撳叆濂戠害

閿笌鍊煎嵆鍏ㄩ儴杈撳叆锛屾棤鏂囦欢杈撳叆銆傚叏灞€閿細

| 閿?| 绫诲瀷 | 鍑哄巶榛樿 | 鏍￠獙涓庣敤閫?|
|---|---|---|---|
| `decision_threshold` | float | 0.5 | (0,1)锛岄娴嬫爣绛句笌璇勪及榛樿闃堝€?|
| `risk_high_threshold` | float | 0.5 | (0,1)锛屼笖澶т簬 risk_mid_threshold |
| `risk_mid_threshold` | float | 0.2 | (0,1)锛屼笖灏忎簬 risk_high_threshold |
| `default_dataset` | string | 绌?| 宸茬櫥璁?dataset_id锛涘彧浣滀究鍒╅€夋嫨 |
| `default_xai` | string | `shap` | 宸叉敞鍐岃В閲婃妧鏈?|
| `metrics_selected` | list | 鍏」鍩虹鎸囨爣 | 鍏冪礌灞炰簬 evaluate/metrics 娉ㄥ唽琛ㄤ笖鍘婚噸 |
| `primary_metric` | string | `auc` | 蹇呴』灞炰簬 metrics_selected |
| `effort_enabled` | bool | true | 鏄惁鍚敤 effort-aware 璇勪及 |
| `page_prefs` | object | `{}` | 浠呯櫧鍚嶅崟椤甸潰鍋忓ソ锛屼笉瀛樻晱鎰熶俊鎭?|

妯″潡鍛藉悕绌洪棿閿繚鎸佹湰韬殑鍊肩被鍨嬶細鍏佽鏍圭洰褰曚笌鍗忚涓?list锛屾ā鏉夸笌瀹氫綅鏉冮噸/Top-N 涓?object锛屾壒澶у皬/TTL/閲嶈瘯娆℃暟/鏂囦欢澶у皬涓?int锛屽姣斿紑鍏充负 bool锛屽缓璁潵婧愪负 list锛涘璞″唴閮ㄥ瓧娈垫寜妯″潡 schema 鏍￠獙锛?
| 鍛藉悕绌洪棿 | 閿?|
|---|---|
| collect | `collect.allow_roots`銆乣collect.protocol_whitelist` |
| clean | `clean.chain_templates` |
| train | `train.templates` |
| predict | `predict.batch_size`銆乣predict.cache_ttl`銆乣predict.retry_max` |
| explain | `explain.cache_ttl`銆乣explain.compare_enabled` |
| localization | `localization.weights`銆乣localization.top_n`銆乣localization.file_size_max`銆乣localization.suggestion_sources` |

璇锋眰涓嶅緱鍚澶栨湭鐭ラ敭锛涢槇鍊间笉鍙潤榛樻埅鏂紝甯冨皵鍊间笉鎺ュ彈鍚硦瀛楃涓诧紝妯℃澘涓殑绠楁硶/鎿嶄綔/鎶€鏈繀椤诲瓨鍦ㄣ€傞厤缃牎楠屽彲浠ヨ鍙栫櫥璁拌〃锛屼絾涓氬姟妯″潡杩愯浠嶄笉浠ヨ繖浜涜〃浣滀负鏂囦欢浜ゆ崲鍓嶇疆銆?
## 4. 杈撳嚭濂戠害

浠呰緭鍑轰笂杩?JSON 閰嶇疆椤逛笌鍒犻櫎鍥為€€缁撴灉锛屼笉鐢熸垚 CSV/XLSX銆佹姤鍛婃垨 manifest锛屼篃涓嶅垱寤?`temp/outputs` 鐩綍銆傚搷搴斾笉杩斿洖閮ㄧ讲鐜鍙橀噺銆佽繛鎺ヤ覆銆佸瘑閽ユ垨鍙€嗘晱鎰熷瓧娈点€?
鎵归噺 PUT 鐨勮繑鍥為『搴忎笌璇锋眰涓€鑷达紱GET 鎸?config_key 瀛楀吀搴忚繑鍥烇紝淇濊瘉娴嬭瘯绋冲畾銆俿ource 琛ㄧず瀹為檯鐢熸晥灞傜骇锛屼笉鎶?factory 榛樿浼涓虹敤鎴峰凡淇濆瓨鍊笺€?
## 5. 鍙厤缃」

鏈瘒鍗抽厤缃潈濞併€傝鍙栭『搴忓浐瀹氫负褰撳墠鐢ㄦ埛 鈫?global 鈫?鍑哄巶榛樿锛岃В鏋愬彧瀛樺湪浜庨厤缃湇鍔★紱鍓嶇鍜屽悇妯″潡涓嶅緱鍚勭淮鎶や竴濂椾紭鍏堢骇銆?
- decision_threshold 涓?risk_high/risk_mid 鏄笉鍚岃涔夛紝涓嶅緱浜掔浉鏇夸唬銆?- default_dataset 涓虹┖涓嶉樆姝㈡枃浠朵笂浼犺繍琛岋紱妯″瀷涓嶈榛樿鍊硷紝杩愯鍏ュ彛蹇呴』鏄惧紡鎸囧畾銆?- 鎭㈠榛樿閫氳繃 DELETE 瀹屾垚锛岃€屼笉鏄妸鍑哄巶鍊煎鍒跺埌鐢ㄦ埛琛屻€?- 鎵€鏈夋ā鍧楀懡鍚嶇┖闂撮敭閬靛惊鐩稿悓鏍￠獙銆佸師瀛愬啓鍏ヤ笌閲嶅惎鎭㈠瑙勫垯銆?- W1 宸叉彁渚涢厤缃鍐欍€佺被鍨嬫牎楠屼笌椋庨櫓闃堝€兼帴鍏ワ紱榛樿妯″瀷鎺ュ叆宸茬Щ闄ゃ€俙page_prefs` 瀛愰敭涓?`page_size/remember_drawer/explain_top_n/collect_branch/collect_mode`锛涘悗涓ら」涓?W3 鏀堕泦椤甸潰鐨勯粯璁ゅ垎鏀笌妯″紡锛屾樉寮忎繚瀛樺悗鎸佷箙鍖栵紝涓嶈鐩栧凡鍒涘缓浠诲姟鐨勫叆鍙傦紝瀹氫綅 Top-N 瀵硅薄涓?`{files,lines}`銆?- W4 clean.chain_templates 鐢变節鎿嶄綔娉ㄥ唽琛ㄦ牎楠岋紝鍙繚瀛樻渶澶?30 涓懡鍚嶉厤缃璞★紱姝ラ鐪佺暐 enabled/params 鍒嗗埆浣跨敤 true/榛樿鍙傛暟銆傛ā鏉挎寜鍘熷瓙閰嶇疆鍐欏叆鎸佷箙鍖栵紝鍗曟杩愯鍥哄寲蹇収銆俉5 train.templates 鐢辩畻娉曟敞鍐岃〃鏍￠獙锛坙ine/algos/瓒呭弬/鍒掑垎/绉嶅瓙锛夛紝鏈€澶?30 涓懡鍚嶆ā鏉匡紝闈?expert 绾挎ā鏉垮洜杈撳叆濂戠害涓嶆敮鎸佽€屾嫆缁濓紱W8 宸叉敞鍐?SHAP/LIME锛宒efault_xai 鍙€?shap/lime锛沞xplain.compare_enabled 鎺у埗 HTTP 澶氭妧鏈瘮杈冿紝榛樿 false锛屾樉寮忓紑鍚墠鐢熸晥銆?- 鍒犻櫎褰撳墠褰掑睘琛屽墠涔熸牎楠屽洖閫€鍚庣殑璺ㄩ敭绾︽潫锛屽け璐ユ椂涓嶅垹闄わ紱鏃犵櫥褰曚笂涓嬫枃鍒犻櫎 global 琛屽洖閫€鍑哄巶榛樿銆?
## 6. 鐘舵€佹寔涔呭寲

- 姣忔鎴愬姛鍐欏叆绔嬪嵆钀?user_config 骞舵洿鏂?updated_at锛涙壒閲忔洿鏂板湪鍗曚簨鍔″唴瀹屾垚銆?- 鍚庣銆佸鍣ㄦ垨杩涚▼寮傚父鍏抽棴鍚庨噸鍚紝GET 杩斿洖鍘熼厤缃紱杩愯涓ā鍧楀湪涓嬫璇诲彇鏃惰幏寰楁柊鍊硷紝宸蹭骇鏂囦欢浠嶄互鍏?manifest 閰嶇疆蹇収涓哄噯銆?- 涓嶅垱寤?job锛屼笉鐢熸垚杈撳嚭鏂囦欢銆傞厤缃彉鍖栧彲浣胯繍琛屾椂缂撳瓨澶辨晥锛屼絾涓嶅緱鏀瑰啓鍘嗗彶 job 鎴?manifest銆?- 瀹¤鏃ュ織璁板綍閿€佹潵婧愬拰鏃堕棿锛屼笉璁板綍鏁忔劅鍊硷紱鏁忔劅閿姹傜洿鎺ユ嫆缁濄€?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/config/`锛屼互 JSON 姝ｅ父銆佽竟鐣屻€侀潪娉曢厤缃牱渚嬮┍鍔ㄦ帴鍙ｆ祴璇曘€?
- **姝ｅ父**锛氭壒閲?鍗曢敭璇诲啓鎵€鏈夊叏灞€閿笌鍛藉悕绌洪棿閿紝source 姝ｇ‘锛涢噸鍚悗鍊笺€佹ā鏉垮拰椤甸潰鍋忓ソ瀹屾暣鎭㈠銆?- **杈圭晫**锛氬垹闄ょ敤鎴烽敭鍥為€€ global/factory锛宒efault_dataset 涓虹┖锛岀紦瀛?TTL 涓?0锛岄槇鍊艰法閿仈鍔ㄥ潎鎸夊绾︽墽琛屻€?- **闈炴硶**锛氭湭鐭ラ敭銆?.5 闃堝€笺€乵id鈮igh銆乸rimary_metric 鏈€夈€佹晱鎰熼敭銆侀敊璇璞＄粨鏋勩€佹壒閲忎竴涓潖鍊煎潎杩斿洖 40001 涓斿師鍊间笉鍙橈紱鍒犻櫎涓嶅瓨鍦ㄩ敭杩斿洖 40400銆?- 淇敼闃堝€?XAI 鍚庣浉鍏虫ā鍧椾娇鐢ㄦ柊閰嶇疆锛屽巻鍙?manifest 涓嶅彉锛涙ā鍨嬬敱姣忔杩愯鏄惧紡閫夋嫨锛屾帴鍙ｄ笌璁剧疆椤佃鍐欎竴鑷翠笖鏃犲瘑閽ユ硠婕忋€?
## 8. 杈圭晫

閰嶇疆鏄悇妯″潡鐨勮繍琛屽弬鏁版潵婧愶紝涓嶆槸鏁版嵁浜ゆ崲閫氶亾銆傛ā鍧楀彲浠呭嚟鏄惧紡 config part 鍜岃緭鍏ユ枃浠惰繍琛岋紱user_config 鎻愪緵鎸佷箙榛樿涓庝究鍒╅」锛屾暟鎹簱涓嶅彲鐢ㄤ笉寰楁敼鍙樺凡涓婁紶鏂囦欢鐨?schema锛屼篃涓嶅簲琚敤浣滈殣寮忎笂娓镐緷璧栥€?