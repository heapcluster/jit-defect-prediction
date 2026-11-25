# 缂洪櫡鏁版嵁鏀堕泦 API锛坈ollect锛?
瀹炵幇鐘舵€侊細鐩爣濂戠害銆€鏈熸锛氫竴鏈?
> 鏃ф帴鍙ｅ彛寰勫寘鍚?14 缁寸壒寰併€?0/30 鍒囧垎鍜屸€滃彲閫夊鍏ュ簱鈥濓紱鏈枃宸插簾姝€傛柊鎺ュ彛鍙礋璐ｆ敹闆?Git 浠撳簱鎴栧鍏ュ叕寮€鏍囨敞鏁版嵁闆嗭紝浜у嚭甯︽爣绛句簩缁磋〃锛岄粯璁や繚瀛樻暟鎹簱锛屽苟鎻愪緵棰勮鍜屼笅杞姐€傛湰杞彧淇敼璁捐鏂囨。銆?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.1銆伮?.9锛涘叕鍏遍壌鏉冦€佸寘缁滃拰浠诲姟鍙ｅ緞瑙?[README.md](README.md)銆?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗 Git 浠撳簱鎷夊彇/璇诲彇銆佹彁浜ら噰闆嗐€丼ZZ 鎵撴爣锛屾垨鍏紑鏍囨敞鏁版嵁闆嗗鍏ャ€佸瓧娈垫槧灏勩€佹爣绛惧綊涓€鍖栧拰璐ㄩ噺鏍￠獙銆?- 璐熻矗鐢熸垚 `collected_commits.csv/xlsx`銆乻ummary銆乵anifest 鍜屽叕寮€鏁版嵁闆嗚川閲忔姤鍛娿€?- 璐熻矗榛樿淇濆瓨鏁版嵁闆嗗埌 `dataset` / `dataset_commit`銆?- 涓嶈礋璐?14 缁寸壒寰併€佽缁?娴嬭瘯鍒囧垎銆佹竻娲椼€佽缁冦€侀娴嬨€佽瘎浼般€佽В閲娿€佸畾浣嶅拰淇銆?- 涓嶆妸鏁版嵁搴撴垨鐜鍙橀噺涓殑鍥哄畾浠撳簱褰撲綔杩愯鍓嶆彁銆?
## 2 绔偣濂戠害

### POST /api/collect/run

`multipart/form-data`銆傝姹傚寘鍚?`config` JSON part锛屽叕寮€鏁版嵁闆嗘垨鎻愪氦娓呭崟鍙斁 `files[]`銆?
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

鍒涘缓 `job.kind=collect`銆傚悓 kind 鍚屾椂鏈€澶氫竴涓?running锛屽啿绐佽繑鍥?40001銆?
#### 2.1 `config` 鍏叡瀛楁

| 瀛楁 | 蹇呭～ | 绫诲瀷 | 濂戠害 |
|---|---|---|---|
| `source_type` | 鏄?| string | `git_repo` / `public_dataset` |
| `dataset_name` | 鏄?| string | 鏁版嵁闆嗘樉绀哄悕 |
| `save_to_db` | 鍚?| bool | 榛樿 `true` |
| `format` | 鍚?| string | `csv` / `xlsx`锛岄粯璁?`csv`锛汚PI 鍙悓鎵逛氦浠樺弻鏍煎紡 |

#### 2.2 Git 浠撳簱妯″紡 `source_type=git_repo`

| 瀛楁 | 蹇呭～ | 绫诲瀷 | 濂戠害 |
|---|---|---|---|
| `repo_source` | 鏄?| string | 鏈湴璺緞椤诲湪鍏佽鏍圭洰褰曞唴锛沀RL 鍗忚椤诲湪鐧藉悕鍗曞唴 |
| `branch` | 鍚?| string | 鍒嗘敮/ref锛岄粯璁?HEAD |
| `start_time` / `end_time` | 鍚?| datetime | ISO 8601 UTC 闂尯闂?|
| `start_commit` / `end_commit` | 鍚?| string(40 hex) | 鍙鍑烘彁浜よ寖鍥?|
| `mode` | 鍚?| string | `full` / `incremental`锛岄粯璁?`incremental` |
| `fetch_remote` | 鍚?| bool | 榛樿 `true` |
| `head_expect` | 鍚?| string(40 hex) | HEAD 涓嶇鍒欐嫆缁?|
| `dedup` | 鍚?| string | 褰撳墠浠?`commit_hash` |
| `szz_method` | 鍚?| string | `szz_v1` / `szz_lite`锛岄粯璁?`szz_v1` |
| `commit_list` | 鍚?| file | 浠呭惈 `commit_hash` 鐨?CSV/XLSX锛岀敤浜庡湀瀹氳寖鍥?|

Git 妯″紡绂佹浼犲叆 `split_ratio`銆乣feature_version`銆乣is_test` 绛夊瓧娈碉紱鏀跺埌鍗宠繑鍥?40001銆?
#### 2.3 鍏紑鏁版嵁闆嗘ā寮?`source_type=public_dataset`

