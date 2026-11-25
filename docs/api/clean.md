# 鏁版嵁娓呮礂涓庨澶勭悊 API锛坈lean锛?
瀹炵幇鐘舵€侊細鐩爣濂戠害銆€鏈熸锛氫竴鏈?
> 鏃?API 鍙ｅ緞鍖呭惈 `commits.csv`銆乣szz_label`銆乣d5_exclude`銆乣time_split`銆乣is_test`銆乣feature_build`銆並amei 14 缁存ā鍨嬬壒寰侊紱鏈枃宸插簾姝€傛湰杞彧淇敼璁捐鏂囨。銆?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔`../file-contracts.md`](../file-contracts.md) 搂3.1銆伮?.2銆伮?.9锛涘叕鍏卞彛寰勮 [README.md](README.md)銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗鎿嶄綔娉ㄥ唽琛ㄣ€佸鐞嗛摼鏍￠獙銆乸review/apply銆佹瘡姝ユ暟鎹泦鍙樺寲缁熻銆佹寚瀹氬垪鍙樺寲缁熻銆佸浘琛ㄥ拰娓呮礂鍚庢暟鎹泦鏂囦欢浜や粯銆?- 杈撳叆涓烘澘鍧?2 鐨?`collected_commits.csv/xlsx`銆?- 涓嶆墽琛?SZZ銆丏5銆丟it 鎷夊彇銆?- 涓嶇敓鎴?`is_test`锛屼笉鍋氳缁?娴嬭瘯鍒囧垎銆?- 涓嶇敓鎴愭垨閫夋嫨妯″瀷鐗瑰緛锛汯amei 14 缁淬€佽涔夊悜閲忋€佽瀺鍚堢壒寰併€佺鍒扮鏂囨湰鐗瑰緛鍧囧湪璁粌闃舵澶勭悊銆?- 涓嶅仛璁粌渚?`log_transform` / `standardize` / `categorical_encode` / `feature_select`銆?- 涓嶈缁冩ā鍨嬨€佷笉璇勪及銆佷笉瑙ｉ噴銆佷笉瀹氫綅銆?- 涓嶈姹傛暟鎹簱鏈変笂娓告暟鎹紱涓嶅啓 `dataset` / `dataset_commit`銆?
## 2 绔偣濂戠害

### GET /api/clean/operations

鏃犺姹傚弬鏁般€傚搷搴?`data.operations[]`锛屾瘡涓搷浣滃寘鍚細

```text
op
group = cleaning | preprocessing
name
description
input_schema
output_schema
params_schema[]
order_constraints[]
supports_preview
```

涓€鏈熸搷浣滐細

娓呮礂锛?
```text
schema_validate
duplicate_drop
merge_commit_filter
missing_value_handle
invalid_time_filter
unlabeled_handle
outlier_filter
label_validate
text_clean
```

閫氱敤棰勫鐞嗭細

```text
type_convert
date_normalize
text_normalize
category_normalize
derive_basic_fields
```

### POST /api/clean/run

`multipart/form-data`銆?
鏂囦欢锛?
| part | 蹇呭～ | 璇存槑 |
|---|---|---|
| `files[]` | 鏄?| `collected_commits.csv/xlsx` |
| 鍚屽悕 manifest | 鍚?| 鎻愪緵鏃舵牎楠?checksum 涓庢潵婧?|

`config` JSON part锛?
| 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `mode` | 鏄?| `preview` / `apply` |
| `steps[]` | 鏄?| 鏈夊簭鏁扮粍锛歚{op,enabled,params}` |
| `chart_columns[]` | 鍚?| 闇€瑕佸墠鍚庡彉鍖栧浘鐨勫垪/鍩虹鐗瑰緛锛涘彲涓虹┖ |
| `format` | 鍚?| `csv` / `xlsx`锛岄粯璁?`csv` |

绂佹瀛楁锛?
```text
repo_source
feature_file
feature_set
feature_plan
feature_build
feature_align
log_transform
standardize
categorical_encode
feature_select
split_ratio
seed
is_test
```

