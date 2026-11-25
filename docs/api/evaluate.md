# 棰勬祴鎬ц兘璇勪及 API锛坋valuate锛?
涓€鍙ヨ瘽锛氱嫭绔嬫帴鏀舵澘鍧?鈶?瀵规祴璇曢泦棰勬祴浜у嚭銆佸凡閫忎紶鐪熸爣绛剧殑 predictions锛埪?.4锛夛紝鎸夋寚瀹氶槇鍊煎拰鎸囨爣璁＄畻 metrics銆佹贩娣嗙煩闃点€佸妯″瀷瀵规瘮銆佸浘褰笌鎶ュ憡锛屼笉璁粌妯″瀷銆佷笉鏀瑰彉棰勬祴姒傜巼銆佷笉鎺ュ彈鐙珛鏍囩鏂囦欢銆?
瀹炵幇鐘舵€侊細宸插疄鐜般€€鏈熸锛氫竴鏈?
鏂囦欢濂戠害鍞竴鏉冨▉锛歔../file-contracts.md](../file-contracts.md) 搂3.4锛坧redictions 杈撳叆锛夈€伮?.3锛坱rain_testset 浣?effort 鏉ユ簮锛夈€伮?.6銆伮?.9锛涙棫 搂3.5 `labels.csv` 宸插簾姝€傛寚鏍囧叕寮忓崟婧愪负 `data_model/evaluation/metrics.py`銆?
## 1. 鑱岃矗涓庝笉璐熻矗鑼冨洿

- 璐熻矗闃堝€间笌鎸囨爣閰嶇疆銆侀€愭ā鍨嬫寚鏍囥€佹贩娣嗙煩闃点€佸妯″瀷鎺掑簭瀵规瘮銆丷OC/PR/鏍″噯/effort 绛夊浘褰㈠強鎶ュ憡浜や粯銆?- 璐熻矗涓嶅彲鐢ㄥ師鍥犳姭闇诧細鏃犳湁鏁堥娴嬨€佹牱鏈笉瓒炽€佹ā鍨嬪厓淇℃伅涓嶅吋瀹逛笉寰椾吉閫犳暟鍊硷紱缂虹湡鏍囩鐨勮緭鍏ュ湪鍏ュ彛鍓嶇疆鎷掔粷銆?- 涓嶈礋璐ｉ噰闆嗐€佹竻娲椼€佽缁冦€侀娴嬫垨 XAI锛涗笉璇诲彇灞曠ず椤电姸鎬佷綔涓鸿绠椾緷鎹€?- 涓嶆帴鍙楃嫭绔嬫爣绛炬枃浠讹紙鏃?`labels.csv` 宸插簾姝級锛氱湡鏍囩 MUST 宸茬敱鏉垮潡 鈶?浠?搂3.3 `train_testset` 閫忎紶鍦?predictions 鍐呫€?- 鍘嗗彶 `model_metrics.csv` 浠呬綔榛樿 0.5 鐨勬暟鍊煎彛寰勫鐓у熀绾匡紝涓嶆槸杩愯杈撳叆鎴栧敮涓€鏁版嵁鏉ユ簮銆?
## 2. 绔偣濂戠害

### GET /api/evaluate/metrics

鏃犺姹傚弬鏁般€傚搷搴?`data.metrics[]` 姣忛」 `{key,name,description,formula,threshold_dependent,effort_aware}`锛涘彟杩斿洖 `defaults:{metrics_selected,primary_metric,effort_enabled}`銆?
涓€鏈熻嚦灏戠櫥璁?`auc`銆乣ap`銆乣f1`銆乣precision`銆乣recall`銆乣accuracy`銆乣recall_at_20`銆乣recall_at_50`銆乣p_norm`銆乣popt`銆傚叕寮忚鏄庣敱缁熶竴鎸囨爣妯″潡瀵煎嚭锛屽墠绔笉鍙﹀啓鍏紡銆?
### POST /api/evaluate/run

`multipart/form-data`锛歚files[]` 蹇呴』鍚?predictions 琛ㄦ牸锛埪?.4锛岄』鑷甫鐪熸爣绛撅級锛屽彲鍐嶅惈涓€涓?effort 鏉ユ簮琛ㄦ牸锛埪?.3 `train_testset`锛夛紱`config` JSON part銆備笉鍐嶆帴鍙?labels 琛ㄦ牸銆傚皬鏂囦欢鍚屾锛屽ぇ鏂囦欢鍒涘缓 `kind=evaluate` job銆?
| config 瀛楁 | 蹇呭～ | 濂戠害 |
|---|---|---|
| `dataset_id` | 鍚?| 宸插鍏?predictions 鐨勪究鍒╅€夋嫨锛涙樉寮忎笂浼犱紭鍏?|
| `model_names[]` | 鍚?| 闄愬畾妯″瀷锛涚己鐪佽瘎浼?predictions 鍐呭叏閮ㄦā鍨?|
| `threshold` | 鍚?| 寮€鍖洪棿 (0,1)锛岀己鐪佽 `decision_threshold` |
| `metrics[]` | 鍚?| 缂虹渷璇?`metrics_selected`锛岄€愰」椤诲湪娉ㄥ唽琛?|
| `primary_metric` | 鍚?| 缂虹渷璇?`primary_metric`锛岄』灞炰簬鏈 metrics |
| `effort_enabled` | 鍚?| 缂虹渷璇诲悓鍚嶉厤缃紱鎺у埗 effort-aware 鎸囨爣涓庡浘 |
| `report_format` | 鍚?| `md` / `html`锛岄粯璁?`md` |
| `format` | 鍚?| 琛ㄦ牸杈撳嚭 `csv` / `xlsx`锛岄粯璁?`csv` |

