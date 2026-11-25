# 缁熶竴浠诲姟 API锛坖obs锛?
涓€鍙ヨ瘽锛氱粺涓€鏌ヨ鍏被寮傛鎴栧悓姝ヨ惤搴撲换鍔＄殑鐘舵€併€佽繘搴︺€佹棩蹇椾笌杈撳嚭寮曠敤锛屽苟鎻愪緵鍙楅檺閲嶈瘯鍜屽彇娑堬紝鎵€鏈夌敓鍛藉懆鏈熶互 job 琛ㄤ负鍑嗐€?
瀹炵幇鐘舵€侊細閮ㄥ垎銆€鏈熸锛氫竴鏈?
W2 宸插疄鐜板叚绫讳簲鎬佺鐞嗐€佸悓 kind 鏁版嵁搴撲簰鏂ャ€侀噸鍚腑鏂仮澶嶅拰鎸佷箙杩涘害銆俉3 collect/run銆乄4 clean/run銆乄5 train/run銆乄6 predict/run銆乄7 evaluate/run銆乄8 explain/run 浠诲姟閲嶈瘯鍚庣敱鍚勮嚜鎵ц鍣ㄦ秷璐归槦鍒楋紱鍏朵綑灏氭湭鎺ュ叆鎵ц鍣ㄧ殑 kind 浠嶅彧鎺掗槦锛屼笉瀹ｇО鑷姩鎵ц銆傛墽琛屽櫒鎼哄甫 retry_count 浠ょ墝骞跺崗浣滄鏌ュ彇娑堢姸鎬侊紱clean/train 鍦ㄥ彂甯冩枃浠朵笌鍐?success 鏈熼棿鎸佹湁鍚?kind 閿侊紝闃绘鏃?attempt 鍙戝竷銆?
浠诲姟涓庤緭鍑哄叕鍏卞彛寰勮 [README.md](README.md)锛涘瓨鍌ㄨ亴璐ｈ [storage.md](storage.md)銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗 `collect / clean / train / predict_batch / evaluate / explain` 鍏被 kind 鐨勫垪琛ㄣ€佽鎯呫€乺etry銆乧ancel銆?- 浜旀€佸浐瀹氫负 `queued / running / success / failed / cancelled`锛涘悓姝?run 涔熷啓 success/failed 缁堟€佷緵瀹¤銆?- 涓嶈礋璐ｆ墽琛屾ā鍧椾笟鍔＄畻娉曘€佷慨鏀硅緭鍑烘枃浠跺唴瀹规垨绠＄悊 localize/storage 鎵规锛涘悗涓よ€呬笉鏂板 kind銆?- 涓嶄緷璧栬繘绋嬪唴瀛楀吀鎺ㄦ柇鐘舵€侊紝涓嶅湪鍝嶅簲涓硠婕忓嚟璇併€佸爢鏍堛€丼QL 鎴栨湰鏈烘晱鎰熻矾寰勩€?
## 2. 绔偣濂戠害

### GET /api/jobs

