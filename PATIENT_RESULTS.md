# 환자별 결과 사용법

첫 시트 Results는 patient_id별 한 행입니다. CMD, MED, DDD, ED95, GARDNER, WOODS, CPZ_FGA, CMD_DIRECT, CMD_INDIRECT 순으로 제공하며 각 열에 기준 약물(CPZ/OLZ)과 mg/day 단위를 표시합니다.

- 기존 데이터에 patient_id를 키로 left join/merge 하세요. 행 순서로 붙이지 마세요.
- 원본 ID를 문자열로 보존합니다. 앞자리 0을 유지하려면 입력 Excel의 ID를 텍스트로 저장하세요. 표시 형식으로만 붙인 0은 원본 값에 포함되지 않습니다.
- 파일의 모든 시트·행·약물 열에서 같은 ID를 합산합니다. 동일 시점 처방만 넣으세요. 중복 처방 행은 자동 제거하지 않습니다.
- ID가 없으면 행별 임시 ID(__MISSING_ID_...)를 부여하고 Errors에 표시합니다. 병합 전 수정하세요.
- 대상 약물 중 환산 불가 항목이 있으면 해당 방법의 환자 합계는 빈칸입니다. PatientChecks에서 부분합, 환산/미해결/제외 개수, 검토 필요 여부를 확인하세요. 빈칸은 0이 아닙니다.
- 비대상 약물은 합계에서 제외합니다. 빈 처방 또는 비대상 약물만 있으면 합계를 비워둡니다.
- MedicationResults, Detailed, CellTotals, AuditTrail은 계산 근거를 확인하는 보조 시트입니다.
- 환산 계수와 LAI 변환 방식은 변경하지 않았습니다. 이름/등록번호 대신 연구용 가명 ID를 입력하세요.
