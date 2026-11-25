# 缂洪櫡鏁版嵁鏀堕泦锛堝姛鑳?2锛?
瀹炵幇鐘舵€侊細鐩爣濂戠害銆€鏈熸锛氫竴鏈?
> 鏃у疄鐜颁腑瀛樺湪 14 缁寸壒寰佹彁鍙栥€?0/30 鍒囧垎鍜屸€滃彲閫夊鍏ュ簱鈥濆彛寰勶紱鏈枃宸叉寜鏈€鏂版澘鍧?2 瀹氫箟閲嶅啓锛屾棫鍙ｅ緞搴熸銆傛湰杞彧淇敼璁捐鏂囨。锛宍infra/schema.sql`銆丱RM銆佹湇鍔″拰椤甸潰瀹炵幇鍚庣画鎸夋湰鏂囧悓姝ャ€?
## 涓€鍙ヨ瘽姒傝堪

鐙珛鐨勬暟鎹敹闆嗗伐鍏凤細鐢ㄦ埛鎸囧畾 Git 浠撳簱鎴栧叕寮€鏍囨敞鏁版嵁闆嗭紝绯荤粺瀹屾垚浠撳簱鎷夊彇鎴栨暟鎹泦瀵煎叆锛岀敓鎴愬甫缂洪櫡鏍囩鐨勪簩缁磋〃锛岄〉闈㈠睍绀猴紝榛樿淇濆瓨鏁版嵁搴擄紝骞舵敮鎸佸鍑?CSV/XLSX銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

**璐熻矗**锛?
- Git 浠撳簱妯″紡锛氭帴鏀朵粨搴撹矾寰?URL銆佸垎鏀€佹椂闂存垨鎻愪氦鑼冨洿銆侀噰闆嗘ā寮忋€丼ZZ 鏂规硶銆佹暟鎹泦鍚嶇О锛屽畬鎴愭媺鍙?璇诲彇銆佹彁浜ら噰闆嗐€丼ZZ 鎵撴爣鍜屼簩缁磋〃鐢熸垚銆?- 鍏紑鏁版嵁闆嗘ā寮忥細鎺ユ敹鏁版嵁闆嗘枃浠?URL銆佽鍙瘉銆佹潵婧愯鏄庛€佸瓧娈垫槧灏勫拰鏍囩鍊兼槧灏勶紝鎶婄涓夋柟宸叉墦鏍囨暟鎹粺涓€杞崲涓烘湰绯荤粺浜岀淮琛ㄣ€?- 鐢熸垚缁熻淇℃伅鍜?manifest銆?- 榛樿鎶婁簩缁磋〃淇濆瓨鍒版暟鎹簱锛涙暟鎹簱淇濆瓨澶辫触鏃朵繚鐣欐枃浠朵骇鐗╁苟缁欏嚭鏄庣‘鐘舵€併€?- 鎻愪緵浜岀淮琛ㄩ瑙堛€丆SV/XLSX 瀵煎嚭銆乵anifest 涓嬭浇鍜屾暟鎹泦鍒楄〃灞曠ず銆?- 缁存姢浠撳簱璺緞/鍗忚瀹夊叏杈圭晫銆佹暟鎹泦鏉ユ簮涓庤鍙瘉淇℃伅銆丼ZZ 鍒ゆ嵁鍗曟簮銆?
**涓嶈礋璐?*锛?
- Kamei 14 缁寸壒寰佽绠椼€?- 璁粌/娴嬭瘯闆嗗垏鍒嗭紝`is_test` 涓嶅湪鏈ā鍧椾骇鍑恒€?- 娓呮礂澶勭悊閾俱€佹爣鍑嗗寲銆佸綊涓€鍖栨垨鐗瑰緛鍙樻崲銆?- 璁粌銆侀娴嬨€佽瘎浼般€佽В閲娿€佸畾浣嶃€佷慨澶嶃€?- 鎶婃暟鎹簱鎴栫幆澧冨彉閲忎腑鐨勫浐瀹氫粨搴撳綋浣滆繍琛屽墠鎻愩€?- 鎶婂叕寮€鏁版嵁闆嗕吉瑁呮垚 SZZ 鎵撴爣缁撴灉銆?
## 2 鐙珛杩愯鍏ュ彛

| 鍏ュ彛 | 鍛戒护 / 绔偣 | 濂戠害 |
|---|---|---|
| CLI | `python data_model/preparation/collect.py git ...` | Git 浠撳簱閲囬泦锛涢粯璁や繚瀛樻暟鎹簱锛屽彲鐢?`--no-save` 鍏抽棴 |
| CLI | `python data_model/preparation/collect.py public ...` | 鍏紑鏍囨敞鏁版嵁闆嗗鍏ワ紱榛樿淇濆瓨鏁版嵁搴?|
| 浠诲姟 API | `POST /api/collect/run` | `source_type=git_repo` 鎴?`public_dataset`锛屽垱寤?`job.kind=collect` |
| 浠诲姟绠＄悊 | `GET /api/jobs/{id}`銆乣POST /api/jobs/{id}/retry\|cancel` | 浜旀€併€佽繘搴︺€佽劚鏁忔棩蹇椼€侀噸璇曘€佸彇娑?|
| 棰勮 | `GET /api/collect/preview/{job_id}` | 杩斿洖鍒楀悕鍜屽墠 20 琛?|
| 涓嬭浇 | `GET /api/collect/outputs/{job_id}/{name}` | 涓嬭浇浜岀淮琛ㄣ€佺粺璁°€佽川閲忔姤鍛娿€乵anifest |
| 鏁版嵁闆嗗垪琛?| `GET /api/datasets` | 鏌ョ湅宸蹭繚瀛樻暟鎹泦 |
| 閲嶆柊淇濆瓨 | `POST /api/collect/resave/{job_id}` | 鏂囦欢宸茬敓鎴愪絾鏁版嵁搴撲繚瀛樺け璐ユ椂閲嶈瘯淇濆瓨锛屼笉閲嶆柊閲囬泦 |