鍚屾鍝嶅簲 `data`锛歚{job_id,status:"success",outputs[],summary}`锛涘紓姝ヤ负 `{job_id,status:"queued"}`銆俿ummary 鍚?`models`銆乣rows`銆乣unavailable[]`銆乣primary_metric`銆乣effort:{provided,matched}`锛泆navailable 椤逛负 `{model_name,reason_code,message}`锛屽師鍥犵爜鍖呮嫭 `missing_effort`銆乣no_predictions`銆乣insufficient_samples`銆乣incompatible_model`銆傜己鐪熸爣绛剧殑杈撳叆鍦ㄥ叆鍙ｇ洿鎺?40001 鎷掔粷锛屼笉鐢熸垚 job銆?
### GET /api/evaluate/outputs/{job_id}/{name}

涓嬭浇鎸囨爣銆佹贩娣嗐€佸浘銆佹姤鍛婃垨 manifest锛涙墍鏈夋枃浠堕兘瑕佹眰 `X-API-Key`銆?
### 閿欒鐮?
| 涓氬姟鐮?| HTTP | 鍦烘櫙 |
|---|---|---|
| 40001 | 400 | schema/闃堝€?鎸囨爣/鎺掑簭閰嶇疆闈炴硶銆佺己鐪熸爣绛俱€佸叕寮忔敞鍏ャ€佸悓 kind 鍐茬獊銆侀潪娉曚笅杞藉悕 |
| 40100 | 401 | 缂哄け鎴栭敊璇殑 `X-API-Key` |
| 40400 | 404 | 鍙€?dataset銆乯ob 鎴栬緭鍑轰笉瀛樺湪 |
| 50000 | 500 | 鏈鏈熸湇鍔￠敊璇紱杩愯鏈熷け璐ュ啓鑴辨晱 job 鏃ュ織 |

## 3. 杈撳叆濂戠害

predictions 閫愬瓧閲囩敤 [../file-contracts.md](../file-contracts.md) 搂3.4锛?
| 鍒?| 绫诲瀷 | 蹇呭～ | 鍚箟 |
|---|---|---|---|
| commit_hash | string(40) | 鏄?| 鎻愪氦 |
| model_name | string | 鏄?| 妯″瀷 |
| risk_score | float [0,1] | 鏄?| 姒傜巼锛? 浣嶅皬鏁帮級 |
| predicted_label | int 0/1 | 鏄?| 鎸?decision_threshold 鐨勪簩鍒嗙被鏍囩 |
| decision_threshold | float | 鏄?| 鏈鍒ゅ畾闃堝€?|
| model_version / feature_version | string | 鏄?| 鐗堟湰鍏冧俊鎭?|
| predicted_at | datetime | 鏄?| 棰勬祴鏃堕棿 |
| is_bug_inducing | int 0/1 | 鏄?| 閫忎紶鐪熸爣绛撅紙鏉ヨ嚜 搂3.3 `train_testset`锛岃瘎浼板繀濉級 |

