# 棰勬祴鎬ц兘璇勪及锛堝姛鑳?6锛?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
## 涓€鍙ヨ瘽姒傝堪

鐙珛鐨勮瘎浼板伐鍏峰彴锛氫笂浼犵敱鏉垮潡 鈶?瀵规祴璇曢泦棰勬祴浜у嚭鐨?`predictions.csv`锛堝凡閫忎紶鐪熸爣绛撅紝搂3.4锛変笌鍙€?effort 鏉ユ簮锛埪?.3 `train_testset`锛屾寜 la/ld 杩樺師鐪熷疄 LOC锛夛紝鎸夐槇鍊煎拰鎸囨爣閰嶇疆璁＄畻鏁板€笺€佹贩娣嗙煩闃点€佸妯″瀷瀵规瘮銆佷袱绫?effort 鍥惧強鎶ュ憡锛屼笉璁粌妯″瀷銆佷笉鏀瑰彉棰勬祴姒傜巼銆佷笉鎺ュ彈鐙珛鏍囩琛ュ厖鏂囦欢锛屼篃涓嶈姹傚簱涓凡鏈夎褰曘€?
## 1 鑱岃矗涓庝笉璐熻矗鑼冨洿

**璐熻矗**锛?
- 瀵逛竴涓垨澶氫釜妯″瀷鐨?搂3.4 `predictions.csv`锛堥』鑷甫鏉垮潡 鈶?閫忎紶鐨勭湡鏍囩锛夋墽琛岀嫭绔嬭瘎浼帮紝鏀寔闃堝€笺€佹寚鏍囩粍鍚堛€佷富鎺掑簭鎸囨爣鍜屾姤鍛婃牸寮忛厤缃紱澶氭ā鍨嬫€ц兘瀵规瘮鍦ㄦ湰妯″潡瀹屾垚銆?- 浠?`data_model/evaluation/metrics.py` 涓烘墍鏈夊熀纭€涓?effort-aware 鎸囨爣鍏紡鍗曟簮锛學eb 涓?CLI 鍏辩敤銆?- 浜у嚭鎸囨爣闀胯〃銆佹贩娣嗙煩闃点€佸妯″瀷姣旇緝銆丷OC/PR/鏍″噯/effort 绛夊浘鍜屽甫涓嶅彲鐢ㄥ師鍥犵殑鎶ュ憡銆?- 淇濈暀榛樿 0.5 涓嬩笌鍘嗗彶 `model_metrics.csv` 鐨勯€愬€间竴鑷存€ч獙鏀剁嚎锛岃嚜瀹氫箟闃堝€煎彧褰卞搷渚濊禆闃堝€肩殑鎸囨爣銆?
**涓嶈礋璐?*锛?
- 璁粌銆侀娴嬨€佷慨鏀归闄╂鐜囥€佽В閲婅川閲忚瘎浠锋垨 CI 闂ㄧ銆?- 鎺ュ彈鐙珛鏍囩鏂囦欢锛涙棫 `labels.csv` 宸插簾姝紝涓婁紶鍗宠繑鍥?40001銆傜湡鏍囩 MUST 宸茬敱鏉垮潡 鈶?閫忎紶鍦?`predictions.csv` 鍐咃紝璇勪及鍦烘櫙缂烘爣绛剧殑杈撳叆鍓嶇疆鎷掔粷銆?- 鎶婂巻鍙查潤鎬?CSV 褰撲綔璁＄畻鏈嶅姟锛屾垨鍦ㄥ墠绔€佸悗绔€佸悇绾胯剼鏈腑鍚勫啓涓€濂楁寚鏍囧叕寮忋€?- 浠ユ爣绛剧己澶便€佹牱鏈笉瓒崇瓑鐞嗙敱浼€?0 鎴栫┖鐧芥暟鍊硷紱杩欎簺鎯呭喌蹇呴』鏄惧紡鎶ュ憡銆?
## 2 鐙珛杩愯鍏ュ彛

```bash
python -m evaluation.evaluate run \
  --predictions predictions.csv \
  --effort train_testset.csv \
  --threshold 0.5 --metrics auc,ap,f1,precision,recall,accuracy,popt \
  --primary-metric auc --format md --out ./out
python -m evaluation.evaluate metrics
```