CLI 涓?API 璋冪敤鍚屼竴閲囬泦瀹炵幇銆侰LI 鍙劚绂?Web 椤甸潰杩愯锛汚PI 杩愯鍦ㄧ粺涓€浠诲姟涓庨厤缃熀纭€璁炬柦涔嬩笂锛屼絾涓嶈姹備笂娓告ā鍧楀厛杩愯銆?
## 3 鏁版嵁鏉ユ簮妯″紡

### 3.1 Git 浠撳簱妯″紡

杈撳叆锛?
| 杈撳叆 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `repo_source` | 鏄?| 鏈湴璺緞鎴?Git URL锛涙湰鍦拌矾寰勯』鍦ㄥ厑璁告牴鐩綍鍐咃紝URL 鍗忚椤诲湪鐧藉悕鍗曞唴 |
| `branch` | 鍚?| 鍒嗘敮/ref锛岀己鐪佷负浠撳簱榛樿 HEAD |
| `start_time` / `end_time` | 鍚?| ISO 8601 UTC锛岄檺瀹氳緭鍑烘彁浜よ寖鍥?|
| `start_commit` / `end_commit` | 鍚?| 鍙鍑虹殑鎻愪氦鑼冨洿锛屽彲涓庢椂闂磋寖鍥寸粍鍚?|
| `mode` | 鍚?| `full` / `incremental`锛岄粯璁?`incremental` |
| `fetch_remote` | 鍚?| 榛樿 `true`锛沗false` 鐢ㄦ湰鍦?HEAD |
| `head_expect` | 鍚?| 鏈熸湜 HEAD锛屼笉涓€鑷村垯鎷掔粷 |
| `dedup` | 鍚?| 褰撳墠浠?`commit_hash` |
| `szz_method` | 鍚?| `szz_v1` / `szz_lite`锛岄粯璁?`szz_v1` |
| `dataset_name` | 鏄?| 灞曠ず鍜屼繚瀛樼敤鍚嶇О |
| `save_to_db` | 鍚?| 榛樿 `true` |

澶勭悊閾撅細

```text
浠撳簱鏍￠獙 鈫?鎷夊彇/璇诲彇浠撳簱 鈫?閲囬泦鎻愪氦 鈫?SZZ 鎵撴爣 鈫?鐢熸垚浜岀淮琛?鈫?鐢熸垚缁熻淇℃伅 鈫?榛樿淇濆瓨鏁版嵁搴?鈫?鐢熸垚 manifest 鈫?鎻愪緵瀵煎嚭
```

SZZ 杈撳嚭鍙啓鏍囩瀛楁锛屼笉鍐?Kamei 14 缁达紝涓嶇敓鎴?`is_test`銆?
### 3.2 鍏紑鏍囨敞鏁版嵁闆嗘ā寮?
杈撳叆锛?
| 杈撳叆 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `dataset_name` | 鏄?| 灞曠ず鍜屼繚瀛樼敤鍚嶇О |
| `source_url` 鎴栦笂浼犳枃浠?| 鏄?| CSV/JSON/ZIP锛屾垨鍙闂殑鏁版嵁闆?URL |
| `license` | 鏄?| SPDX 鏍囪瘑鎴栧師濮嬭鍙瘉璇存槑 |
| `source_note` | 鏄?| 璁烘枃銆侀」鐩富椤点€佷笅杞藉湴鍧€绛夋潵婧愯鏄?|
| `field_mapping` | 鏄?| 鎻愪氦鏍囪瘑銆佹椂闂淬€佹爣绛惧瓧娈靛埌绯荤粺瀛楁鐨勬槧灏?|
| `label_mapping` | 鏄?| 鍘熷鏍囩鍊煎埌 `1/0/null` 鐨勬槧灏?|
| `save_to_db` | 鍚?| 榛樿 `true` |

澶勭悊閾撅細

```text
鏂囦欢/URL 鏍￠獙 鈫?瀛楁鏄犲皠 鈫?鏍囩褰掍竴鍖?鈫?璐ㄩ噺鏍￠獙 鈫?鐢熸垚浜岀淮琛?鈫?鐢熸垚缁熻淇℃伅 鈫?榛樿淇濆瓨鏁版嵁搴?鈫?鐢熸垚璐ㄩ噺鎶ュ憡鍜?manifest 鈫?鎻愪緵瀵煎嚭
```

鍏紑鏁版嵁闆嗗凡鏈夋爣绛撅紝鏈ā寮?*涓嶆墽琛?SZZ**銆傛爣绛炬潵婧愯涓?`public_dataset`銆?
鍏紑鏁版嵁闆嗚嚦灏戝繀椤诲叿澶囧彲鏄犲皠鐨勬彁浜ゆ爣璇嗗瓧娈靛拰鏍囩瀛楁锛涙椂闂村瓧娈靛缓璁繀濉紝缂哄け鏃跺湪璐ㄩ噺鎶ュ憡涓槑纭爣娉紝骞剁姝㈣繘鍏ヤ緷璧栨椂闂存帓搴忕殑鍚庣画婕旂ず銆?
## 4 杈撳嚭濂戠害

### 4.1 浜岀淮琛?
鏂囦欢鍚嶏細

```text
collected_commits_<job_id>.csv
collected_commits_<job_id>.xlsx
```

鍒楀畾涔夛細

| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| `commit_hash` | string(40 hex) | 鏄?| 鎻愪氦鏍囪瘑锛屽皬鍐?|
| `repo_name` | string | 鏄?| 浠撳簱鍚嶆垨鏁版嵁闆嗗悕 |
| `repo_url` | string | 鍚?| 浠撳簱 URL 鎴栨暟鎹泦鏉ユ簮 URL |
| `author_name` | string | 鍚?| 浣滆€?|
| `author_email` | string | 鍚?| 浣滆€呴偖绠?|
| `committed_at` | datetime | 鍚?| 鎻愪氦鏃堕棿锛孶TC ISO 8601 |
| `message` | string | 鍚?| 鎻愪氦淇℃伅 |
| `parent_hash` | string(40) | 鍚?| 鐖舵彁浜?|
| `is_bug_inducing` | int 绌哄彲 | 鏄?| 鏍囩锛?/0/绌?|
| `label_method` | string | 鍚?| `szz_v1` / `szz_lite` / `third_party` |
| `label_source` | string | 鏄?| `git_szz` / `public_dataset` |
| `labeled_at` | datetime | 鍚?| 鎵撴爣鏃堕棿鎴栨潵婧愭椂闂?|
| `fix_commit_hash` | string(40) | 鍚?| SZZ 鍥炴函鍒扮殑淇鎻愪氦 |
| `source_type` | string | 鏄?| `git_repo` / `public_dataset` |

纭害鏉燂細

- 涓嶅嚭鐜?Kamei 14 缁寸壒寰佸垪锛坄ns,nd,nf,entropy,la,ld,lt,fix,ndev,age,nuc,exp,rexp,sexp`锛夈€?- 涓嶅嚭鐜?`is_test`銆?- 鏈墦鏍?`is_bug_inducing` 淇濇寔绌哄€硷紝MUST NOT 鍐?0銆?- CSV 浣跨敤 UTF-8 BOM锛沊LSX 鍗?sheet锛涜〃澶?ASCII snake_case銆?
### 4.2 缁熻淇℃伅

