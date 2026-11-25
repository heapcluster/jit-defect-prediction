# 鏁版嵁娓呮礂涓庨澶勭悊锛堝姛鑳?3锛?
瀹炵幇鐘舵€侊細鐩爣濂戠害銆€鏈熸锛氫竴鏈?
> 鏃у疄鐜颁腑瀛樺湪 `szz_label`銆乣d5_exclude`銆乣time_split`銆乣is_test`銆乣feature_build`銆並amei 14 缁撮粯璁ゅ浘鍜岃缁冧晶鍙樻崲锛涙湰鏂囧凡搴熸銆傛湰杞彧淇敼璁捐鏂囨。锛屼唬鐮佸悗缁寜鏈枃鍚屾銆?
## 涓€鍙ヨ瘽姒傝堪

鐙珛鐨勬暟鎹竻娲椾笌棰勫鐞嗗伐鍏凤細涓婁紶鏉垮潡 2 浜у嚭鐨?`collected_commits.csv/xlsx`锛屾寜鐢ㄦ埛閫夋嫨鐨勫父鐢ㄦ竻娲楁搷浣滃拰閫氱敤棰勫鐞嗘搷浣滅敓鎴愭竻娲楀悗鏁版嵁闆嗭紱姣忎竴姝ュ睍绀烘暟鎹泦鍙樺寲鍜屾寚瀹氬垪/鍩虹鐗瑰緛鍙樺寲锛岀粨鏋滃彲瀵煎嚭 CSV/XLSX銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

**璐熻矗**锛?
- 鎻愪緵鍒嗙粍鎿嶄綔娉ㄥ唽琛細甯哥敤娓呮礂鎿嶄綔銆侀€氱敤棰勫鐞嗘搷浣溿€?- 鏀寔鐢ㄦ埛閫夋嫨銆佹帓搴忋€佸惎鍋溿€侀厤缃瘡涓搷浣溿€?- 鏀寔 `preview` / `apply` 涓ょ妯″紡锛?  - `preview` 鍙骇鍑烘瘡姝ョ粺璁″拰鍥捐〃銆?  - `apply` 棰濆浜у嚭娓呮礂鍚庢暟鎹泦銆?- 瀵规瘡涓€姝ヨ褰曞鐞嗗墠鍚庤鏁般€佸垹闄?淇敼琛屾暟銆佹爣绛惧垎甯冦€佺己澶卞€笺€侀噸澶嶆暟鍜屾帓闄ゅ師鍥犮€?- 瀵圭敤鎴锋寚瀹氬垪/鍩虹鐗瑰緛灞曠ず澶勭悊鍓嶅悗鍒嗗竷鍙樺寲锛涜嫢娌℃湁鎸囧畾鍒楋紝鍒欒嚦灏戝睍绀烘暟鎹泦绾у彉鍖栥€?- 浜у嚭 `clean_dataset_<job_id>.csv/xlsx`銆佺粺璁°€佸浘琛ㄣ€乵anifest銆?- 淇濊瘉鍚岃緭鍏ャ€佸悓澶勭悊閾俱€佸悓閰嶇疆鍙鐜般€?
**涓嶈礋璐?*锛?
- Git 鎷夊彇銆丼ZZ 鎵撴爣銆丏5 鍥炴函涓庝慨澶嶅€欓€夊垽瀹氥€?- 璁粌/娴嬭瘯闆嗗垏鍒嗐€乣is_test` 鐢熸垚銆?- Kamei 14 缁淬€佽涔夊悜閲忋€佽瀺鍚堢壒寰併€佺鍒扮鏂囨湰鐗瑰緛绛?*妯″瀷鐗瑰緛**鐨勭敓鎴愩€侀€夋嫨鎴栭攣瀹氥€?- 璁粌渚?`log_transform` / `standardize` / `categorical_encode` / `feature_select`銆?- 妯″瀷璁粌銆侀娴嬨€佽瘎浼般€佽В閲娿€佸畾浣嶃€?- 鎶婃暟鎹簱鎴栭〉闈綔涓鸿繍琛屽墠鎻愩€?- 鎶婃竻娲楃粨鏋滃己鍒跺啓鍏ユ暟鎹簱銆?
妯″瀷鐗瑰緛涓庤缁冧晶鍙樻崲缁熶竴灞炰簬鏉垮潡 4銆屾ā鍨嬭缁冦€嶃€?
## 2 鐙珛杩愯鍏ュ彛

| 鍏ュ彛 | 鍛戒护 / 绔偣 | 濂戠害 |
|---|---|---|
| CLI | `python -m preparation.clean run --input collected_commits.csv --chain chain.json --mode apply --out ./out` | 鏂囦欢涓庡鐞嗛摼鍗冲彲杩愯 |
| CLI | `python -m preparation.clean operations` | 鏌ヨ鎿嶄綔娉ㄥ唽琛?|
| 娉ㄥ唽琛?API | `GET /api/clean/operations` | 杩斿洖娓呮礂/閫氱敤棰勫鐞嗘搷浣滃厓鏁版嵁 |
| 浠诲姟 API | `POST /api/clean/run` | multipart 涓婁紶 CSV/XLSX + `config`锛岃繑鍥?`job_id` |
| 浠诲姟绠＄悊 | `GET /api/jobs/{id}`銆乣POST /api/jobs/{id}/retry\|cancel` | 浜旀€併€佽繘搴︺€佹棩蹇?|
| 棰勮 | `GET /api/clean/preview/{job_id}` | 浠?apply 鎴愬姛鍚庤繑鍥炴竻娲楀悗鏁版嵁闆嗗墠 20 琛?|
| 涓嬭浇 | `GET /api/clean/outputs/{job_id}/{name}` | 涓嬭浇娓呮礂鍚庢暟鎹泦銆佺粺璁°€佸浘銆乵anifest |

