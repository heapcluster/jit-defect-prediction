# 缂洪櫡瀹氫綅銆佷慨澶嶅缓璁笌婧愮爜 API锛坙ocalize / source锛?
涓€鍙ヨ瘽锛氱嫭绔嬫秷璐?predictions銆佸彲閫?explanations 涓庢寚瀹氫粨搴撶増鏈紝杈撳嚭鍙枒琛屻€佸畬鏁磋瘉鎹笌鍥涙寮忎慨澶嶅缓璁紝骞舵彁渚涘悓鐗堟湰婧愮爜鏍戜笌鏂囦欢璇诲彇锛涘綋鍓嶄笉鐢熸垚淇琛ヤ竵銆?
瀹炵幇鐘舵€侊細宸插疄鐜帮紙瀹氫綅銆佹簮鐮佽鍙栥€佸缓璁笌鏂囦欢浜や粯锛涙棤鍙潬淇敼锛屽綋鍓嶄笉鐢熸垚淇琛ヤ竵锛夈€€鏈熸锛氫竴鏈?
楠岃瘉鍙ｅ緞锛?026-11-23 鏈疆鍚庣鍏ㄩ噺 809 椤广€佸墠绔叏閲?253 椤规祴璇曢€氳繃锛?200/375px 娴忚鍣ㄨ嚜鍔ㄥ寲瑕嗙洊婧愮爜娴忚銆侀珮浜€佺湡瀹?SHAP 鏂囦欢鍖归厤銆佺増鏈嫆缁濄€佹彁浜ょ骇鍥為€€銆佷笅杞芥牎楠屽強鍏?tab 鏃ч摼鎺ュ吋瀹癸紝CLI/API 鍚岃緭鍏ョ粨鏋滀竴鑷淬€傛祴璇曚负 AI 鐢熸垚銆佹湭缁忎汉宸ュ闃咃紝涓嶄唬琛ㄤ汉宸ラ獙鏀躲€?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.4銆伮?.7銆伮?.8銆伮?.9锛涘叕鍏卞彛寰勮 [README.md](README.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗鎻愪氦鐗堟湰婧愮爜鐩綍/鏂囦欢鎸夐檺棰濊鍙栥€佽绾у彲鐤戝害鎺掑簭銆佸畬鏁磋瘉鎹拰鍥涙寮忎慨澶嶅缓璁紱鍘熷 Git diff 浠呬负鍙璇佹嵁銆傚綋鍓嶆棤鍙潬淇敼锛屼笉鐢熸垚淇琛ヤ竵锛沗patch_preview=true` 璁板綍 `summary.patch_reason="no_reliable_patch"`銆?- 鎻愪氦绾?risk_score 涓庤绾?suspicion 鏄笉鍚屾暟鍊硷紱鍚庤€呬负鍙厤缃惎鍙戝紡鍙枒搴︼紝涓嶅绉颁负鐙珛璁粌鐨勮绾ф鐜囥€?- 涓嶈礋璐ｆ彁浜ょ骇棰勬祴銆乆AI 璁＄畻銆佽缁冩垨璇勪及锛涘彧娑堣垂鍏舵枃浠讹紝涓嶈皟鐢?predict/explain 鏈嶅姟銆?- 涓嶈嚜鍔ㄥ簲鐢ㄨˉ涓併€佷慨鏀瑰伐浣滃尯銆佸垱寤烘彁浜ゆ垨 PR锛涙棤婧愮爜鎴栧缓璁湇鍔″け璐ヤ笉褰卞搷宸蹭氦浠橀娴嬫枃浠躲€?
## 2. 绔偣濂戠害

### POST /api/localize/run

鍚屾 multipart锛歚files[]` 蹇呴』鍚?predictions锛屽彲鍚?explanations 鍙婂叾鍚?stem manifest锛沗config` JSON part銆傛渶澶?4 涓枃浠躲€佸悎璁?64MiB锛堝惈 manifest锛夛紝鏂囦欢鍚嶄笉鍙噸澶嶃€傛枃浠跺彲鐩存帴涓婁紶锛屼篃鍙寜 [浜х墿搴撻€夋嫨娴佺▼](README.md#浜х墿搴撻€夋嫨涓庝笂浼犵瓑浠?浠?`predict_batch` / `explain` 浠诲姟涓嬭浇鍚庢彁浜わ紱`dataset_id` 浠呬究鍒╄В鏋愪粨搴擄紝涓嶄唬鏇块娴嬫枃浠躲€俵ocalize 涓嶆柊澧?job kind锛涚瓫閫夊悗鏈€澶?20 涓娴嬬洰鏍囷紙鎻愪氦/妯″瀷/鐗堟湰棰勬祴琛岋級锛屼笖棰勪及 `targets * top_n.files * top_n.lines <= 5000`锛岃秴闄愯繑鍥?40001锛岀敱璋冪敤鏂圭瓫閫夈€侀檷浣?Top-N 鎴栧垎鎵广€?
| config 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `repo_source` | 涓?dataset_id 浜岄€変竴 | 鏈湴璺緞鎴?URL锛涘畨鍏ㄨ鍒欏悓 collect锛屾樉寮忓€间紭鍏?|
| `dataset_id` | 涓?repo_source 浜岄€変竴 | 瑙ｆ瀽鐧昏浠撳簱鐨勪究鍒╅」锛屼笉浠ｆ浛棰勬祴鏂囦欢 |
| `commit_hash` | 鍚?| 40 浣?hex锛岀瓫閫夐娴嬬洰鏍囷紱涓嶄紶鍒欎笉鎸夋彁浜ょ瓫閫?|
| `model_name` | 鍚?| 闈炵┖妯″瀷鍚嶏紝绛涢€夐娴嬬洰鏍囷紱涓嶄紶鍒欎笉鎸夋ā鍨嬬瓫閫?|
| `weights` | 鍚?| `file_types` / `change` / `hunk` / `line_content` / `line_path` / `mix`锛涘祵濂楅儴鍒嗚鐩?`localization.weights`锛屾湭鎻愪緵椤逛繚鐣欏凡淇濆瓨榛樿鍊?|
| `top_n` | 鍚?| 瀵硅薄 `{files,lines}`锛屽悇涓?1..1000 鏁存暟锛涢儴鍒嗚鐩栦繚鐣?`localization.top_n` 鏈彁渚涢」 |
| `file_size_max` | 鍚?| 瀛楄妭鏁帮紝1..16MiB 鐨勬暣鏁帮紱榛樿鍙栧凡淇濆瓨 `localization.file_size_max`锛堝嚭鍘?1MiB锛?|
| `suggestion_sources` | 鍚?| `template` / `llm` / `history` 鐨勯潪绌恒€佹棤閲嶅瀛愰泦 |
| `patch_preview` | 鍚?| 榛樿 true锛涘綋鍓嶄笉鐢熸垚淇琛ヤ竵锛宼rue 鏃?`summary.patch_reason="no_reliable_patch"`锛宖alse 鏃朵负 null |
| `format` | 鍚?| `csv` / `xlsx`锛岄粯璁?`csv`锛涘綋鍓嶄袱绉嶈〃鏍煎潎杈撳嚭锛屾椤瑰喅瀹氶閫夋牸寮忓拰涓?manifest |

鍝嶅簲 `data`锛歚{job_id,module:"localize",status:"success",outputs[],manifest_name,summary,localization,suggestions}`銆傝繖閲?job_id 涓?UUID锛屼粎鏄緭鍑烘壒娆℃爣璇嗭紝涓嶅垱寤?job 琛岋紱`outputs[]` 椤逛负 `{name,sha256,size_bytes}`锛宍localization` 涓哄墠 20 琛岄瑙堬紝`suggestions` 涓哄缓璁叏鏂囥€傚畬鏁?rows 浠庣櫥璁扮殑 `localization_evidence_<job_id>.json` 鍔犺浇锛屼笉浠ラ瑙堝厖褰撳叏閮ㄧ粨鏋滐紱椤甸潰椤诲畬鎴愯瘉鎹?JSON 缁撴瀯鏍￠獙鍚庢墠纭杈撳嚭鎴愬姛銆俿ummary 鍚?`commits,localized_rows,line_rows,commit_rows,insufficient_count,suggestion_sources,truncated,patch_reason`銆傚崟鎵硅繃澶ц繑鍥?40001锛屼笉鎺掗槦銆佷笉闅愬紡鍒涘缓寮傛浠诲姟銆?
### GET /api/localize/outputs/{job_id}/{name}

涓嬭浇宸茬櫥璁扮殑 localization CSV/XLSX銆佸畬鏁?evidence JSON銆乻uggestions Markdown 鎴?manifest锛涘彧鍏佽 `outputs[]` 鐧昏鐨勫熀纭€鏂囦欢鍚嶃€傚綋鍓嶆病鏈変慨澶?patch 鏂囦欢鍙笅杞斤紝鍘熷鎻愪氦 Git diff 浣嶄簬 evidence JSON 涓紝浠呬緵鍙鍙栬瘉銆?
### GET /api/source/tree

| 鍙傛暟 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `commit_hash` | 鏄?| 瀹屾暣 40 浣?hex锛屼笉鎺ュ彈鍒嗘敮鍚嶃€乺ef 鎴栫煭鍝堝笇 |
| `path` | 鍚?| 浠撳簱鐩稿鐩綍锛岄粯璁ゆ牴鐩綍锛涚姝㈢粷瀵硅矾寰勪笌 `..` |
| `search` | 鍚?| 闈炵┖璺緞瀛愪覆锛屾渶澶?4096 瀛楃锛涚┖鎼滅储蹇呴』鐪佺暐鍙傛暟锛屼笉鑳戒紶 `search=` |
| `repo_source` / `dataset_id` | 浜岄€変竴 | 鏄惧紡浠撳簱鎴栧彲閫夌櫥璁颁究鍒╅」 |

鍝嶅簲 `data:{commit_hash,path,entries[],truncated,skipped[]}`锛沞ntries 姣忛」 `{name,path,type,size,mode}`锛宼ype 涓?tree/blob锛屾瘡娆℃渶澶?1000 椤癸紝瓒呭嚭鏍囪 `truncated`銆備笉鏀寔鐨?gitlink 浠?`skipped:[{path,reason:"unsupported_gitlink"}]` 鏍囨敞锛堟渶澶?1000 椤癸級锛涚洰褰曟祻瑙堜笉淇濊瘉鍗曟杩斿洖鏁存５鏍戙€?
### GET /api/source/file

`commit_hash` 蹇呭～涓斾负瀹屾暣 40 浣?hex锛宍path` 蹇呭～涓斾负浠撳簱鐩稿鏂囦欢璺緞锛宍repo_source`/`dataset_id` 鍚屼笂锛涘彟鎺ュ彈 `start_line`锛堥粯璁?1锛夈€乣end_line`锛?-based 闂尯闂达級銆傛瘡娆℃渶澶氳繑鍥?2000 琛岋紝鐪佺暐 end 鏃惰鑷?start 璧锋渶澶?2000 琛岋紱end 瓒呰繃 EOF 鎴栬姹備笂闄愭椂鑷姩澶瑰彇锛宻tart 瓒呰繃 EOF 闈炴硶锛堢┖鏂囦欢浠呭厑璁?start=1锛夈€傝秴杩?`file_size_max` 鐨勬枃浠舵暣浣撹繑鍥?`too_large`锛岀缉灏忚鑼冨洿涓嶈兘缁曡繃澶у皬闄愬埗銆傚搷搴旓細

| 瀛楁 | 鍚箟 |
|---|---|
| `commit_hash` / `path` | 鐗堟湰涓庢枃浠?|
| `status` | `ok` / `binary` / `too_large` / `not_found` |
| `content` | ok 鏃舵枃鏈紝鍏朵綑涓?null |
| `start_line` / `end_line` / `total_lines` | 瀹為檯琛岃寖鍥翠笌鎬昏鏁?|
| `size_bytes` / `encoding` | 瀛楄妭鏁颁笌鏂囨湰缂栫爜 |
| `reason` | 闈?ok 鐨勬槑纭師鍥?|

鏂囦欢 binary/too_large/not_found 鍦ㄦ彁浜ゅ彲杈炬椂浠?HTTP 200 + data.status 琛ㄨ揪锛屼笉褰撲綔鏈嶅姟寮傚父銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 璺緞瓒婄晫銆佽鑼冨洿闈炴硶銆佽緭鍏?schema/鏉冮噸/top_n 闈炴硶銆佸崟鎵硅繃澶с€佷笅杞藉悕闈炴硶 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key`锛屽寘鎷簮鐮佸拰涓嬭浇 |
| 40400 | 404 | 浠撳簱銆佹彁浜ゃ€佸彲閫?dataset銆佽緭鍑烘壒娆℃垨鏂囦欢鐧昏涓嶅瓨鍦?|
| 50000 | 500 | 鏈鏈?Git/鏈嶅姟閿欒锛涘缓璁敓鎴愬け璐ュ簲鍥為€€妯℃澘骞舵爣鏉ユ簮 |

## 3. 杈撳叆濂戠害

predictions 閫愬瓧閲囩敤 搂3.4锛?
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

鍙€?explanations 閫愬瓧閲囩敤 搂3.7锛?
> `commit_hash,model_name,technique,feature,raw_value,contribution,direction,rank,label,model_version,feature_version`锛涗笉鏀寔缁勫悎浜?`reason_code` 琛岋紙feature 绌恒€乧ontribution 绌恒€乺eason_code 闈炵┖锛夛紝MUST NOT 闈欓粯缂鸿銆?
婧愮爜鏉ヨ嚜 repo_source 瀵瑰簲 commit 鐨?Git 瀵硅薄锛岀姝互褰撳墠宸ヤ綔鍖烘浛浠ｃ€備笂浼犳墽琛屽ぇ灏忋€佹墿灞曞悕榄旀暟銆乻chema銆佸叕寮忔敞鍏ユ牎楠岋紱Git 浣跨敤鍙傛暟鏁扮粍锛屼粨搴撹矾寰勯檺瀹氬厑璁告牴鐩綍锛屾枃浠惰矾寰勭姝㈢┛瓒婏紝鏂囦欢鍚嶄笉鎷兼帴 shell銆?
缂哄皯 explanations 鏃跺彲浠呬緷 predictions銆乨iff 涓庝唬鐮佷笂涓嬫枃瀹氫綅锛屼絾 evidence_json 蹇呴』鏍囨槑璇佹嵁鏉ユ簮涓嶈冻锛涚己 predictions 涓嶅厑璁稿嚟绌虹敓鎴愭彁浜ら闄┿€?
## 4. 杈撳嚭濂戠害

褰撳墠浜や粯閲囩敤 搂3.8 鐨勫畾浣嶅垪涓庡洓娈靛紡寤鸿锛?
> localization锛歚commit_hash,file_path,line_number,suspicion,rank,evidence_json,level(line|commit)`锛涘缓璁惈闂璇存槑/寤鸿淇敼/椋庨櫓鎻愮ず/鍙傝€冧緷鎹€偮?.8 鐨勪慨澶?patch 褰撳墠涓嶇敓鎴愶細娌℃湁鍙潬淇敼锛屼笉鑳藉皢鍘熷 Git diff 褰撲綔淇琛ヤ竵浜や粯銆?
| 鏂囦欢 | 鍛藉悕锛坖ob_id 涓?UUID锛?| 濂戠害 |
|---|---|---|
| localization | `localization_localization_<job_id>.csv` 鍜?`.xlsx` | 涓ょ鏍煎紡鍧囩敓鎴愶紝涓ユ牸浣跨敤涓婅堪 搂3.8 鍒?|
| evidence | `localization_evidence_<job_id>.json` | `{rows,evidence,summary}`锛況ows 涓哄畬鏁村畾浣嶈锛宔vidence 鎸?commit_hash 鏀跺綍鍘熷 diff銆佹枃浠?棰勬祴璇佹嵁涓庝笉瓒冲師鍥?|
| suggestions | `localization_suggestions_<job_id>.md` | 鍥涙寮忥紝寮曠敤瀹為檯 file_path/line_number 涓庤瘉鎹潵婧愶紱鏃犲彲楠岃瘉鏂囨湰琛屾椂寮曠敤鎻愪氦骞舵敞鏄庝笉瓒?|
| manifest | 鍚勪骇鐗╁悓 stem `.manifest.json` | 琛ㄦ牸鍏辩敤 `localization_localization_<job_id>.manifest.json`锛涜瘉鎹拰寤鸿鍚勬湁鍚?stem manifest锛屾寜 搂3.9 鐧昏杈撳叆銆侀厤缃揩鐓у強鍏ㄩ儴浜х墿 checksum |

褰撳墠涓嶈緭鍑轰慨澶?`.diff`锛沗patch_preview=true` 鏃?`summary.patch_reason="no_reliable_patch"`锛宖alse 鏃朵负 null銆俥vidence 涓殑 `diff` 鏄師濮嬫彁浜ょ殑鍙 Git 璇佹嵁锛屼笉鏄缓璁慨鏀圭殑琛ヤ竵銆?
閫愯 `evidence_json` 璁板綍棰勬祴椋庨櫓銆佽В閲婁笂涓嬫枃銆乨iff 鍏冩暟鎹€佷唬鐮佷笂涓嬫枃銆佸巻鍙蹭慨澶嶅強涓嶈冻鍘熷洜锛涙彁浜ょ骇瑙ｉ噴涓嶈瘉鏄庢煇琛屾湁缂洪櫡锛屼篃涓嶄綔涓哄彲璋冪殑瑙ｉ噴鏄犲皠鏉冮噸銆俵evel 鍙兘 line/commit锛涙棤娉曢獙璇佽鏃跺彲缁?commit 绾х粨鏋滐紝file_path/line_number 涓?null锛岀姝㈢紪閫犺鍙枫€?
suggestions 蹇呴』鍚€滈棶棰樿鏄庛€佸缓璁慨鏀广€侀闄╂彁绀恒€佸弬鑰冧緷鎹€濆洓娈碉紱LLM 涓嶅彲鐢ㄥ洖閫€妯℃澘骞舵爣鏉ユ簮銆侰SV UTF-8 BOM銆乆LSX 鍗?sheet锛岃瘉鎹?JSON 涓?md 浣跨敤 UTF-8銆?
婧愮爜 GET 鍙 Git 瀵硅薄锛屼笉浜х敓浜ゆ崲鏂囦欢鎴?manifest锛沴ocalize run 鐨勪笂杩版枃浠跺繀椤诲叏閮ㄨ惤鐩樺苟鍙笅杞姐€?
## 5. 鍙厤缃」

- `localization.weights`锛氫粎 `file_types`銆乣change`銆乣hunk`銆乣line_content`銆乣line_path`銆乣mix` 鍏粍锛涙潈閲嶉』涓洪潪璐熸湁闄愭暟锛屾嫆缁濇湭鐭ュ瓧娈点€侶TTP run 鐨勫祵濂楅儴鍒嗚鐩栦繚鐣欐暟鎹簱宸蹭繚瀛樼殑鏈彁渚涢」锛屼笉閫€鍥炲嚭鍘傞粯璁わ紱瑙ｉ噴浠呬负涓婁笅鏂囷紝涓嶅瓨鍦ㄨВ閲婃槧灏勬潈閲嶃€?- `localization.top_n`锛坒iles/lines 鍚?1..1000锛夈€乣localization.file_size_max`锛?..16MiB 瀛楄妭鏁存暟锛夈€乣localization.suggestion_sources`锛屽叏閮ㄨ惤 user_config锛岄噸鍚仮澶嶃€?- 鍗曟杩愯鍙鐩栨潈閲嶃€乀op-N銆佹枃浠跺ぇ灏忎笂闄愩€佸缓璁潵婧愩€乸atch_preview銆佹牸寮忓拰鐩爣绛涢€夛紱婧愮爜鏂囦欢瓒呰繃 file_size_max 鏁翠綋杩斿洖 too_large锛岃鑼冨洿涓嶈兘缁曡繃闄愬埗銆?- LLM 杩炴帴鍜屽瘑閽ュ彧璧伴儴缃茬幆澧冿紝涓嶅啓鍏?user_config 鎴?manifest锛沗.env` 浠呮彁渚涢潪鏁忔劅鍑哄巶榛樿銆?
## 6. 鐘舵€佹寔涔呭寲

- localize 鍚屾鎵ц锛屼笉鏂板 job kind锛屼笉鍐?queued/running锛沯ob_id 浠呯敤浜庤緭鍑虹洰褰曘€乵anifest 涓庝笅杞藉叧鑱斻€?- 杈撳嚭钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紱閰嶇疆鍐?user_config锛岄噸鍚仮澶嶃€備换鍔″垪琛ㄤ笉浼氭妸 localize 鏄剧ず涓虹涓冪被浠诲姟銆?- 瓒呭ぇ杈撳叆浠?40001 璇锋眰鍒嗘壒锛屽凡瀹屾垚鎵规鏂囦欢淇濈暀锛涗笉寰楄繑鍥為儴鍒嗘垚鍔熷嵈缂?manifest 鐨勭洰褰曘€?- 婧愮爜 tree/file 涓哄彧璇昏姹傦紝涓嶅垱寤鸿緭鍑虹洰褰曪紱瀹氫綅缁撴灉澶嶇幇渚濊緭鍏?checksum銆乧ommit銆佹潈閲嶄笌寤鸿鏉ユ簮蹇収銆?
## 7. 楠屾敹

鑷姩鍖栫敤渚嬩笌涓存椂 Git/琛ㄦ牸杈撳叆瑙?`backend/tests/test_localization_core.py`銆乣backend/tests/test_source_api.py` 鍜?`frontend/tests/Localization.spec.js`锛屾棤闇€ predict/explain 鏈嶅姟鍦ㄧ嚎锛涘潎涓?AI 鐢熸垚銆佹湭缁忎汉宸ュ闃呯殑鑷姩鍖栭獙璇侊紝涓嶄綔涓轰汉宸ラ獙鏀剁粨璁恒€?
- **姝ｅ父**锛氬緱鍒?搂3.8 鍙枒琛?CSV/XLSX銆佸畬鏁?evidence JSON銆佸洓娈靛缓璁拰鍚?stem manifest锛泃ree/file 璇诲彇鍚屼竴 commit锛岃鍙锋槧灏勪竴鑷达紝涓嬭浇鍏ㄩ儴閴存潈銆傚綋鍓嶄笉鐢熸垚淇琛ヤ竵锛涜姹?patch 鏃舵槑纭?`no_reliable_patch`锛屽師濮?diff 鍙綔涓鸿瘉鎹€?- **杈圭晫**锛氭棤 explanations銆乧ommit 绾ч檷绾с€佺┖ diff銆佷簩杩涘埗銆佽秴澶ф枃浠躲€丩LM 澶辫触銆佹棤琛ヤ竵鍧囨槑纭爣娉紝涓嶄吉閫犺鍙锋垨淇敼宸ヤ綔鍖恒€?- **闈炴硶**锛氱己 predictions銆乭ash/鐗堟湰涓嶇銆佽矾寰?`..`銆佺粷瀵硅矾寰勩€侀潪娉曡鑼冨洿銆佹潈閲嶅缓妯￠敊璇€佸崟鎵硅繃澶у潎杩斿洖 40001/40400锛屼笉浜у崐鎴愬搧銆?- 鏉冮噸鍜?Top-N 鏀瑰姩鐪熷疄褰卞搷鎺掑簭锛涗笉鏂板 job kind锛汣LI/API 鍚?fixture 鐨?localization 鏁板€间笌寤鸿缁撴瀯涓€鑷淬€?
## 8. 杈圭晫

localization 涓?predict/explain 浠呬互 搂3.4/搂3.7 鏂囦欢鍜屾ā鍨?鐗瑰緛鐗堟湰琛旀帴锛屼笌 collect 浠呭叡浜粨搴撳畨鍏ㄧ害鏉熴€俙dataset_id` 鍙究鍒╄В鏋愪粨搴撱€侰LI 鏂囦欢瀹氫綅涓庢簮鐮佹祻瑙堟棤闇€鏁版嵁搴撴垨涓婃父鏈嶅姟锛屼絾蹇呴』鏄惧紡鎻愪緵 `--allow-root`锛沗localize run --config` 鐨?JSON 浠呰鏄惧紡鎻愪緵鐨勫悓鍚?flag 瑕嗙洊銆侶TTP 浣跨敤鏁版嵁搴撹鍙栭厤缃拰鍙€夋暟鎹泦锛屼笉搴斿皢 CLI 鐨勬棤鏁版嵁搴撹兘鍔涚瓑鍚屼负 HTTP 鏃犳暟鎹簱銆?