```text
collect_summary_<job_id>.json
```

鑷冲皯鍖呭惈锛?
- `source_type`銆乣source_url`銆乣dataset_name`銆?- `label_source`銆乣szz_method` 鎴栫涓夋柟鏍囩璇存槑銆?- `total_rows`銆乣positive_rows`銆乣negative_rows`銆乣unlabeled_rows`銆?- `duplicate_rows`銆乣skipped_rows`銆?- Git 妯″紡鐨勫垎鏀€丠EAD銆佹椂闂?鎻愪氦鑼冨洿銆?- 鍏紑鏁版嵁闆嗘ā寮忕殑璁稿彲璇併€佹潵婧愩€佸瓧娈垫槧灏勬憳瑕併€?- `save_db_status`銆乣dataset_id`銆?
### 4.3 璐ㄩ噺鎶ュ憡

鍏紑鏁版嵁闆嗘ā寮忛澶栫敓鎴愶細

```text
collect_quality_<job_id>.json
collect_quality_<job_id>.md
```

鑷冲皯鍖呭惈锛?
- 缂哄け鐜囥€?- 閲嶅鎻愪氦鏁般€?- 鏍囩鍐茬獊鏁般€?- 鏃堕棿寮傚父鏁般€?- 瀛楁鏄犲皠琛ㄣ€?- 寮傚父鏍锋湰绀轰緥鍜屽缃缓璁€?
### 4.4 manifest