CLI 涓?API 璋冪敤鍚屼竴澶勭悊閾惧疄鐜般€?
## 3 杈撳叆濂戠害

涓昏緭鍏ユ槸 [`../file-contracts.md`](../file-contracts.md) 搂3.1 鐨勶細

```text
collected_commits_<job_id>.csv / xlsx
```

鍙敤鍒楋細

```text
commit_hash, repo_name, repo_url, author_name, author_email,
committed_at, message, parent_hash,
is_bug_inducing, label_method, label_source,
labeled_at, fix_commit_hash, source_type
```

鍙€夎緭鍏ュ彧鏈夊悓鍚?manifest锛岀敤浜庢牎楠?checksum 涓庢潵婧愪俊鎭€?
鏈ā鍧椾笉鍐嶆帴鍙楋細

```text
repo_source
feature_file
feature_plan
feature_set
```

杩欎簺瀛楁鑻ュ嚭鐜帮紝杩斿洖 40001锛屽苟鎻愮ず鈥滄ā鍨嬬壒寰侀厤缃鍦ㄨ缁冮樁娈垫彁渚涒€濄€?
杈撳叆绾︽潫锛?
- 鏂囦欢鍚嶄笉鍐嶅亣瀹氫负 `commits.csv`銆?- 涓嶈姹傝緭鍏ュ凡鏈?Kamei 14 缁淬€?- 涓嶈姹傝緭鍏ュ凡鏈?`is_test`銆?- 鏈墦鏍?`is_bug_inducing` 蹇呴』淇濇寔绌哄€笺€?- CSV 浣跨敤 UTF-8/UTF-8 BOM锛沊LSX 鍗?sheet锛涜〃澶翠负 snake_case銆?
## 4 鎿嶄綔娉ㄥ唽琛?
鎿嶄綔娉ㄥ唽琛ㄥ繀椤荤敱鍚庣鎻愪緵锛屽墠绔笉寰楃‖缂栫爜銆?
### 4.1 甯哥敤娓呮礂鎿嶄綔

| 鎿嶄綔 | 鑱岃矗 | 榛樿鍙傛暟 / 绾︽潫 |
|---|---|---|
| `schema_validate` | 鏍￠獙鍒椼€佺被鍨嬨€佸搱甯屾牸寮忋€佹椂闂存牸寮忋€佹爣绛惧€煎煙 | 濮嬬粓鍏堟墽琛岋紝涓嶅彲鍏抽棴 |
| `duplicate_drop` | 鎸?`commit_hash` 鍘婚噸 | 榛樿淇濈暀棣栬锛岄噸澶嶆牱鏈啓鍏ユ帓闄ゆ槑缁?|
| `merge_commit_filter` | 鏍规嵁 `parent_hash` 涓涓湁鏁堢埗鍝堝笇杩囨护鍚堝苟鎻愪氦 | 涓嶄粠 message 鐚滄祴 |
| `missing_value_handle` | 澶勭悊浣滆€呫€侀偖绠便€佹椂闂淬€佹秷鎭瓑缂哄け鍊?| 绛栫暐锛歚keep` / `fill` / `exclude`锛岄粯璁?`keep` |
| `invalid_time_filter` | 杩囨护闈炴硶鏃堕棿鎴栬秴鍑鸿寖鍥寸殑鏃堕棿 | 榛樿鎺掗櫎闈炴硶鏃堕棿 |
| `unlabeled_handle` | 澶勭悊鏈墦鏍囨牱鏈?| 绛栫暐锛歚keep` / `exclude` / `warn`锛岄粯璁?`keep` |
| `outlier_filter` | 瀵瑰凡鏈夋暟鍊煎垪鍋氬紓甯告娴?| 鏂规硶 `iqr` / `zscore`锛岄粯璁?`iqr`锛涗笉鐢熸垚妯″瀷鐗瑰緛 |
| `label_validate` | 鏍￠獙鏍囩鍙兘鏄?1 / 0 / 绌?| 榛樿寮€鍚紱NULL 涓嶅～ 0 |
| `text_clean` | 娓呮礂 `message` 鏂囨湰 | 鍘婚灏剧┖鐧姐€佹帶鍒跺瓧绗︺€佸浣欐崲琛?|