鐪熸爣绛惧凡鐢辨澘鍧?鈶?閫忎紶鍦?搂3.4 `predictions.csv` 鐨?`is_bug_inducing` 鍒楋紝**姣忚 MUST 闈炵┖**锛涙湰绔偣涓嶅啀鎺ュ彈鐙珛鏍囩鏂囦欢锛堟棫 搂3.5 `labels.csv` 搴熸锛夈€傜己鐪熸爣绛惧湪鍏ュ彛鐩存帴 40001 鎷掔粷锛屼笉鐢熸垚 job銆佷笉浜у崐鎴愬搧銆?
- 璇勪及鎸夋湰娆?threshold 浠?risk_score 閲嶆柊鎺ㄥ璇勪及鐢ㄦ爣绛撅紝涓嶄緷璧栬緭鍏?predicted_label 鐨勬棫闃堝€硷紱杈撳叆 predicted_label 浠嶉』閫氳繃 schema 鏍￠獙銆?- 鐪熸爣绛炬潵鑷?搂3.3 `train_testset`锛屾棤鏈墦鏍囨牱鏈紱缂洪娴嬭涓嶈ˉ 0銆?- effort-aware 鎸囨爣闇€鐪熷疄 LOC 宸ヤ綔閲忥細鍙€変笂浼犱竴涓?搂3.3 `train_testset` 琛ㄦ牸浣滀负 effort 鏉ユ簮锛屾寜 `la/ld`锛坙og1p锛夊弽鍙樻崲杩樺師 `LOC = round(expm1(la)+expm1(ld))`锛屾寜 commit_hash join銆傜己 effort 鏉ユ簮鏃?effort-aware 鎸囨爣鎶湶 `missing_effort`锛屼袱绫?effort 鍥句粛浜や粯锛坅ware 鍥炬爣娉ㄦ棤宸ヤ綔閲忚緭鍏ワ級銆俿ummary 鍚?`effort:{provided,matched}` 鐧昏鏉ユ簮琛屾暟涓庡懡涓鏁帮紱CLI 浠?`--effort <train_testset>` 鎻愪緵鍚屾簮杈撳叆銆?- 涓婁紶鏍￠獙澶у皬銆佹墿灞曞悕榄旀暟銆佸垪 schema銆佹鐜囪寖鍥淬€佺湡鏍囩闈炵┖涓?CSV 鍏紡娉ㄥ叆锛涚己 predictions銆佷吉閫犳枃浠舵垨缂虹湡鏍囩杩斿洖 40001銆?
## 4. 杈撳嚭濂戠害

搂3.6 鐨勫垪瀹氫箟閫愬瓧濡備笅锛屼笉鍙﹂€犺瘎浼板垪锛?
- **metrics**锛歚model_name,line,metric,value,threshold,n,pos_rate,dataset_version,model_version,computed_at`锛堥暱琛紝閫愭ā鍨嬮€愭寚鏍囦竴琛岋級銆?- **confusion**锛歚model_name,threshold,tp,fp,fn,tn`銆?- **report**锛歮d/html 鍚寚鏍囪〃 + 娣锋穯 + 鍥惧紩鐢?+ 涓嶅彲鐢ㄥ師鍥犳竻鍗曘€?- **鍥?png**锛歳oc/pr/confusion/calibration/effort/feat_importance锛坋ffort 涓ょ被璇剧▼纭姹傦級銆?
| 鏂囦欢 | 鍛藉悕 |
|---|---|
| metrics | `evaluate_metrics_<job_id>.csv`锛屾垨 `.xlsx` |
| confusion | `evaluate_confusion_<job_id>.csv`锛屾垨 `.xlsx` |
| report | `evaluate_report_<job_id>.md`锛屾垨 `.html` |
| 鍚勫浘 | `evaluate_<figure_type>_<job_id>.png`锛沞ffort-aware 涓?effort-unaware 鍒嗗埆浠?artifact 鍚嶅尯鍒?|
| manifest | `evaluate_metrics_<job_id>.manifest.json` |

report 涓紩鐢ㄧ浉瀵瑰熀纭€鏂囦欢鍚嶏紝涓嶅紩鐢ㄦ湰鏈虹粷瀵硅矾寰勩€傛病鏈夋湁鏁堟暟鍊兼椂瀵瑰簲 metrics 琛屼笉鍐?0锛屽師鍥犺繘鍏?report锛涙牱鏈暟銆佹鏍锋湰鐜囥€侀槇鍊笺€佹暟鎹泦鐗堟湰鍜屾ā鍨嬬増鏈殢缁撴灉缁欏嚭銆?
manifest 涓ユ牸閲囩敤 搂3.9锛岃褰曡緭鍏?checksum銆佺湡鏍囩鏉ユ簮锛坱rain_testset锛夈€侀槇鍊笺€佹寚鏍囬泦鍚堛€乪ffort 寮€鍏炽€佽緭鍑?checksum 鍜屼唬鐮佺増鏈€侰SV UTF-8 BOM锛孹LSX 鍗?sheet銆傞粯璁?0.5 涓嬩笌鍘嗗彶 `model_metrics.csv` 瀵瑰簲鎸囨爣閫愬€间竴鑷达紝瀹瑰樊 1e-6锛屾槸鍙ｅ緞楠屾敹绾裤€?
## 5. 鍙厤缃」