姣忎釜涓讳骇鐗╁悓鍚?manifest锛?
```text
collected_commits_<job_id>.manifest.json
```

瀛楁閬靛惊 file-contracts 搂3.9锛屽苟琛ュ厖锛?
- `source_type`
- `label_source`
- `license`锛堝叕寮€鏁版嵁闆嗭級
- `source_url`
- `save_db_status`
- `dataset_id`

## 5 鍙厤缃」

| 閰嶇疆 | 鏉ユ簮 | 榛樿 / 绾︽潫 |
|---|---|---|
| `collect.allow_roots` | `user_config` | Git 鏈湴璺緞涓庡厠闅嗙洰褰曞厑璁告牴 |
| `collect.protocol_whitelist` | `user_config` | 榛樿鍙厑璁?https/git |
| `default_dataset` | `user_config` | 浠呬究鍒╅€夋嫨锛屼笉鏄繍琛屽墠鎻?|
| Git 閲囬泦鍙傛暟 | 鏈 run | 瀹屾暣蹇収鍏?`job.params_json` 涓?manifest |
| 鍏紑鏁版嵁闆嗗瓧娈垫槧灏?| 鏈 run | 蹇呴』鏄惧紡澹版槑锛屼笉鍏佽闈欓粯鐚滄祴 |
| 鏍囩鍊兼槧灏?| 鏈 run | 蹇呴』瑕嗙洊杈撳叆涓嚭鐜扮殑鎵€鏈夊師濮嬫爣绛惧€?|
| `save_to_db` | 鏈 run | 榛樿 `true` |
| 杈撳嚭鏍煎紡 | 鏈 run | CSV 榛樿锛孹LSX 鍙€?鍚屾壒鐢熸垚 |