| 鍏ュ彛 | 鍛戒护 / 绔偣 | 濂戠害 |
|---|---|---|
| CLI | `python -m evaluation.evaluate run/metrics` | 鏂囦欢鍜岃瘎浼伴厤缃嵆鍙繍琛岋紝涓?API 鍏辩敤鎸囨爣涓庣粯鍥惧唴鏍?|
| 鎸囨爣 API | `GET /api/evaluate/metrics` | 杩斿洖鎸囨爣閿€佽鏄庛€佸叕寮忔爣璇嗐€佹槸鍚︿緷璧栭槇鍊煎拰 effort 绫诲瀷 |
| 浠诲姟 API | `POST /api/evaluate/run` | multipart 涓婁紶甯︾湡鏍囩鐨?predictions + 鍙€?effort 鏉ユ簮涓庨厤缃紝杩斿洖 `kind=evaluate` 鐨?`job_id` |
| 浠诲姟绠＄悊 | `GET /api/jobs/{id}`銆乣POST /api/jobs/{id}/retry\|cancel` | 杩涘害銆佹棩蹇椼€侀噸璇曚笌鍙栨秷 |
| 涓嬭浇 | `GET /api/evaluate/outputs/{job_id}/{name}` | 涓嬭浇鎸囨爣銆佹贩娣嗐€佸浘銆佹姤鍛婂拰 manifest |

鎵€鏈?HTTP 绔偣锛堝惈鍥惧儚鍜屾姤鍛婁笅杞斤級蹇呴』浣跨敤 `X-API-Key`锛涘浘鐗囩敱閴存潈 fetch 杞?ObjectURL銆俽un 鐨勫彲閫?`dataset_id` 浠呯敤浜庨€夋嫨宸插鍏ョ殑绛変环鏂囦欢锛屼笉鏄绠楀墠鎻愩€?
## 3 杈撳叆濂戠害

- 蹇呴渶涓昏緭鍏ラ伒寰?[`../file-contracts.md`](../file-contracts.md) 搂3.4 `predictions.csv`锛岀敱鏉垮潡 鈶?瀵规祴璇曢泦棰勬祴浜у嚭锛?*姣忚 MUST 甯﹂潪绌?`is_bug_inducing` 鐪熸爣绛?*锛堟澘鍧?鈶?浠?搂3.3 `train_testset` 閫忎紶锛夈€傜己鐪熸爣绛剧殑杈撳叆鍓嶇疆鎷掔粷锛涗笉鍐嶆帴鍙椾换浣曠嫭绔嬫爣绛炬枃浠讹紙鏃?搂3.5 `labels.csv` 宸插簾姝級銆?- 鍙€?effort 鏉ユ簮涓?搂3.3 `train_testset`锛堟寜 la/ld 杩樺師鐪熷疄 LOC锛夛紝鎸夋彁浜ゅ搱甯?join锛涚己 effort 鏉ユ簮鏃?effort-aware 鎸囨爣鎶湶 `missing_effort`锛屼袱绫?effort 鍥句粛浜や粯銆?- 鍙€?`dataset_id` 鍙€夋嫨宸插鍏ョ殑 predictions 鏂囦欢锛涙棤搴撹褰曟椂涓婁紶鏂囦欢鍗冲彲瀹屾垚璇勪及銆傜瓫閫夋椂闂淬€佹ā鍨嬪垪琛ㄧ瓑鏉′欢鍙綔鐢ㄤ簬鏈杈撳叆蹇収銆?- 鏈閰嶇疆鍖呮嫭 `threshold`銆乣metrics[]`銆乣primary_metric`銆乣effort_enabled`銆乣report_format` 鍜屽浘閫夐」锛涢槇鍊煎湪寮€鍖洪棿 (0,1)锛屼富鎺掑簭鎸囨爣蹇呴』灞炰簬宸查€夋寚鏍囥€?- 鍙€?搂3.7 `explanations.csv` 鐢ㄤ簬姹囨€荤壒寰侀噸瑕佹€у浘锛涙湭鎻愪緵鏃舵姤鍛婅椤逛笉鍙敤鍘熷洜锛屼笉浠?predictions 鍙嶆帹鐗瑰緛璐＄尞銆?- 缂洪娴嬭涓嶅緱琛?0锛涚湡鏍囩鏉ヨ嚜娴嬭瘯闆嗐€佷笉鍐嶆湁鏈墦鏍囪褰曡繘鍏ヨ瘎浼般€傛祴璇曢泦鍙ｅ緞鐢辫緭鍏ユ枃浠讹紙搂3.3 `train_testset`锛夌‘瀹氾紝骞跺湪 manifest 鍥哄寲銆?
### 涓€鏈熸寚鏍囨竻鍗?
| 绫诲瀷 | 鎸囨爣 | 鏄惁渚濊禆鍒ゅ畾闃堝€?|
|---|---|---|
| 鎺掑簭/姒傜巼 | `auc / ap` | 鍚?|
| 鍩虹鍒嗙被 | `f1 / precision / recall / accuracy` | 鏄?|
| effort-aware | `recall_at_20 / recall_at_50 / p_norm / popt` | 鍚?|

## 4 杈撳嚭濂戠害

| 杈撳嚭 | 鏂囦欢涓庡唴瀹?|
|---|---|
| 鎸囨爣 | `evaluate_metrics_<job_id>.csv`锛氫弗鏍奸噰鐢?搂3.6 metrics 闀胯〃 schema锛岄€愭ā鍨嬮€愭寚鏍囦竴琛?|
| 娣锋穯鐭╅樀 | `evaluate_confusion_<job_id>.csv`锛氫弗鏍奸噰鐢?搂3.6 confusion schema锛岄殢鏈闃堝€艰绠?|
| 澶氭ā鍨嬫瘮杈?| `evaluate_comparison_<job_id>.json`锛氭寜涓绘寚鏍囨帓搴忥紝闄勬牱鏈暟銆佹鏍锋湰鐜囥€侀槇鍊笺€佹暟鎹笌妯″瀷鐗堟湰 |
| 鍩虹鍥?| `evaluate_roc_<job_id>.png`銆乣evaluate_pr_<job_id>.png`銆乣evaluate_confusion_<job_id>.png`銆乣evaluate_calibration_<job_id>.png` |
| effort 涓ょ被鍥?| `evaluate_effort_unaware_<job_id>.png` 涓?`evaluate_effort_aware_<job_id>.png` 鍧囦负纭€т骇鐗╋紝瑕嗙洊璇剧▼瑕佹眰鐨勪袱绫昏瘎浼拌鍥?|
| 鐗瑰緛閲嶈鎬?| 鎻愪緵 explanations 鏃朵骇 `evaluate_feat_importance_<job_id>.png`锛涘惁鍒欏湪鎶ュ憡璁板綍涓嶅彲鐢ㄥ師鍥?|
| 鎶ュ憡 | `evaluate_report_<job_id>.md`锛屽彲閫?`.html`锛涘惈鎸囨爣琛ㄣ€佹贩娣嗐€佸浘寮曠敤銆佺瓫閫夊彛寰勫拰涓嶅彲鐢ㄥ師鍥犳竻鍗?|
| manifest | 姣忎釜浜х墿浼村悓鍚?`evaluate_<artifact>_<job_id>.manifest.json`锛屾弧瓒?搂3.9锛岃褰曡緭鍏?checksum銆佺湡鏍囩鏉ユ簮锛坱rain_testset锛夊拰瀹屾暣閰嶇疆 |