### 4.2 閫氱敤棰勫鐞嗘搷浣?
| 鎿嶄綔 | 鑱岃矗 | 榛樿鍙傛暟 / 绾︽潫 |
|---|---|---|
| `type_convert` | 鎶婂瓧绗︿覆鏃堕棿/鏁板瓧杞负缁熶竴绫诲瀷 | 鐢辩敤鎴锋寚瀹氬垪锛涗笉浜х敓妯″瀷鐗瑰緛闆?|
| `date_normalize` | 缁熶竴鏃堕棿涓?UTC ISO 8601 | 浣滅敤浜?`committed_at` / `labeled_at` |
| `text_normalize` | 缁熶竴鏂囨湰绌虹櫧鍜屾崲琛?| 浣滅敤浜?`message` 绛夋枃鏈垪 |
| `category_normalize` | 缁熶竴绫诲埆鍊煎啓娉曪紝濡傚ぇ灏忓啓鍜岀┖鐧?| 涓嶅仛妯″瀷缂栫爜锛屽彧鍋氬€艰鑼冨寲 |
| `derive_basic_fields` | 娲剧敓鍩虹灞曠ず鍒楋紝濡?`message_length`銆乣parent_count`銆乣commit_hour` | 榛樿鍏抽棴锛涗笉寰楃敓鎴?Kamei 14 缁淬€佽涔夊悜閲忔垨妯″瀷杈撳叆鐗瑰緛 |

`derive_basic_fields` 鍙槸鏁版嵁鏌ョ湅鍜屽彉鍖栧浘鐢ㄧ殑鍩虹鍒楋紝涓嶆槸妯″瀷鐗瑰緛宸ョ▼銆傛ā鍨嬭缁冮渶瑕佸摢浜涚壒寰侊紝鐢辨澘鍧?4 鍐冲畾銆?
### 4.3 宸茬Щ闄ゆ搷浣?
浠ヤ笅鎿嶄綔涓嶅啀灞炰簬鏉垮潡 3锛?
| 鏃ф搷浣?| 鐜板綊灞?|
|---|---|
| `szz_label` | 鏉垮潡 2锛孲ZZ 鎵撴爣 |
| `d5_exclude` | 鏉垮潡 2锛孲ZZ 璐ㄩ噺鎺у埗 |
| `time_split` | 鏉垮潡 4锛岃缁冮厤缃?|
| `feature_build` | 鏉垮潡 4锛岃缁冩椂鎸夋ā鍨嬬嚎鐢熸垚妯″瀷鐗瑰緛 |
| `feature_align` | 鏉垮潡 4锛岃缁冩椂閿佸畾鐗瑰緛鍒?|
| `log_transform` | 鏉垮潡 4锛岃缁冧晶棰勫鐞?|
| `standardize` | 鏉垮潡 4锛岃缁冧晶棰勫鐞?|
| `categorical_encode` | 鏉垮潡 4锛岃缁冧晶棰勫鐞?|
| `feature_select` | 鏉垮潡 4锛岃缁冩椂閫夋嫨妯″瀷鐗瑰緛 |

### 4.4 椤哄簭绾︽潫