鏌ヨ鍙傛暟锛歚kind`銆乣status` 鍙€夛紝`page=1`銆乣size=20` 鍙€夛紝1鈮ize鈮?00銆傚搷搴?`{total,page,size,items[]}`锛宨tems 涓鸿鎯呮憳瑕侊紝鎸?created_at DESC銆乯ob_id ASC 鎺掑簭銆?
### GET /api/jobs/{job_id}

鍝嶅簲 `data`锛?
| 瀛楁 | 鍚箟 |
|---|---|
| `job_id` / `kind` / `status` | 鏍囪瘑銆佸叚绫讳箣涓€銆佷簲鎬佷箣涓€ |
| `params_json` | 鑴辨晱鍏ュ弬涓庨厤缃揩鐓?|
| `total` / `done` / `current_item` | 杩涘害涓庡綋鍓嶅璞?|
| `created_at` / `started_at` / `finished_at` | UTC ISO 8601 `Z` 鏃堕棿 |
| `error_log` | 鑴辨晱鍙閿欒锛屾垚鍔熷彲涓?null |
| `retry_count` | 宸查噸璇曟鏁?|
| `output_ref_json` | 杈撳嚭鐩綍鐩稿鏂囦欢鍚嶃€乧hecksum銆佸瓙椤圭姸鎬佸拰缁熻锛屼笉鍚粷瀵硅矾寰?|

### POST /api/jobs/{job_id}/retry

鏃犺姹備綋锛屼粎 failed 鍙噸璇曪紱澶嶇敤 params_json 鏂板缓鎺掗槦涓婁笅鏂囷紝鐘舵€佽浆 queued銆乺etry_count+1銆傚搷搴?`{job_id,status:"queued",retry_count}`銆傚凡瀹屾垚杈撳嚭涓嶅垹闄わ紝閲嶈瘯浜х敓鐨勬柊鏂囦欢蹇呴』閬垮厤琚璁や负鏃ф垚鍔熸壒娆°€?
### POST /api/jobs/{job_id}/cancel

鏃犺姹備綋锛屼粎 queued/running 鍙彇娑堬紱鍝嶅簲 `{job_id,status:"cancelled",retry_count}`銆傛墽琛屽櫒椤诲崗浣滃仠姝紝涓嶈兘鍙栨秷鍚庣户缁啓 success銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | kind/status/鍒嗛〉闈炴硶銆侀潪娉曠姸鎬佹祦杞€乺etry 鍚?kind 浜掓枼鍐茬獊 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key` |
| 40400 | 404 | job_id 涓嶅瓨鍦紱localize/storage 杈撳嚭鎵规 id 涓嶅睘浜庢湰鎺ュ彛 |
| 50000 | 500 | 鏈鏈熷瓨鍌ㄩ敊璇紝涓嶅洖鏄惧唴閮ㄧ粏鑺?|

## 3. 杈撳叆濂戠害

杈撳叆浠呬负 kind/status銆佸垎椤靛拰 job_id锛屾棤鏂囦欢杈撳叆銆俴ind 涓?status 蹇呴』閫愬瓧鍖归厤鍏被浜旀€侊紝id 蹇呴』涓哄凡鐧昏鏍囪瘑锛況etry/cancel 涓嶆帴鏀惰鐩栧弬鏁帮紝闃叉閲嶈瘯鏃堕厤缃鎮勬倓鏀瑰彉銆?
杈撳嚭鐩綍涓殑鏂囦欢涓嬭浇浠嶈蛋鍚勬ā鍧?`/api/{module}/outputs/{job_id}/{name}`锛宩obs 涓嶆彁渚涗换鎰忚矾寰勮鍙栥€俻arams_json 涓殑 repo URL銆佹ā鏉垮拰瓒呭弬鍙繚鐣欙紝API Key銆佸彛浠ゃ€丩LM Key 蹇呴』鍦ㄥ啓鍏ュ墠鍓旈櫎銆?
## 4. 杈撳嚭濂戠害

