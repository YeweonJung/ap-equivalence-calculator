# 제품별 주사제 정보와 처리 속도

공식 자료 확인일: 2026-09-28. 기존 경구 환산계수는 변경하지 않았습니다.

| 제품 | 입력 용량 / 간격 | 경구 risperidone 대응 mg/day |
| --- | --- | --- |
| UZEDY (피하) | 50 / 75 / 100 / 125 mg, 매월 | 2 / 3 / 4 / 5 |
| UZEDY (피하) | 100 / 150 / 200 / 250 mg, 2개월 | 2 / 3 / 4 / 5 |
| PERSERIS (피하) | 90 / 120 mg, 매월 | 3 / 4 |
| RISPERDAL CONSTA (근육) | 12.5 / 25 / 37.5 / 50 mg, 2주 | 단일 대응용량 미적용; DDD만 |

- [UZEDY 공식 설명서, 표 1](https://www.uzedy.com/globalassets/uzedy/prescribing-information.pdf)
- [PERSERIS 공식 설명서, 2.1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a4f21b1a-5691-4b14-a56d-651962d06f39)
- [RISPERDAL CONSTA 공식 설명서](https://www.jnjlabels.com/package-insert/product-monograph/prescribing-information/RISPERDAL%20CONSTA-pi.pdf)
- [WHO risperidone depot DDD: 2.7 mg](https://atcddd.fhi.no/atc_ddd_index/?code=N05AX08&showdescription=no)
- [WHO chlorpromazine 경구 DDD: 300 mg](https://atcddd.fhi.no/atc_ddd_index/?code=N05AA01&showdescription=no)

새 제품은 간격을 반드시 입력합니다. 월 단위는 기존 연구 규칙인 30일로 정규화하며 q4w(28일)와 구분합니다. DDD는 투여량/간격/2.7×300으로 계산합니다. 다른 환산법은 허가문서의 경구 대응량을 거치는 추정이며 주사제 직접 환산계수가 아닙니다. AuditTrail에 제품, 간격, 경구 대응량, 근거 URL이 남습니다. 초기·부하요법, 불명확한 간격, 경로 충돌은 확인 대상으로 남습니다. 이는 약물 전환 처방 지침이 아닙니다.

엑셀은 하나의 파일 연결을 공유하고 제목행 판별에는 앞부분만 읽은 후 선택된 시트 데이터를 한 번 읽습니다. 약물명은 시작할 때 만든 단일 검색식으로 처리합니다. 실행 중 외부 검색이나 AI 호출은 없습니다. 결과 시트는 Results, MedicationResults, Review, AuditTrail 네 개를 유지합니다.

공개 앱의 환산·엑셀 생성은 서버에서 이루어져 다른 PC도 같은 처리 코드를 사용합니다. 실제 대기시간은 파일 크기, 통신 상태, 동시 사용량에 따라 달라집니다. 저장소 render.yaml은 무료 플랜이며 [Render 무료 서비스](https://render.com/docs/free)는 15분 비활성 후 중지되어 재시작 시간이 발생합니다. 유료 상시 실행 서버로의 변경은 별도 운영 결정이며 이번 변경에서 요금제는 바꾸지 않습니다.

## 로컬 검증

동일 PC에서 각 3회 측정한 중앙값: 실제 CSV(88명,144약물) 전체 요청 처리 0.659초 → 0.535초(약19% 단축). 합성 Excel 5,000행의 파일 읽기만 3.063초 → 0.597초(약81% 단축). 후자는 전체 업로드 처리시간이 아니며 네트워크와 서버 재시작 시간은 포함하지 않습니다. 기존 792개 환산값과 144개 감사 항목이 일치합니다. Python 검사 449개와 두 UI 검사가 통과했습니다.