- `schema_validate` 蹇呴』绗竴姝ャ€?- 娓呮礂鎿嶄綔蹇呴』鍏堜簬閫氱敤棰勫鐞嗘搷浣溿€?- `date_normalize` 蹇呴』鍏堜簬浠讳綍鍩轰簬鏃堕棿鐨勫熀纭€娲剧敓銆?- `derive_basic_fields` 鍙兘娲剧敓鍩虹鍒楋紝涓嶅緱鐢熸垚妯″瀷鐗瑰緛銆?- 涓嶅厑璁镐换浣曡缁冩祴璇曞垏鍒嗘垨妯″瀷鐗瑰緛閫夋嫨鎿嶄綔銆?
## 5 杈撳嚭濂戠害

### 5.1 娓呮礂鍚庢暟鎹泦

鏂囦欢鍚嶏細

```text
clean_dataset_<job_id>.csv
clean_dataset_<job_id>.xlsx
```

瀛楁锛?
- 淇濈暀 搂3.1 鐨勫師濮嬪垪锛屾寜娓呮礂缁撴灉鏇存柊銆?- 鍙拷鍔?`derive_basic_fields` 鐢熸垚鐨勫熀纭€鍒椼€?- 涓嶇敓鎴?Kamei 14 缁淬€佽涔夊悜閲忋€佽瀺鍚堢壒寰佹垨妯″瀷杈撳叆鐗瑰緛銆?- 涓嶅嚭鐜?`is_test`銆?- 涓嶅嚭鐜拌缁?娴嬭瘯鍒掑垎鍒椼€?- 鏈墦鏍?`is_bug_inducing` 淇濇寔绌恒€?
瀵煎嚭瑕佹眰锛?
- CSV 浣跨敤 UTF-8 BOM銆?- XLSX 鍗?sheet銆?- apply 妯″紡鎵嶇敓鎴愪富琛ㄣ€?- preview 妯″紡涓嶇敓鎴愪富琛ㄣ€?
### 5.2 姣忔鏁版嵁闆嗗彉鍖?
```text
clean_steps_stats_<job_id>.json
```

姣忎竴姝ュ繀椤诲寘鍚細

```text
step
rows_before
rows_after
removed_rows
modified_rows
label_dist_before
label_dist_after
missing_before
missing_after
duplicate_before
duplicate_after
elapsed_ms
excluded_samples
```

瀵瑰簲鍥撅細

```text
clean_dataset_change_<step>_<job_id>.png
```

鍥句腑鑷冲皯灞曠ず锛?
- 琛屾暟鍓嶅悗瀵规瘮銆?- 鏍囩鍒嗗竷鍓嶅悗瀵规瘮銆?- 缂哄け/閲嶅鍙樺寲銆?
### 5.3 鎸囧畾鍒?鍩虹鐗瑰緛鍙樺寲

```text
clean_column_stats_<job_id>.json
clean_column_distribution_<step>_<column>_<job_id>.png
```

瀵规瘡涓寚瀹氬垪璁板綍锛?
```text
mean
median
std
min
max
quantiles
missing_count
```

鍥捐〃绫诲瀷锛?
- 鏁板€煎垪锛氱洿鏂瑰浘銆佺绾垮浘銆佸瘑搴﹀浘銆?- 绫诲埆鍒楋細棰戞暟鏌辩姸鍥俱€?
鑻ユ病鏈夋寚瀹氬垪锛屾暟鎹泦绾у浘蹇呴』浜у嚭锛屽垪绾у浘鍙负绌哄苟鍦?manifest 鏍囪鍘熷洜銆?
### 5.4 manifest

姣忎釜涓讳骇鐗╁悓鍚?manifest锛岄伒寰?file-contracts 搂3.9锛屽苟璁板綍锛?
```text
source_type = collected_commits
chain_config
chart_columns
derived_columns
column_schema
input_checksum
output_checksum
mode
```

涓嶅啀璁板綍 `feature_schema`锛涙ā鍨嬬壒寰?schema 鐢辨澘鍧?4 鍐欏叆 `model_package.zip`銆?
## 6 鍙厤缃」

| 閰嶇疆 | 鏉ユ簮 | 璇存槑 |
|---|---|---|
| `clean.chain_templates` | `user_config` | 鍙鐢ㄥ鐞嗛摼妯℃澘 |
| `steps[]` | 鏈 run | 鎿嶄綔銆佸惎鍋溿€佸弬鏁?|
| `chart_columns[]` | 鏈 run | 闇€瑕佺敾鍓嶅悗鍙樺寲鍥剧殑鍒?鍩虹鐗瑰緛 |
| `mode` | 鏈 run | `preview` / `apply` |
| `format` | 鏈 run | `csv` / `xlsx` |

