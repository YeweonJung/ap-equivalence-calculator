# Candidate Retrieval 전체 오류 목록

고정 정책의 저장된 평가 결과에서 추출. 평가 입력을 수정하거나 삭제하지 않았다.

## fixed — A 기존 retrieval + 거리순위 (4건)

| ID | 입력 | 원형 | 정답 target | 오류 | 1위 target |
| --- | --- | --- | --- | --- | --- |
| synthetic-00981 | 로핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| synthetic-00984 | 로나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | ranking | blonanserin\|non_product_specific |
| synthetic-01482 | 조핀 1mg QD | 조테핀 | zotepine\|non_product_specific | retrieval | 없음 |
| synthetic-01492 | 지돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |

## fixed — B 개선 retrieval + 거리순위 (1건)

| ID | 입력 | 원형 | 정답 target | 오류 | 1위 target |
| --- | --- | --- | --- | --- | --- |
| synthetic-00984 | 로나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | ranking | blonanserin\|non_product_specific |

## fixed — C 개선 retrieval + LR (1건)

| ID | 입력 | 원형 | 정답 target | 오류 | 1위 target |
| --- | --- | --- | --- | --- | --- |
| synthetic-00984 | 로나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | ranking | blonanserin\|non_product_specific |

## stress — A 기존 retrieval + 거리순위 (180건)

| ID | 입력 | 원형 | 정답 target | 오류 | 1위 target |
| --- | --- | --- | --- | --- | --- |
| stress-00000 | 나틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00001 | 라나틸가 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00003 | 라틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00006 | 라가 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00011 | 래개틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00012 | ᄅ가틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00019 | 나다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00020 | 라나다투 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00022 | 라다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00025 | 라투 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00030 | 래태다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00031 | ᄅ투다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00038 | 나디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00039 | 렉나디설 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00041 | 렉디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00044 | 렉설 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00049 | 랙샐디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00050 | ᄅᆨ설디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00057 | 나센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00060 | 로센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00063 | 로나 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00068 | 래내센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00069 | ᄅ나센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00076 | 나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00077 | 로나핀도 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00078 | 로 나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | ranking | blonanserin\|non_product_specific |
| stress-00079 | 로핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00082 | 로도 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00087 | 래대핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00088 | ᄅ도핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00095 | 나릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00096 | 멜나릴라 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00098 | 멜릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00101 | 멜라 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00106 | 맬래릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00107 | ᄆᆯ라릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00114 | 나캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00115 | 세나캘로 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00117 | 세캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00120 | 세로 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00125 | 새래캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00126 | ᄉ로캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00133 | 나안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00134 | 솔나안리 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00136 | 솔안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00139 | 솔리 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00144 | 샐래안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00145 | ᄉᆯ리안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00152 | 나가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00153 | 인나가베 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00155 | 인가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00158 | 인베 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00163 | 앤배가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00164 | ᄋᆫ베가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00171 | 나돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00172 | 지나돈오 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00174 | 지돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00177 | 지오 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00182 | 재애돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00183 | ᄌ오돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00190 | 나자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00191 | 트나자린 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00193 | 트자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00196 | 트린 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00201 | 태랜자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00202 | ᄐ린자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00209 | 트자 injeciton 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00210 | 나스달 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00211 | 리나스달패 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00216 | 리스 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00222 | 래새패달 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00230 | 나프스 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00231 | 사나프스리 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00236 | 사프 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00242 | 새패리스 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00250 | 나스나 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00251 | 서나스나티 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00256 | 서스 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00262 | 새새티나 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00270 | 서스나 injeciton 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00271 | 나르돌 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00272 | 세나르돌틴 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00277 | 세르 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00283 | 새래틴돌 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00291 | 나텔진 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00292 | 스나텔진라 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00297 | 스텔 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00303 | 새탤라진 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00311 | 나리졸 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00312 | 아나리졸피 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00317 | 아리 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00323 | 애래피졸 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00331 | 나란핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00332 | 올나란핀자 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00337 | 올란 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00343 | 앨랜자핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00351 | 나로린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00352 | 클나로린자 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00357 | 클로 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00363 | 캘래자린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00371 | 나릴폰 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00372 | 트나릴폰라 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00377 | 트릴 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00383 | 태랠라폰 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00391 | 나오센 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00392 | 티나오센틱 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00397 | 티오 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00403 | 태애틱센 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00411 | 나피라 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00412 | 하나피라에 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00417 | 하피 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00423 | 해패에라 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00431 | 하피라 injeciton 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00432 | xkdi 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00433 | oxkdei 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00440 | xkzdi 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00447 | okdi injeciton 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00448 | 나즈로핀 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00454 | 벤즈 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00455 | 벤즈트 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00460 | 밴재트로핀 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00468 | 나로리돈 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00474 | 일로 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00475 | 일로페 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00480 | 앨래페리돈 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00488 | 나루나진 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00494 | 플루 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00495 | 플루페 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00500 | 팰래페나진 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00508 | 나로리도 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00514 | 할로 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00515 | 할로페 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00520 | 핼래페리도 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00528 | xanpt 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00536 | xanzpt 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00543 | fanpt injeciton 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00544 | xeoon 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00552 | xeozon 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00559 | geoon injeciton 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00560 | xalol 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00568 | xalzol 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00575 | halol injeciton 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00576 | xnvga 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00584 | xnvzga 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00591 | invga injeciton 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00592 | xatda 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00600 | xatzda 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00607 | latda injeciton 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00608 | xavne 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00616 | xavzne 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00623 | navne injeciton 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00624 | xolan 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00632 | xolzan 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00639 | solan injeciton 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00640 | xriza 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00648 | xrizza 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00655 | triza injeciton 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00671 | abiify injeciton 1mg QD | abilify | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00687 | byanli injeciton 1mg QD | byannli | paliperidone\|PP6M | retrieval | 없음 |
| stress-00718 | lodpin injeciton 1mg QD | lodopin | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00734 | rexlti injeciton 1mg QD | rexulti | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00750 | sapris injeciton 1mg QD | saphris | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00766 | xepion injeciton 1mg QD | xeplion | paliperidone\|PP1M | retrieval | 없음 |
| stress-00782 | zypexa injeciton 1mg QD | zyprexa | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00789 | 에스 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00790 | 에스시 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00791 | 에스시탈 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00818 | arisada injeciton 1mg QD | aristada | aripiprazole\|ARI_LAUROXIL | retrieval | 없음 |
| stress-00834 | clozril injeciton 1mg QD | clozaril | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00865 | mainena injeciton 1mg QD | maintena | aripiprazole\|ARI_1M | retrieval | 없음 |
| stress-00881 | mellril injeciton 1mg QD | mellaril | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00912 | prolxin injeciton 1mg QD | prolixin | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00928 | serouel injeciton 1mg QD | seroquel | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00944 | asimufii injeciton 1mg QD | asimtufii | aripiprazole\|ARI_2M | retrieval | 없음 |
| stress-00960 | largctil injeciton 1mg QD | largactil | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00991 | perpenan injeciton 1mg QD | perphenan | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-01007 | risprdal injeciton 1mg QD | risperdal | risperidone\|non_product_specific | retrieval | 없음 |
| stress-01023 | serdlect injeciton 1mg QD | serdolect | sertindole\|non_product_specific | retrieval | 없음 |
| stress-01039 | stelzine injeciton 1mg QD | stelazine | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-01070 | zypahera injeciton 1mg QD | zypadhera | olanzapine\|OLZ_PAMOATE | retrieval | 없음 |