鏀跺埌绂佹瀛楁杩斿洖 40001锛屽苟鎻愮ず妯″瀷鐗瑰緛涓庤缁冨垏鍒嗗睘浜庤缁冮樁娈点€?
鍝嶅簲锛?
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "j-123",
    "status": "queued"
  }
}
```

灏忔枃浠跺彲鍚屾瀹屾垚锛涘ぇ鏂囦欢璧板紓姝?job銆傚悓 kind 鍚屾椂鏈€澶氫竴涓?running銆?
### GET /api/clean/preview/{job_id}

浠?apply 鎴愬姛鎻愪緵锛?
```json
{
  "columns": [],
  "preview": []
}
```

鏈€澶氬墠 20 琛岋紱绌烘爣绛捐繑鍥?`null`銆俻review 妯″紡娌℃湁涓昏〃锛岃繑鍥?40001銆?
### GET /api/clean/outputs/{job_id}/{name}

涓嬭浇宸茬櫥璁颁骇鐗┿€傚厑璁稿悕绉帮細

```text
clean_dataset_<job_id>.csv
clean_dataset_<job_id>.xlsx
clean_steps_stats_<job_id>.json
clean_column_stats_<job_id>.json
clean_dataset_change_<step>_<job_id>.png
clean_column_distribution_<step>_<column>_<job_id>.png
clean_dataset_<job_id>.manifest.json
```

`name` 蹇呴』鍑虹幇鍦?manifest `outputs[]`锛岀姝㈣矾寰勫垎闅旂鍜?`..`銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 鏈煡鎿嶄綔銆侀『搴忓啿绐併€佺姝㈠瓧娈点€侀潪娉?schema銆佸叕寮忔敞鍏?|
| 40100 | 401 | 缂哄け鎴栭敊璇?`X-API-Key` |
| 40400 | 404 | job 鎴栬緭鍑轰笉瀛樺湪 |
| 50000 | 500 | 鏈鏈熼敊璇紱杩愯鏈熷け璐ュ啓鑴辨晱鏃ュ織 |

## 3 杈撳叆濂戠害

涓昏〃涓ユ牸寮曠敤 [`../file-contracts.md`](../file-contracts.md) 搂3.1锛?
```text
commit_hash, repo_name, repo_url, author_name, author_email,
committed_at, message, parent_hash,
is_bug_inducing, label_method, label_source,
labeled_at, fix_commit_hash, source_type
```

鏍￠獙锛?
- `commit_hash` 40 浣嶅皬鍐?hex銆?- `is_bug_inducing` 鍙兘 1 / 0 / 绌恒€?- `label_source` 鍙兘 `git_szz` / `public_dataset`銆?- CSV UTF-8/UTF-8 BOM锛沊LSX 鍗?sheet銆?- 涓嶅厑璁稿叕寮忔敞鍏ュ崟鍏冩牸銆?- 涓嶈姹?14 缁寸壒寰佸垪銆?- 涓嶅厑璁?`is_test` 鍒楄繘鍏ワ紱鑻ヨ緭鍏ュ寘鍚?`is_test`锛屽拷鐣ュ苟鍦?manifest 璁板綍鏉ユ簮璀﹀憡銆?
## 4 澶勭悊閾捐鍒?
- `schema_validate` 蹇呴』绗竴姝ヤ笖涓嶅彲鍏抽棴銆?- 娓呮礂鎿嶄綔蹇呴』鍏堜簬閫氱敤棰勫鐞嗘搷浣溿€?- `date_normalize` 蹇呴』鍏堜簬浠讳綍鍩轰簬鏃堕棿鐨勫熀纭€娲剧敓銆?- `derive_basic_fields` 鍙兘娲剧敓鍩虹鍒楋紝涓嶅緱鐢熸垚妯″瀷鐗瑰緛銆?- 涓嶅厑璁?SZZ銆丏5銆佹椂闂村垏鍒嗐€佹ā鍨嬬壒寰佺敓鎴愭垨璁粌渚у彉鎹綔涓烘湰妯″潡鎿嶄綔銆?
## 5 杈撳嚭濂戠害

### 5.1 娓呮礂鍚庢暟鎹泦

apply 妯″紡浜у嚭锛?
```text
clean_dataset_<job_id>.csv
clean_dataset_<job_id>.xlsx
```

鍒楋細

- 淇濈暀 搂3.1 鍘熷鍒楋紝鎸夋竻娲楃粨鏋滄洿鏂般€?- 鍙拷鍔?`derive_basic_fields` 鐢熸垚鐨勫熀纭€鍒椼€?- 涓嶇敓鎴?Kamei 14 缁淬€佽涔夊悜閲忋€佽瀺鍚堢壒寰佹垨妯″瀷杈撳叆鐗瑰緛銆?- 涓嶅啓 `is_test`銆?- 涓嶅啓浠讳綍璁粌/娴嬭瘯鏍囪銆?
### 5.2 姣忔缁熻

```text
clean_steps_stats_<job_id>.json
```

姣忔鍖呭惈锛?
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

### 5.3 鏁版嵁闆嗗彉鍖栧浘

```text
clean_dataset_change_<step>_<job_id>.png
```

灞曠ず琛屾暟銆佹爣绛惧垎甯冦€佺己澶?閲嶅鍙樺寲銆?
### 5.4 鎸囧畾鍒楀彉鍖?
```text
clean_column_stats_<job_id>.json
clean_column_distribution_<step>_<column>_<job_id>.png
```

`chart_columns[]` 涓虹┖鏃跺彧浜ф暟鎹泦绾у彉鍖栧拰 stats锛屼笉浼€犲垪绾у浘銆?
### 5.5 manifest

閬靛惊 搂3.9锛屽苟璁板綍锛?
```text
mode
chain_config
chart_columns
derived_columns
column_schema
input_checksum
output_checksum
warnings
```

涓嶈褰?`feature_schema`锛涙ā鍨嬬壒寰?schema 鐢辫缁冮樁娈靛啓鍏ユā鍨嬪寘銆?
## 6 鐘舵€佹寔涔呭寲

- `job.kind=clean`锛屼簲鎬併€?- 浠诲姟璁板綍妯″紡銆佸鐞嗛摼銆佸浘琛ㄥ垪銆佽緭鍏ヨ緭鍑哄紩鐢ㄣ€侀敊璇棩蹇椼€?- preview 涓嶄骇涓昏〃锛沘pply 鎵嶄骇娓呮礂鍚庢暟鎹泦銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`銆?- 鍚岃緭鍏ャ€佸悓閰嶇疆涓昏〃銆佺粺璁″拰鍥捐〃鏁板€间竴鑷淬€?- `elapsed_ms`銆佹墽琛屾椂闂村拰 job_id 涓嶄綔涓鸿法杩愯涓€鑷撮」銆?
## 7 楠屾敹