| 瀛楁 | 蹇呭～ | 绫诲瀷 | 濂戠害 |
|---|---|---|---|
| `source_url` | 鍚?| string | 涓庝笂浼犳枃浠朵簩閫変竴锛沀RL 鍗忚椤诲湪鐧藉悕鍗曞唴 |
| `license` | 鏄?| string | SPDX 鎴栧師濮嬭鍙瘉璇存槑 |
| `source_note` | 鏄?| string | 璁烘枃銆侀」鐩富椤点€佷笅杞藉湴鍧€绛夋潵婧愯鏄?|
| `field_mapping` | 鏄?| object | `commit_hash`銆乣committed_at`銆乣is_bug_inducing` 鐨勬簮瀛楁鏄犲皠 |
| `label_mapping` | 鏄?| object | 鍘熷鏍囩鍊煎埌 `1/0/null` 鐨勬槧灏?|
| `dataset_format` | 鍚?| string | `csv` / `json` / `zip`锛屾寜涓婁紶鏂囦欢鑷姩璇嗗埆鏃跺彲鐪佺暐 |
| `files[]` | 鍚?| file | CSV/JSON/ZIP 鏁版嵁闆嗘枃浠讹紱涓?`source_url` 浜岄€変竴 |

`field_mapping` 绀轰緥锛?
```json
{
  "commit_hash": "sha",
  "committed_at": "date",
  "is_bug_inducing": "bug"
}
```

`label_mapping` 绀轰緥锛?
```json
{
  "1": 1,
  "true": 1,
  "bug": 1,
  "0": 0,
  "false": 0,
  "clean": 0
}
```

鍏紑鏁版嵁闆嗘ā寮忎笉鎵ц SZZ锛涙爣绛炬潵婧愯涓?`public_dataset`銆?
### GET /api/collect/preview/{job_id}

杩斿洖 `{columns, preview}`銆?
- `columns` 蹇呴』涓?file-contracts 搂3.1 閫愬瓧涓€鑷淬€?- `preview` 鏈€澶氬墠 20 琛屻€?- 鏈墦鏍囧瓧娈佃繑鍥?`null`銆?- 鍙厑璁搁瑙堝凡鐧昏銆乧hecksum 鏍￠獙閫氳繃鐨?CSV銆?
### GET /api/collect/outputs/{job_id}/{name}

涓嬭浇鏈浠诲姟鐧昏鐨勪骇鐗╂枃浠躲€?
鍏佽鐨勫熀纭€鍚嶇О锛?
```text
collected_commits_<job_id>.csv
collected_commits_<job_id>.xlsx
collect_summary_<job_id>.json
collect_quality_<job_id>.json
collect_quality_<job_id>.md
collected_commits_<job_id>.manifest.json
```

`name` 蹇呴』鍑虹幇鍦?manifest `outputs[]`锛岀姝㈣矾寰勫垎闅旂鍜?`..`銆?
### POST /api/collect/resave/{job_id}