## stress — B 개선 retrieval + 거리순위 (164건)

| ID | 입력 | 원형 | 정답 target | 오류 | 1위 target |
| --- | --- | --- | --- | --- | --- |
| stress-00000 | 나틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00001 | 라나틸가 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00006 | 라가 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00011 | 래개틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00019 | 나다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00020 | 라나다투 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00025 | 라투 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00030 | 래태다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00038 | 나디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00039 | 렉나디설 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00044 | 렉설 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00049 | 랙샐디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00050 | ᄅᆨ설디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00057 | 나센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00063 | 로나 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00068 | 래내센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00076 | 나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00077 | 로나핀도 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00078 | 로 나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | ranking | blonanserin\|non_product_specific |
| stress-00082 | 로도 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00087 | 래대핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00095 | 나릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00096 | 멜나릴라 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00101 | 멜라 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00106 | 맬래릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00107 | ᄆᆯ라릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00114 | 나캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00115 | 세나캘로 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00120 | 세로 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00125 | 새래캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00133 | 나안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00134 | 솔나안리 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00139 | 솔리 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00144 | 샐래안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00145 | ᄉᆯ리안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00152 | 나가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00153 | 인나가베 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00158 | 인베 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00163 | 앤배가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00164 | ᄋᆫ베가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00171 | 나돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00172 | 지나돈오 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00177 | 지오 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00182 | 재애돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00190 | 나자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00191 | 트나자린 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00196 | 트린 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00201 | 태랜자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00209 | 트자 injeciton 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00210 | 나스달 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00211 | 리나스달패 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00216 | 리스 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00222 | 래새패달 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00230 | 나프스 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00231 | 사나프스리 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00236 | 사프 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00242 | 새패리스 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00250 | 나스나 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00251 | 서나스나티 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00256 | 서스 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00262 | 새새티나 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00270 | 서스나 injeciton 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00271 | 나르돌 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00272 | 세나르돌틴 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00277 | 세르 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00283 | 새래틴돌 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00291 | 나텔진 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00292 | 스나텔진라 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00297 | 스텔 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00303 | 새탤라진 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00311 | 나리졸 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00312 | 아나리졸피 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00317 | 아리 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00323 | 애래피졸 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00331 | 나란핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00332 | 올나란핀자 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00337 | 올란 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00343 | 앨랜자핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00344 | ᄋᆯ란자핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00351 | 나로린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00352 | 클나로린자 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00357 | 클로 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00363 | 캘래자린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00364 | ᄏᆯ로자린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00371 | 나릴폰 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00372 | 트나릴폰라 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00377 | 트릴 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00383 | 태랠라폰 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00391 | 나오센 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00392 | 티나오센틱 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00397 | 티오 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00403 | 태애틱센 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00411 | 나피라 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00412 | 하나피라에 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00417 | 하피 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00423 | 해패에라 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00431 | 하피라 injeciton 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00432 | xkdi 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00433 | oxkdei 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00440 | xkzdi 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00447 | okdi injeciton 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00448 | 나즈로핀 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00454 | 벤즈 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00455 | 벤즈트 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00460 | 밴재트로핀 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00468 | 나로리돈 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00474 | 일로 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00475 | 일로페 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00480 | 앨래페리돈 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00488 | 나루나진 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00494 | 플루 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00495 | 플루페 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00500 | 팰래페나진 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00508 | 나로리도 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00514 | 할로 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00515 | 할로페 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00520 | 핼래페리도 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00528 | xanpt 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00536 | xanzpt 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00543 | fanpt injeciton 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00544 | xeoon 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00552 | xeozon 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00559 | geoon injeciton 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00560 | xalol 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00568 | xalzol 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00575 | halol injeciton 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00576 | xnvga 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00584 | xnvzga 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00591 | invga injeciton 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00592 | xatda 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00600 | xatzda 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00607 | latda injeciton 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00608 | xavne 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00616 | xavzne 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00623 | navne injeciton 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00624 | xolan 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00632 | xolzan 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00639 | solan injeciton 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00640 | xriza 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00648 | xrizza 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00655 | triza injeciton 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00671 | abiify injeciton 1mg QD | abilify | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00687 | byanli injeciton 1mg QD | byannli | paliperidone\|PP6M | retrieval | 없음 |
| stress-00718 | lodpin injeciton 1mg QD | lodopin | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00734 | rexlti injeciton 1mg QD | rexulti | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00750 | sapris injeciton 1mg QD | saphris | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00766 | xepion injeciton 1mg QD | xeplion | paliperidone\|PP1M | retrieval | 없음 |
| stress-00782 | zypexa injeciton 1mg QD | zyprexa | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00789 | 에스 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00790 | 에스시 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00791 | 에스시탈 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00818 | arisada injeciton 1mg QD | aristada | aripiprazole\|ARI_LAUROXIL | retrieval | 없음 |
| stress-00834 | clozril injeciton 1mg QD | clozaril | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00865 | mainena injeciton 1mg QD | maintena | aripiprazole\|ARI_1M | retrieval | 없음 |
| stress-00881 | mellril injeciton 1mg QD | mellaril | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00912 | prolxin injeciton 1mg QD | prolixin | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00928 | serouel injeciton 1mg QD | seroquel | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00944 | asimufii injeciton 1mg QD | asimtufii | aripiprazole\|ARI_2M | retrieval | 없음 |
| stress-00960 | largctil injeciton 1mg QD | largactil | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00991 | perpenan injeciton 1mg QD | perphenan | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-01007 | risprdal injeciton 1mg QD | risperdal | risperidone\|non_product_specific | retrieval | 없음 |
| stress-01023 | serdlect injeciton 1mg QD | serdolect | sertindole\|non_product_specific | retrieval | 없음 |
| stress-01039 | stelzine injeciton 1mg QD | stelazine | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-01070 | zypahera injeciton 1mg QD | zypadhera | olanzapine\|OLZ_PAMOATE | retrieval | 없음 |