## 6 鐘舵€佷笌鎸佷箙鍖?
- `job.kind=collect`锛屼簲鎬?`queued / running / success / failed / cancelled`銆?- 杩涘害闃舵锛氭媺鍙?瀵煎叆銆侀噰闆?鏄犲皠銆丼ZZ 鎴栨爣绛惧綊涓€鍖栥€佺敓鎴愪簩缁磋〃銆佷繚瀛樻暟鎹簱銆佺敓鎴愬鍑烘枃浠躲€?- 鍚?kind 鍚屼竴鏃跺埢鏈€澶氫竴涓?running銆?- 杩涚▼閲嶅惎閬楃暀 running 缃?failed锛屼繚鐣欒繘搴﹀拰鑴辨晱鏃ュ織锛屽彲閲嶈瘯銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`銆?- 榛樿淇濆瓨鏁版嵁搴擄細鎴愬姛鍚庡啓 `dataset` 涓?`dataset_commit`銆?- 鑻ユ枃浠剁敓鎴愭垚鍔熶絾鏁版嵁搴撲繚瀛樺け璐ワ細
  - `job.status=failed`锛?  - `error_log` 鍐欐槑淇濆瓨澶辫触鍘熷洜锛?  - 鏂囦欢浜х墿浠嶅彲涓嬭浇锛?  - 椤甸潰鎻愪緵鈥滈噸鏂颁繚瀛樷€濆叆鍙ｃ€?- 鐩稿悓杈撳叆涓庨厤缃噸璺戝簲浜х敓绛変环浜岀淮琛紱鍚屼竴鏁版嵁闆嗗唴鎸?`commit_hash` 骞傜瓑銆?
## 7 涓庡叾浠栨ā鍧楄竟鐣?
- clean/train 鍚庣画鍙秷璐规湰妯″潡浜у嚭鐨?`collected_commits.csv`锛屼笉鍐嶅亣璁惧叾涓寘鍚?Kamei 14 缁村拰 `is_test`銆?- 鏉垮潡 3 璐熻矗鐗瑰緛鎻愬彇銆佹竻娲楀拰棰勫鐞嗭紱鍒囧垎璁粌/娴嬭瘯闆嗗綊鏉垮潡 4 璁粌閰嶇疆銆?- 鏈ā鍧椾笉璋冪敤 clean/train/predict/evaluate/explain/localization銆?- storage 鍙槸鏈ā鍧楅粯璁よ惤搴撶殑瀹炵幇鏀拺锛屼笉鏇夸唬鏂囦欢浜х墿锛涘叕寮€鏁版嵁闆嗕篃蹇呴』钀界洏鏂囦欢涓?manifest銆?- 鏁版嵁闆嗗垪琛ㄦ槸淇濆瓨缁撴灉灞曠ず锛屼笉鍙備笌妯″潡闂存枃浠?handoff銆?
## 8 楠屾敹鏍囧噯

- 鐢ㄦ埛鍙～鍐欎换鎰忓悎娉曟湰鍦颁粨搴撹矾寰勬垨 Git URL 骞跺彂璧锋敹闆嗭紝涓嶄慨鏀圭幆澧冨彉閲忋€?- 绯荤粺瀹屾垚鎷夊彇銆佹彁浜ら噰闆嗗拰 SZZ 鎵撴爣锛岃緭鍑轰簩缁磋〃涓嶅惈 14 缁寸壒寰佸拰 `is_test`銆?- 鏈墦鏍囨牱鏈繚鎸佺┖鍊硷紝涓嶈鍐欐垚 0銆?- 鍏紑鏁版嵁闆嗗彲閫氳繃瀛楁鏄犲皠瀵煎叆锛屾爣绛炬潵婧愭爣璁颁负 `public_dataset`锛屼笉鎵ц SZZ銆?- 浜岀淮琛ㄩ粯璁や繚瀛樻暟鎹簱锛屾暟鎹泦鍒楄〃鍙煡璇紱淇濆瓨澶辫触鏃舵枃浠朵粛鍙笅杞戒笖鍙噸璇曚繚瀛樸€?- CSV/XLSX 鍙墦寮€銆佷腑鏂囦笉涔辩爜锛屽唴瀹逛笌鏁版嵁搴撲簩缁磋〃涓€鑷淬€?- summary銆乹uality锛堝叕寮€鏁版嵁闆嗭級銆乵anifest 鍧囧彲涓嬭浇锛宑hecksum 涓€鑷淬€?- 鍚岄厤缃噸澶嶈繍琛屾棤閲嶅鎴愬憳锛涗粨搴撹秺鐣屻€佸崗璁潪娉曘€佸瓧娈电己澶便€佹爣绛炬槧灏勪笉瀹屾暣銆丠EAD 涓嶇鍧囨湁鏄庣‘閿欒銆?- job 浜旀€併€佸彇娑堛€侀噸璇曘€侀噸鍚腑鏂仮澶嶅潎閫氳繃銆?