鍛藉悕缁熶竴涓?`<module>_<artifact>_<job_id>.<ext>`銆傜己鐪熸爣绛剧殑杈撳叆鍦ㄥ叆鍙ｅ墠缃嫆缁濓紙涓嶄骇鍗婃垚鍝侊級锛涙棤棰勬祴銆佹牱鏈笉瓒虫垨妯″瀷杈撳叆涓嶅吋瀹规椂锛屽鐩稿簲鎸囨爣鍐欏叆鏄庣‘鐨勪笉鍙敤鍘熷洜锛屼笉浜т吉鏁板€笺€傚敮涓€鍏紡瀹炵幇鏄?`data_model/evaluation/metrics.py`锛涢粯璁ら槇鍊?0.5 涓嬩笌鍘嗗彶 `model_metrics.csv` 瀵瑰簲鍊奸€愰」涓€鑷达紝缁濆瀹瑰樊 1e-6銆?
## 5 鍙厤缃」

| 閰嶇疆 | 鏉ユ簮 | 榛樿 / 绾︽潫 |
|---|---|---|
| `decision_threshold` | `user_config` 鍏ㄥ眬閿垨 run 瑕嗙洊 | 榛樿 0.5锛涗笌椋庨櫓灞曠ず闃堝€煎垎閿?|
| `metrics_selected` | `user_config` 鍏ㄥ眬閿垨 run 瑕嗙洊 | 榛樿 AUC/AP/F1/Precision/Recall/Accuracy |
| `primary_metric` | `user_config` 鍏ㄥ眬閿垨 run 瑕嗙洊 | 榛樿 `auc`锛岄』灞炰簬鏈鎸囨爣闆?|
| `effort_enabled` | `user_config` 鍏ㄥ眬閿?| 榛樿 true锛涙帶鍒?effort 鎸囨爣閫夋嫨锛屼笉鍒犻櫎璇剧▼瑕佹眰鐨勪袱绫诲浘鐣欒瘉 |
| `risk_high_threshold` / `risk_mid_threshold` | `user_config` 鍏ㄥ眬閿?| 浠呬緵椋庨櫓灞曠ず椤碉紝涓嶅弬涓庢€ц兘鍏紡 |
| 鎶ュ憡鏍煎紡涓庡浘閫夐」 | run 閰嶇疆 | Markdown 榛樿锛屽彲閫?HTML锛涘浘閫夐」涓嶅緱缁曡繃涓ょ被 effort 纭姹?|
| `default_dataset` | `user_config` 鍏ㄥ眬閿?| 浠呬綔杈撳叆涓嬫媺榛樿閫夐」 |