## stress — C 개선 retrieval + LR (164건)

| ID | 입력 | 원형 | 정답 target | 오류 | 1위 target |
| --- | --- | --- | --- | --- | --- |
| stress-00000 | 나틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00001 | 라나틸가 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00006 | 라가 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00011 | 래개틸 1mg QD | 라가틸 | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00019 | 나다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00020 | 라나다투 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00025 | 라투 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00030 | 래태다 1mg QD | 라투다 | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00038 | 나디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00039 | 렉나디설 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00044 | 렉설 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00049 | 랙샐디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00050 | ᄅᆨ설디 1mg QD | 렉설디 | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00057 | 나센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00063 | 로나 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00068 | 래내센 1mg QD | 로나센 | blonanserin\|non_product_specific | retrieval | 없음 |
| stress-00076 | 나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00077 | 로나핀도 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00078 | 로 나핀 1mg QD | 로도핀 | zotepine\|non_product_specific | ranking | blonanserin\|non_product_specific |
| stress-00082 | 로도 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00087 | 래대핀 1mg QD | 로도핀 | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00095 | 나릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00096 | 멜나릴라 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00101 | 멜라 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00106 | 맬래릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00107 | ᄆᆯ라릴 1mg QD | 멜라릴 | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00114 | 나캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00115 | 세나캘로 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00120 | 세로 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00125 | 새래캘 1mg QD | 세로캘 | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00133 | 나안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00134 | 솔나안리 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00139 | 솔리 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00144 | 샐래안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00145 | ᄉᆯ리안 1mg QD | 솔리안 | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00152 | 나가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00153 | 인나가베 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00158 | 인베 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00163 | 앤배가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00164 | ᄋᆫ베가 1mg QD | 인베가 | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00171 | 나돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00172 | 지나돈오 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00177 | 지오 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00182 | 재애돈 1mg QD | 지오돈 | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00190 | 나자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00191 | 트나자린 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00196 | 트린 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00201 | 태랜자 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00209 | 트자 injeciton 1mg QD | 트린자 | paliperidone\|PP3M | retrieval | 없음 |
| stress-00210 | 나스달 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00211 | 리나스달패 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00216 | 리스 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00222 | 래새패달 1mg QD | 리스패달 | risperidone\|non_product_specific | retrieval | 없음 |
| stress-00230 | 나프스 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00231 | 사나프스리 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00236 | 사프 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00242 | 새패리스 1mg QD | 사프리스 | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00250 | 나스나 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00251 | 서나스나티 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00256 | 서스 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00262 | 새새티나 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00270 | 서스나 injeciton 1mg QD | 서스티나 | paliperidone\|PP1M | retrieval | 없음 |
| stress-00271 | 나르돌 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00272 | 세나르돌틴 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00277 | 세르 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00283 | 새래틴돌 1mg QD | 세르틴돌 | sertindole\|non_product_specific | retrieval | 없음 |
| stress-00291 | 나텔진 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00292 | 스나텔진라 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00297 | 스텔 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00303 | 새탤라진 1mg QD | 스텔라진 | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-00311 | 나리졸 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00312 | 아나리졸피 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00317 | 아리 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00323 | 애래피졸 1mg QD | 아리피졸 | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00331 | 나란핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00332 | 올나란핀자 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00337 | 올란 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00343 | 앨랜자핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00344 | ᄋᆯ란자핀 1mg QD | 올란자핀 | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00351 | 나로린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00352 | 클나로린자 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00357 | 클로 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00363 | 캘래자린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00364 | ᄏᆯ로자린 1mg QD | 클로자린 | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00371 | 나릴폰 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00372 | 트나릴폰라 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00377 | 트릴 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00383 | 태랠라폰 1mg QD | 트릴라폰 | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-00391 | 나오센 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00392 | 티나오센틱 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00397 | 티오 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00403 | 태애틱센 1mg QD | 티오틱센 | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00411 | 나피라 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00412 | 하나피라에 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00417 | 하피 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00423 | 해패에라 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00431 | 하피라 injeciton 1mg QD | 하피에라 | paliperidone\|PP6M | retrieval | 없음 |
| stress-00432 | xkdi 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00433 | oxkdei 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00440 | xkzdi 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00447 | okdi injeciton 1mg QD | okedi | risperidone\|RIS_ISM | retrieval | 없음 |
| stress-00448 | 나즈로핀 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00454 | 벤즈 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00455 | 벤즈트 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00460 | 밴재트로핀 1mg QD | 벤즈트로핀 | benztropine\|non_product_specific | retrieval | 없음 |
| stress-00468 | 나로리돈 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00474 | 일로 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00475 | 일로페 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00480 | 앨래페리돈 1mg QD | 일로페리돈 | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00488 | 나루나진 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00494 | 플루 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00495 | 플루페 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00500 | 팰래페나진 1mg QD | 플루페나진 | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00508 | 나로리도 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00514 | 할로 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00515 | 할로페 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00520 | 핼래페리도 1mg QD | 할로페리도 | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00528 | xanpt 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00536 | xanzpt 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00543 | fanpt injeciton 1mg QD | fanapt | iloperidone\|non_product_specific | retrieval | 없음 |
| stress-00544 | xeoon 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00552 | xeozon 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00559 | geoon injeciton 1mg QD | geodon | ziprasidone\|non_product_specific | retrieval | 없음 |
| stress-00560 | xalol 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00568 | xalzol 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00575 | halol injeciton 1mg QD | haldol | haloperidol\|non_product_specific | retrieval | 없음 |
| stress-00576 | xnvga 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00584 | xnvzga 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00591 | invga injeciton 1mg QD | invega | paliperidone\|non_product_specific | retrieval | 없음 |
| stress-00592 | xatda 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00600 | xatzda 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00607 | latda injeciton 1mg QD | latuda | lurasidone\|non_product_specific | retrieval | 없음 |
| stress-00608 | xavne 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00616 | xavzne 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00623 | navne injeciton 1mg QD | navane | thiothixene\|non_product_specific | retrieval | 없음 |
| stress-00624 | xolan 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00632 | xolzan 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00639 | solan injeciton 1mg QD | solian | amisulpride\|non_product_specific | retrieval | 없음 |
| stress-00640 | xriza 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00648 | xrizza 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00655 | triza injeciton 1mg QD | trinza | paliperidone\|PP3M | retrieval | 없음 |
| stress-00671 | abiify injeciton 1mg QD | abilify | aripiprazole\|non_product_specific | retrieval | 없음 |
| stress-00687 | byanli injeciton 1mg QD | byannli | paliperidone\|PP6M | retrieval | 없음 |
| stress-00718 | lodpin injeciton 1mg QD | lodopin | zotepine\|non_product_specific | retrieval | 없음 |
| stress-00734 | rexlti injeciton 1mg QD | rexulti | brexpiprazole\|non_product_specific | retrieval | 없음 |
| stress-00750 | sapris injeciton 1mg QD | saphris | asenapine\|non_product_specific | retrieval | 없음 |
| stress-00766 | xepion injeciton 1mg QD | xeplion | paliperidone\|PP1M | retrieval | 없음 |
| stress-00782 | zypexa injeciton 1mg QD | zyprexa | olanzapine\|non_product_specific | retrieval | 없음 |
| stress-00789 | 에스 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00790 | 에스시 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00791 | 에스시탈 1mg QD | 에스시탈로프람 | escitalopram\|non_product_specific | retrieval | 없음 |
| stress-00818 | arisada injeciton 1mg QD | aristada | aripiprazole\|ARI_LAUROXIL | retrieval | 없음 |
| stress-00834 | clozril injeciton 1mg QD | clozaril | clozapine\|non_product_specific | retrieval | 없음 |
| stress-00865 | mainena injeciton 1mg QD | maintena | aripiprazole\|ARI_1M | retrieval | 없음 |
| stress-00881 | mellril injeciton 1mg QD | mellaril | thioridazine\|non_product_specific | retrieval | 없음 |
| stress-00912 | prolxin injeciton 1mg QD | prolixin | fluphenazine\|non_product_specific | retrieval | 없음 |
| stress-00928 | serouel injeciton 1mg QD | seroquel | quetiapine\|non_product_specific | retrieval | 없음 |
| stress-00944 | asimufii injeciton 1mg QD | asimtufii | aripiprazole\|ARI_2M | retrieval | 없음 |
| stress-00960 | largctil injeciton 1mg QD | largactil | chlorpromazine\|non_product_specific | retrieval | 없음 |
| stress-00991 | perpenan injeciton 1mg QD | perphenan | perphenazine\|non_product_specific | retrieval | 없음 |
| stress-01007 | risprdal injeciton 1mg QD | risperdal | risperidone\|non_product_specific | retrieval | 없음 |
| stress-01023 | serdlect injeciton 1mg QD | serdolect | sertindole\|non_product_specific | retrieval | 없음 |
| stress-01039 | stelzine injeciton 1mg QD | stelazine | trifluoperazine\|non_product_specific | retrieval | 없음 |
| stress-01070 | zypahera injeciton 1mg QD | zypadhera | olanzapine\|OLZ_PAMOATE | retrieval | 없음 |