- 涓婁紶鏍囧噯 `collected_commits.csv`锛宲review 寰楀埌閫愭缁熻鍜屽浘琛紝鏃犳竻娲楀悗涓昏〃銆?- apply 寰楀埌 `clean_dataset.csv/xlsx`銆佺粺璁°€佸浘琛ㄣ€乵anifest銆?- CSV UTF-8 BOM銆乆LSX 鍗?sheet銆佷腑鏂囦笉涔辩爜銆?- 鎿嶄綔娉ㄥ唽琛ㄥ垎缁勬纭紝椤哄簭绾︽潫鍙牎楠屻€?- 鏃?`szz_label`銆乣d5_exclude`銆乣time_split`銆乣feature_build`銆佹ā鍨嬬壒寰侀€夋嫨銆?- 杈撳嚭涓嶅惈 `is_test` 鍜屾ā鍨嬬壒寰侀泦銆?- 鏈墦鏍囦繚鎸佺┖鍊笺€?- 鎸囧畾鍒楀悗鏈夊墠鍚庡垎甯冨浘锛涙棤鍒楁椂鏈夋暟鎹泦鍙樺寲鍥俱€?- 缂哄垪銆侀敊绫诲瀷銆佸叕寮忔敞鍏ャ€佹湭鐭ユ搷浣溿€侀『搴忓啿绐併€佺姝㈠瓧娈靛潎杩斿洖 40001銆?- CLI/API 鍚屽弬鏁扮瓑浠枫€?