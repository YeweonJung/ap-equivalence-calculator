# 항우울제 제외 처리 업데이트 (2026-09-28)

확인된 항우울제는 항정신병약 환산 대상에서 제외하며 CPZ/OLZ 환산값에 0을 표시합니다. 이 값은 실제 항우울제 복용량이나 약효의 환산값이 아닙니다. 원문 용량은 그대로 보존합니다.

- 한 줄 계산, 결과 다운로드, CSV/Excel 및 환자·처방일별 분석에 같은 규칙을 적용합니다.
- 항우울제만 있으면 0, 항정신병약과 함께 있으면 항정신병약만 합산합니다.
- 미확인 약물, 성분 충돌, 항정신병약 환산계수 누락은 계속 빈칸·Review 대상으로 남습니다. 복합제 이름을 단일 항우울제로 등록하지 않습니다.
- 날짜별 분석은 같은 환자·같은 처방일에만 적용합니다. 다른 날짜 처방을 가져오지 않습니다.
- 항우울제 제외에는 용량·단위·빈도 확정이 필요하지 않습니다. 원본 날짜·ID·중복 오류는 AuditTrail과 Review에 보존합니다.
- Results / MedicationResults / Review / AuditTrail의 4개 시트를 유지합니다. 약물별 0과 제외 사유를 표시하고 모든 원본 행을 감사 기록에 보존합니다.
- 시작 시 로컬 사전을 한 번 읽습니다. 처리 중 AI 호출, 웹 검색, 후보 추천은 없습니다. 기존 항정신병약 환산계수는 변경하지 않았습니다.

## 등록 사전

18개 성분, 201개 인식 표기(성분명·제품명·한글 제형 접미사 포함)입니다. 201개 제품을 뜻하지 않습니다. 과거 제품명도 인식하며 현재 국내 판매 여부나 처방 빈도 순위를 뜻하지 않습니다.

| 성분 | 직접 등록한 이름 | 근거 |
|---|---|---|
| escitalopram | 에스시탈로프람, 렉사프로, Lexapro, Cipralex | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [lundbeck](https://lundbeck-prod.adobemsbasic.com/global/our-science/products) |
| citalopram | 시탈로프람, Citalopram, Celexa, Cipramil | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [celexa](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=4259d9b1-de34-43a4-85a8-41dd214e9177), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| sertraline | 설트랄린, 졸로푸트, Zoloft, Lustral | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [pfizer_kr](https://www.pfizer.co.kr/products-list), [nhs_treatment](https://www.nhs.uk/mental-health/conditions/depression-in-adults/treatment/) |
| fluoxetine | 플루옥세틴, 푸로작, Prozac | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [prozac_kr](https://common.health.kr/shared/images/insert_pdf/IN_A11AOOOOO2927_01.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| paroxetine | 파록세틴, Seroxat, Paxil | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf), [paxil](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ef3b5cbe-f9e1-c1ac-79da-cfe14e3a7e7e) |
| fluvoxamine | 플루복사민, Faverin, Luvox | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf), [luvox](https://www.accessdata.fda.gov/drugsatfda_docs/label/2007/021519lbl.pdf) |
| venlafaxine | 벤라팍신, 이팩사, Effexor, Efexor | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [pfizer_kr](https://www.pfizer.co.kr/products-list), [nhs_treatment](https://www.nhs.uk/mental-health/conditions/depression-in-adults/treatment/) |
| desvenlafaxine | 데스벤라팍신, Pristiq | [pristiq](https://www.pfizermedical.com/pristiq) |
| duloxetine | 둘록세틴, 심발타, Cymbalta | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [cymbalta_kr](https://common.health.kr/shared/images/insert_pdf/IN_tgbuow56mj311_01.pdf), [nhs_treatment](https://www.nhs.uk/mental-health/conditions/depression-in-adults/treatment/) |
| bupropion | 부프로피온, 웰부트린, Wellbutrin | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [bupropion_kr](https://www.cancer.go.kr/lay1/S1T204C209/contents.do) |
| mirtazapine | 미르타자핀, 레메론, Remeron | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [organon_kr](https://www.organon.com/korea/our-focus/products-list/) |
| trazodone | 트라조돈, Molipaxin | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| vortioxetine | 보티옥세틴, 브린텔릭스, Brintellix, Trintellix | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [brintellix_kr](https://www.lundbeck.com/content/dam/lundbeck-com/asia/korea/product/brintellix/KR_Brintellix%205%2010%2020mg%20Leaflet_for%20homepage%20upload.pdf), [lundbeck](https://lundbeck-prod.adobemsbasic.com/global/our-science/products), [trintellix](https://www.takeda.com/newsroom/newsreleases/2016/brintellix-vortioxetine-renamed-trintellix-vortioxetine-in-us-to-avoid-name-confusion/) |
| amitriptyline | 아미트리프틸린, Tryptizol, Lentizol | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| clomipramine | 클로미프라민, Anafranil | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| imipramine | 이미프라민, Tofranil | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| nortriptyline | 노르트립틸린, Allegron, Aventyl | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |
| doxepin | 독세핀, Sinequan | [nhs_classification](https://www.tewv.nhs.uk/wp-content/uploads/2025/10/Antidepressant-Handy-Hints.pdf), [nhs_brands](https://talk2gether.nhs.uk/wp-content/uploads/2017/02/Workbook_Depression_March2016.pdf) |

기계 판독 사전: `lookup/antidepressant_names.json`. 한글 이름 뒤의 정·캡슐·서방정·서방캡슐·오디정은 입력 표기 변형으로 지원하며, 개별 제품 허가를 의미하지 않습니다.