閰嶇疆鍐欏叆 `user_config` 鍚庨噸鍚繚鎸侊紱姣忔 run 鐨勯厤缃揩鐓т笌鐗堟湰杩涘叆 job 鍜?manifest锛屽悗缁慨鏀瑰叏灞€閰嶇疆涓嶆敼鍐欏巻鍙叉姤鍛娿€?
## 6 鐘舵€佹寔涔呭寲

- 璇勪及鍒涘缓 `job.kind=evaluate`锛屼娇鐢ㄧ粺涓€浜旀€侊紝鎸佷箙鍖栬緭鍏ュ紩鐢ㄣ€侀厤缃€佽繘搴︺€侀敊璇棩蹇楀拰杈撳嚭寮曠敤锛涘悓 kind 浜掓枼锛岄噸鍚仐鐣?running 缃?failed銆?- 杈撳嚭钀界洏 `temp/outputs/<job_id>/`锛岀洰褰曟暣浣撳姞鍏?gitignore锛涙墍鏈夋姤鍛婁笌鍥惧潎鍙劚绂绘暟鎹簱閲嶆柊涓嬭浇鍜屽鏍搞€?- 鍏ㄥ眬闃堝€间笌鎸囨爣閰嶇疆鐢?`user_config` 鎸佷箙鍖栧苟閲嶅惎鎭㈠锛涘巻鍙茶瘎浼板浐鍖栭厤缃€佽緭鍏?checksum銆佹牱鏈寖鍥淬€佹ā鍨?鐗瑰緛鐗堟湰涓庡叕寮忎唬鐮佺増鏈€?- 缂撳瓨閿嚦灏戝寘鍚緭鍏?checksum銆佹ā鍨嬬増鏈€侀槇鍊煎拰鎸囨爣闆嗗悎锛涗换涓€鍙樺寲鍗抽噸鏂拌绠楃浉搴旂粨鏋滐紝缂撳瓨涓嶅緱瑕嗙洊鏂扮増鏈€?- 鍙€夊鍏?storage 鍙櫥璁板浘鍜屽睍绀虹储寮曪紱鎸囨爣鏂囦欢銆佹姤鍛婂拰 manifest 浠嶆槸鏉冨▉浜や粯鐗┿€?
## 7 涓庡叾浠栨ā鍧楄竟鐣?
- 涓?predict 鍙姹?搂3.4 鏂囦欢鍏煎锛堥』鍚€忎紶鐪熸爣绛撅級锛涚湡鏍囩鏈€缁堟潵鑷澘鍧?鈶?鐨?搂3.3 `train_testset`锛岀粡鏉垮潡 鈶?閫忎紶锛屼笉鍐嶆湁鐙珛鏍囩鏂囦欢锛沺redict 鏈嶅姟涓嶅湪鍦轰篃鑳借瘎浼般€?- 澶氭ā鍨嬫瘮杈冪敱杈撳叆鏂囦欢鍐呮ā鍨嬫爣璇嗗尯鍒嗭紱evaluate 涓嶄緷璧?train 浠诲姟璁板綍锛屼篃涓嶈鍙栬缁冩湡鎸囨爣銆?- 鍘熸ā鍨嬫€ц兘椤甸潰鎵挎媴鐨勬寚鏍囥€佹贩娣嗐€佸浘涓庢姤鍛婅绠楄亴璐ｅ叏閮ㄥ綊鏈ā鍧楋紱瓒嬪娍灞曠ず鍙 storage 涓凡瀵煎叆鐨勬彁浜や笌棰勬祴锛屼笉鍙︾畻鎬ц兘鎸囨爣銆?- storage 鎻愪緵鍙€夊睍绀哄鍏ュ拰閰嶇疆/浠诲姟鎸佷箙鍖栵紝涓嶄綔涓鸿瘎浼扮殑鏁版嵁鍓嶇疆锛汣I 闃堝€奸棬绂佸綊 extension銆?
## 8 楠屾敹鏍囧噯