- 鍏ㄥ眬锛歚decision_threshold`銆乣metrics_selected`銆乣primary_metric`銆乣effort_enabled`锛沗risk_high_threshold` / `risk_mid_threshold` 浠呯敤浜庨闄╁睍绀猴紝涓嶆贩鍏ユ寚鏍囧叕寮忋€?- 鍗曟杩愯锛氭ā鍨嬪瓙闆嗐€侀槇鍊笺€佹寚鏍囥€佷富鎺掑簭銆乪ffort 寮€鍏炽€佹姤鍛婁笌琛ㄦ牸鏍煎紡銆?- 鎸囨爣娉ㄥ唽鍜岃绠楀潎鏉ヨ嚜 `data_model/evaluation/metrics.py`锛涘悗绔拰鍓嶇涓嶅緱澶嶅埗鍏紡銆?- `.env` 浠呮彁渚涘嚭鍘傞粯璁わ紝鐢ㄦ埛閰嶇疆閲嶅惎鎭㈠銆?
## 6. 鐘舵€佹寔涔呭寲

- 鍚屾杩愯鍐欑粓鎬侊紝寮傛 kind=`evaluate` 鍐欎簲鎬侊紱鍚?kind 鏉′欢鏇存柊浜掓枼锛岄噸鍚仐鐣?running 缃?failed锛屽彲 retry/cancel銆?- 杈撳嚭钀?`temp/outputs/<job_id>/`锛坓itignore锛夛紝job 鐧昏鍏ㄩ儴浜х墿涓庝笉鍙敤椤广€?- 鐩稿悓 predictions銆侀槇鍊间笌鎸囨爣閰嶇疆閲嶈窇涓€鑷达紱`computed_at` 闄ゅ锛屾暟鍊间笌鍥惧舰鏁版嵁蹇呴』涓€鑷淬€?- 璇勪及鏂囦欢鏄惁鐧昏 model_figure 鐢?storage 鍐冲畾锛岃繍琛屾湰韬笉渚濊禆鏁版嵁搴撳凡鏈夋ā鍨嬫垨棰勬祴琛屻€?
## 7. 楠屾敹

fixtures锛歚tests/fixtures/files/evaluate/`锛屼笉涓婁紶妯″瀷銆佷笉璋冪敤 predict 涔熷彲杩愯銆?
- **姝ｅ父**锛氫笂浼犲甫閫忎紶鐪熸爣绛剧殑 predictions 浜у嚭 搂3.6 鍏ㄩ儴鎵€閫夌粨鏋溿€佹姤鍛娿€乵anifest锛涘妯″瀷鎸変富鎸囨爣鎺掑簭锛岄粯璁?0.5 瀵圭収瀹瑰樊涓嶈秴杩?1e-6銆?- **杈圭晫**锛氶槇鍊艰竟鐣屻€佸崟妯″瀷銆佸叏姝?鍏ㄨ礋銆佹牱鏈笉瓒冲拰鏃犳硶璁＄畻 AUC 鏃剁粰鍑哄師鍥狅紝涓嶄吉閫?0锛涚己鐪熸爣绛惧墠缃?40001锛沞ffort-aware 涓?effort-unaware 涓ょ被鍥惧潎瀛樺湪銆?- **闈炴硶**锛氱己 predictions銆佹鐜囪秺鐣屻€佹湭鐭ユ寚鏍囥€乸rimary_metric 鏈€夈€侀噸澶嶉敭鏃犳硶鍒ゅ畾銆佷吉閫?XLSX銆佸叕寮忔敞鍏ュ潎杩斿洖 40001锛屼笉浜у崐鎴愬搧銆?- 鏀归槇鍊煎彧褰卞搷闃堝€肩浉鍏崇粨鏋滐紝涓嶉噸璁篃涓嶆敼 risk_score锛汣LI/API 鏁板€间竴鑷达紝杈撳嚭涓嬭浇閴存潈锛岄噸鍚悗閰嶇疆涓?job 鍙仮澶嶃€?
## 8. 杈圭晫

evaluate 鍙姹?搂3.4 鏂囦欢鍏煎锛堥』鍚€忎紶鐪熸爣绛撅級锛屼笌 predict/train 鐨勬湇鍔℃槸鍚﹀湪绾挎棤鍏筹紱杈撳嚭鍙緵 figures 鐧昏灞曠ず锛屼絾灞曠ず瀵煎叆涓嶆槸璁＄畻鍓嶇疆銆傚叡浜寚鏍囧叕寮忔槸浠ｇ爜渚濊禆锛屼笉鏄暟鎹簱鎴栦笂娓告湇鍔′緷璧栥€?