涓嶅啀鎻愪緵锛?
- `repo_source`
- `feature_file`
- `seed`
- `split_ratio`
- `feature_set`

## 7 鐘舵€佹寔涔呭寲

- `job.kind=clean`锛屼簲鎬?`queued / running / success / failed / cancelled`銆?- 浠诲姟淇濆瓨妯″紡銆佸鐞嗛摼銆佸浘琛ㄥ垪銆佽繘搴︺€侀敊璇棩蹇椼€佽緭鍏ヨ緭鍑哄紩鐢ㄣ€?- preview 涓嶄骇涓昏〃锛沘pply 鎵嶄骇 `clean_dataset`銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`銆?- 鍚岃緭鍏ャ€佸悓閾俱€佸悓閰嶇疆閲嶈窇锛屼富琛ㄣ€佺粺璁″拰鍥捐〃鏁板€间竴鑷淬€?- 妯℃澘鍚庣画鍙樺寲涓嶅奖鍝嶅巻鍙蹭换鍔★紝鍘嗗彶閰嶇疆鍥哄寲鍦?job 涓?manifest銆?
## 8 涓庡叾浠栨ā鍧楄竟鐣?
- 涓?collect 鐨勫叧绯讳粎涓?搂3.1 鏂囦欢 schema 鍏煎銆?- 涓嶈皟鐢?collect 鍦ㄧ嚎鏈嶅姟锛屼笉渚濊禆鏁版嵁搴撳凡鏈夋暟鎹泦銆?- 涓嶅啓 `dataset` / `dataset_commit`銆?- 涓嶉噸鏂版墽琛?SZZ锛屼笉鏀瑰彉 `label_source`銆?- train 鍚庣画娑堣垂鏈ā鍧楃殑 `clean_dataset` 鏂囦欢锛屽苟鍦ㄨ缁冮樁娈甸€夋嫨妯″瀷鐗瑰緛銆佸垏鍒嗘暟鎹拰鎷熷悎璁粌渚у彉鎹€?- storage 涓庢湰妯″潡鏃犲叧锛涙竻娲楃粨鏋滈€氳繃鏂囦欢 handoff銆?
## 9 楠屾敹鏍囧噯

- 绌哄簱涓旀湭杩愯 collect 鏃讹紝CLI 鍜?API 鍧囧彲浠呭嚟涓婁紶鐨?`collected_commits.csv/xlsx` 瀹屾垚 preview 涓?apply銆?- 鎿嶄綔娉ㄥ唽琛ㄥ垎缁勫睍绀烘竻娲?閫氱敤棰勫鐞嗘搷浣滐紝鍓嶇涓嶇‖缂栫爜銆?- 鐢ㄦ埛鍙€夋嫨銆佹帓搴忋€佸惎鍋溿€侀厤缃搷浣滐紱闈炴硶椤哄簭銆佹湭鐭ユ搷浣溿€佸弬鏁拌秺鐣屽墠缃嫆缁濄€?- `feature_build` / 妯″瀷鐗瑰緛閫夋嫨 / 璁粌娴嬭瘯鍒囧垎璇锋眰琚嫆缁濓紝骞舵寚鍚戣缁冮樁娈点€?- preview 浜у嚭姣忔鏁版嵁闆嗗彉鍖栧拰鎸囧畾鍒楀彉鍖栧浘锛屼笉浜ф竻娲楀悗鏁版嵁闆嗐€?- apply 棰濆浜у嚭 `clean_dataset_<job_id>.csv/xlsx`锛屾敮鎸?CSV/Excel 瀵煎嚭銆?- 姣忎竴姝ラ兘鑳界湅鍒拌鏁般€佹爣绛惧垎甯冦€佺己澶卞€笺€侀噸澶嶆暟鍜屾帓闄ゆ牱鏈彉鍖栥€?- 閫夋嫨鎸囧畾鍒楀悗鑳界湅鍒拌鍒楀鐞嗗墠鍚庡垎甯冨浘銆?- 杈撳嚭涓嶅惈 `is_test`銆佽缁?娴嬭瘯鍒掑垎鍒楀拰妯″瀷鐗瑰緛闆嗐€?- 鏈墦鏍囨牱鏈繚鎸佺┖鍊硷紝涓嶅啓 0銆?- 鐩稿悓杈撳叆鍜岀浉鍚岄厤缃彲澶嶇幇銆?- 杈撳嚭 manifest銆乧hecksum銆佸浘琛ㄥ拰缁熻鏂囦欢瀹屾暣銆?