浠呰緭鍑?JSON 浠诲姟璁板綍锛屼笉鐢熸垚 CSV/XLSX銆佹姤鍛婃垨 manifest銆傚疄闄呬笟鍔¤緭鍑哄強 搂3.9 manifest 鐢卞悇 run 妯″潡璐熻矗锛宩obs 鍙繚瀛樺紩鐢ㄣ€乧hecksum 鍜岀姸鎬併€?
- 鏂囦欢鍨?run 鐨?`output_ref_json` 鍖呭惈 `{module,job_id,outputs[],manifest_name}`锛沷utputs 椤瑰惈 `{name,sha256,size_bytes}`锛屽彲鍙﹀甫缁熻鍜屽瓙椤圭姸鎬併€俶odule 鏄笅杞界鐐规爣璇嗭紝棰勬祴浣跨敤 `predict` 鑰岄潪 job kind `predict_batch`锛沯ob_id 鏄骇鐗╂壒娆℃爣璇嗐€備骇鐗╅€夋嫨涓庡啀鎻愪氦閬靛惊 [API 鍏叡濂戠害](README.md#浜х墿搴撻€夋嫨涓庝笂浼犵瓑浠?锛屼笉寰楁毚闇蹭换鎰忔枃浠剁郴缁熻矾寰勩€?- 璁粌绛夊瀛愰」浠诲姟鍦?output_ref_json 涓繚瀛橀€愮畻娉曟垚鍔?澶辫触涓庝骇鐗╋紱鎬讳綋鐘舵€佹眹鎬昏鍒欏繀椤绘槑纭紝閮ㄥ垎鎴愬姛涓嶅緱鎺╃洊澶辫触瀛愰」銆?- 鏃堕棿瀛楁缁熶竴 UTC `Z`锛宔rror_log 鏈夐暱搴︿笂闄愬苟鑴辨晱銆?
## 5. 鍙厤缃」

- jobs API 鏃犵嫭绔嬩笟鍔￠厤缃紱鍒楄〃鍒嗛〉銆侀噸璇曟鏁扮瓑鏉ヨ嚜璇锋眰鍜屽師浠诲姟蹇収銆?- 鍚勬ā鍧楃殑 predict.retry_max銆佹ā鏉垮拰璧勬簮鍙傛暟鐢?[config.md](config.md) 绠＄悊锛宩obs 涓嶆彁渚涢澶栭厤缃壇鏈€?- 鍚?kind 浜掓枼銆侀噸鍚腑鏂疆 failed銆佹棩蹇楄劚鏁忔槸鍥哄畾绯荤粺涓嶅彉閲忥紝涓嶈兘鐢卞崟娆¤姹傚叧闂€?
## 6. 鐘舵€佹寔涔呭寲

- 鍚堟硶娴佽浆锛歚queued鈫抮unning鈫抯uccess/failed`锛宍queued/running鈫抍ancelled`锛宍failed鈫抭ueued`锛涙潯浠舵洿鏂板繀椤绘鏌ュ綋鍓嶇姸鎬併€?- 鍚?kind 鍚屾椂鏈€澶氫竴涓?running锛屼互 job 琛ㄦ潯浠舵洿鏂板疄鐜帮紝鍐茬獊杩斿洖 40001锛涜繘绋嬪唴閿佸彧鍙綔浼樺寲锛屼笉鑳芥浛浠ｈ〃绾︽潫銆?- 鏈嶅姟鍚姩鎶婇仐鐣?running 缃?failed锛宔rror_log 鏍囪杩涚▼閲嶅惎涓柇锛屼繚鐣?done 渚涙敮鎸佺画璺戠殑妯″潡閲嶈瘯銆?- 涓氬姟鏂囦欢钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紱jobs 鑷韩涓嶆柊澧炶緭鍑虹洰褰曪紝閲嶅惎鍚庡垪琛ㄤ笌璇︽儏瀹屾暣鍙銆?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/jobs/`锛屼互鍏被浠诲姟鐨勫弬鏁般€佺姸鎬佷笌杈撳嚭寮曠敤 JSON 鏍蜂緥椹卞姩娴嬭瘯銆?
- **姝ｅ父**锛氬叚绫讳簲鎬佸垪琛?璇︽儏銆佽繘搴︺€佹棩蹇椼€佽緭鍑哄紩鐢ㄥ彲瑙侊紱failed retry 涓?queued/running cancel 鐘舵€佹纭紝鍓嶇鍜?CLI 璇诲彇涓€鑷淬€?- **杈圭晫**锛氬悓姝ョ粓鎬併€佽缁冮儴鍒嗗瓙椤瑰け璐ャ€侀噸澶?cancel銆侀噸鍚仐鐣?running銆佺画璺戝箓绛夈€佺┖杈撳嚭鎴愬姛鍧囨湁鏄庣‘缁撴灉銆?- **闈炴硶**锛氭湭鐭?kind/status銆佸垎椤佃秺鐣屻€乺etry 闈?failed銆乧ancel 缁堟€併€佸悓 kind 鍐茬獊銆佷笉瀛樺湪鐨?id 杩斿洖 40001/40400锛屼笉鍙戠敓闈炴硶娴佽浆銆?- 鍏被涔嬪涓嶅嚭鐜扮涓冪 kind锛涙棩蹇楀拰 params_json 鏃犲嚟璇侊紱杈撳嚭鏂囦欢浠嶅彧鑳介€氳繃鎵€灞炴ā鍧楅壌鏉冧笅杞姐€?
## 8. 杈圭晫

jobs 鏄姸鎬佺鐞嗛潰锛屼笉鏄ā鍧楅棿鏁版嵁閫氶亾銆傛瘡涓笟鍔℃ā鍧椾粎渚濊嚜宸辩殑鏂囦欢 schema 鐙珛杩愯锛沯ob 琛ㄧ敤浜庣姸鎬佸拰瀹¤锛屾暟鎹簱浠诲姟璁板綍涓嶆槸涓婃父鏈嶅姟鏁版嵁鍓嶇疆锛宭ocalize/storage 鐨勫悓姝ユ壒娆′篃涓嶈寮鸿绾冲叆浠诲姟浣撶郴銆?