fixtures 浣嶄簬 `tests/fixtures/files/evaluate/`锛屽惈姝ｅ父銆佽竟鐣屻€侀潪娉曚笁绫诲甫鐪熸爣绛剧殑 predictions锛涘湪鏃?predict 鏈嶅姟銆佺┖搴撶幆澧冧腑锛孋LI 涓?API 鍚勫畬鎴愪竴娆¤瘎浼板苟閫愬垪鏂█ 搂3.6 杈撳嚭銆?
- 淇敼闃堝€煎悗锛孎1/Precision/Recall/Accuracy 涓庢贩娣嗙煩闃垫寜鏂伴槇鍊艰绠楋紝AUC/AP 涓嶈绡℃敼锛涘鎸囨爣鍕鹃€変笌涓绘帓搴忕敓鏁堛€?- 涓や釜鍙婁互涓婃ā鍨嬪彲鍦ㄥ悓涓€姣旇緝缁撴灉涓帓搴忥紱鎶ュ憡鍖呭惈鏍锋湰鏁般€佹鏍锋湰鐜囥€侀槇鍊笺€佹暟鎹?妯″瀷鐗堟湰鍜岃绠楁椂闂淬€?- 榛樿 0.5 涓嬩笌鍘嗗彶 `model_metrics.csv` 閫愬€间竴鑷达紙1e-6锛夛紱鍏紡鍗曞厓娴嬭瘯璇佹槑 train/evaluate 鍏辩敤 `data_model/evaluation/metrics.py`銆?- effort-unaware 涓?effort-aware 涓ょ被鍥惧悇鑷冲皯涓€寮犱笖鏁版嵁鍙绠楋紱ROC/PR/娣锋穯/鏍″噯鍥句笌鎶ュ憡寮曠敤瀹屾暣銆?- 缂虹湡鏍囩鐨勮緭鍏ュ墠缃嫆缁濓紱鏃犻娴嬨€佹牱鏈笉瓒炽€佹湭鐭ユ寚鏍囥€侀槇鍊艰秺鐣屽潎鏈夋槑纭涔夛紱缂鸿涓嶈ˉ 0锛屽け璐ヤ笉鐣欏崐鎴愬搧銆?- 鎵挎帴 TODO/06锛氶槇鍊笺€佹寚鏍囥€佸妯″瀷姣旇緝銆侀厤缃噸鍚仮澶嶃€佹仮澶嶉粯璁ゅ€煎拰寮傚父鍦烘櫙鍧囨湁娴嬭瘯锛涢厤缃繚瀛樺悗閲嶆柊鍚姩浠嶄繚鎸併€?