褰撴枃浠跺凡鐢熸垚浣嗘暟鎹簱淇濆瓨澶辫触鏃讹紝鐢ㄥ凡淇濈暀浜х墿閲嶆柊鍐欏叆 `dataset` 鍜?`dataset_commit`銆?
- 鎴愬姛杩斿洖 `{job_id, dataset_id, status:"success"}`銆?- 杈撳叆浜х墿 checksum 涓嶇杩斿洖 40001銆?- 涓嶉噸鏂版墽琛屼粨搴撴媺鍙栨垨 SZZ銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | 鍙傛暟銆佽矾寰勩€佸崗璁€丠EAD銆佸瓧娈垫槧灏勩€佹爣绛炬槧灏勩€佹枃浠舵牸寮忋€佸悓 kind 鍐茬獊 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key`锛屽寘鎷笅杞?|
| 40400 | 404 | job 鎴栫櫥璁拌緭鍑轰笉瀛樺湪 |
| 50000 | 500 | 鏈鏈熸湇鍔￠敊璇紱杩愯鏈熷け璐ュ啓鑴辨晱 error_log |

## 3 杈撳嚭濂戠害

### 3.1 浜岀淮琛?
`collected_commits_<job_id>.csv/xlsx`锛屽瓧娈典弗鏍奸伒寰?file-contracts 搂3.1銆?
鍏抽敭绾︽潫锛?
- 涓嶅惈 Kamei 14 缁淬€?- 涓嶅惈 `is_test`銆?- `is_bug_inducing` 鏈墦鏍囦繚鎸佺┖銆?- `label_source` 蹇呭～锛歚git_szz` / `public_dataset`銆?- `source_type` 蹇呭～锛歚git_repo` / `public_dataset`銆?
### 3.2 缁熻淇℃伅

`collect_summary_<job_id>.json` 鑷冲皯鍖呭惈锛?
```text
source_type, source_url, dataset_name, label_source,
total_rows, positive_rows, negative_rows, unlabeled_rows,
duplicate_rows, skipped_rows, save_db_status, dataset_id
```

Git 妯″紡棰濆鍚?`repo`銆乣branch`銆乣head_hash`銆乣time_start`銆乣time_end`銆乣szz_method`銆?
鍏紑鏁版嵁闆嗘ā寮忛澶栧惈 `license`銆乣source_note`銆乣field_mapping`銆乣label_mapping`銆?
### 3.3 璐ㄩ噺鎶ュ憡

鍏紑鏁版嵁闆嗘ā寮忓繀浜э細

```text
collect_quality_<job_id>.json
collect_quality_<job_id>.md
```

鍐呭瑙?function_point/collect.md 搂4.3銆?
### 3.4 manifest

涓讳骇鐗╁悓鍚?manifest锛岄伒寰?file-contracts 搂3.9锛屽苟璁板綍锛?
```text
source_type, label_source, license, source_url,
save_db_status, dataset_id
```

## 4 鏁版嵁搴撲繚瀛樿涔?
- `save_to_db=true` 鏃讹紝鏂囦欢鐢熸垚鍚庡啓鍏?`dataset` 鍜?`dataset_commit`銆?- 鎴愬姛鍚庡搷搴旀垨 job 鐨?`output_ref_json` 蹇呴』鍚?`dataset_id`銆?- 鏂囦欢鐢熸垚鎴愬姛浣嗕繚瀛樺け璐ワ細
  - job 鐘舵€佷负 `failed`锛?  - `error_log` 鍐欐槑淇濆瓨澶辫触鍘熷洜锛?  - 鏂囦欢浜х墿浠嶅彲涓嬭浇锛?  - 鍙皟鐢?`POST /api/collect/resave/{job_id}`銆?- `save_to_db=false` 鏃讹紝job 鎴愬姛浠呰〃绀烘枃浠朵氦浠樻垚鍔燂紝鏁版嵁闆嗗垪琛ㄤ笉鏂板璁板綍銆?
## 5 鍙厤缃」

- `collect.allow_roots`锛氭湰鍦颁粨搴撳拰鍏紑鏁版嵁鏂囦欢鍏佽鏍圭洰褰曘€?- `collect.protocol_whitelist`锛氬厑璁哥殑 URL 鍗忚銆?- `default_dataset`锛氫粎浣滃睍绀哄拰渚垮埄閫夋嫨锛屼笉鏄繍琛屽墠鎻愩€?- 鍗曟杩愯閰嶇疆锛氭潵婧愮被鍨嬨€佷粨搴?鏁版嵁闆嗘潵婧愩€佽寖鍥淬€丼ZZ 鏂规硶銆佸瓧娈垫槧灏勩€佹爣绛炬槧灏勩€佷繚瀛樺紑鍏炽€佽緭鍑烘牸寮忋€?- 鎵€鏈夊崟娆￠厤缃畬鏁村啓鍏?`job.params_json` 涓?manifest锛涘嚟璇佷笉寰楀啓鍏ャ€?
## 6 鐘舵€佹寔涔呭寲

- `job.kind=collect`锛屼簲鎬?`queued / running / success / failed / cancelled`銆?- 闃舵锛氭媺鍙?瀵煎叆銆侀噰闆?鏄犲皠銆丼ZZ 鎴栨爣绛惧綊涓€鍖栥€佺敓鎴愪簩缁磋〃銆佷繚瀛樻暟鎹簱銆佺敓鎴愬鍑烘枃浠躲€?- 鍚?kind 浜掓枼锛涢噸鍚仐鐣?running 缃?failed锛涘け璐ュ彲閲嶈瘯锛岃繍琛屼腑鍙彇娑堛€?- 杈撳嚭钀?`temp/outputs/<job_id>/`銆?- 淇濆瓨鏁版嵁搴撳け璐ヤ笉鍒犻櫎鏂囦欢浜х墿銆?
## 7 楠屾敹

- Git 浠撳簱妯″紡锛氭湰鍦颁粨搴撴垨鍚堟硶 URL 鍙骇鍑?搂3.1 浜岀淮琛ㄣ€乻ummary銆乵anifest锛涙湭鎵撴爣涓虹┖锛涙棤 14 缁村拰 `is_test`銆?- 鍏紑鏁版嵁闆嗘ā寮忥細閫氳繃瀛楁/鏍囩鏄犲皠浜у嚭鍚?schema 浜岀淮琛紱涓嶆墽琛?SZZ锛涜川閲忔姤鍛婁笌 manifest 瀹屾暣銆?- 榛樿淇濆瓨鏁版嵁搴撴垚鍔熸椂锛宍GET /api/datasets` 鍙煡璇㈠埌鏂版暟鎹泦銆?- 淇濆瓨澶辫触鏃舵枃浠朵粛鍙笅杞斤紝`resave` 鍙仮澶嶅叆搴撱€?- CSV/XLSX 涓枃涓嶄贡鐮侊紝checksum 涓?manifest 涓€鑷淬€?- 闈炴硶璺緞銆佸崗璁€佸瓧娈垫槧灏勩€佹爣绛炬槧灏勩€丠EAD銆佹枃浠舵牸寮忓潎杩斿洖 40001 涓斾笉浜у崐鎴愬搧銆?