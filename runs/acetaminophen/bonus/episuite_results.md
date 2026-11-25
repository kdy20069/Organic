# EPI Suite 물성 조회 결과

- 조회일: 2026-11-24
- 실제 조회 서버: `https://episuite.dev/api`
- 사용 요청: CAS 검색 `/api/search?query={CAS}&limit=10`, 물성 조회 `/api/submit?cas={CAS}&modules=physicalProperties`
- 세 물질의 검색·물성 조회 요청은 모두 HTTP 200이었다. 원본 응답 본문은 `episuite_raw/`에 그대로 저장했다.
- EPI OpenAPI는 런타임 상태를 `degraded`로 표시했지만, 이번 여섯 요청은 성공했다.

## 값 선택 원칙

요청한 대로 `valueType=EXPERIMENTAL` 값이 있으면 먼저 선택하고, 없으면 `ESTIMATED`를 사용했다. 이번 응답에는 `valueType=EXPERIMENTAL`로 지정된 물성이 없었다. EPI 응답의 `experimentalValues` 배열에는 `valueType=EVIDENCE`, `evidenceType=UNSPECIFIED` 항목이 있었으며, 일부 출처 설명은 “calculated” 또는 “slope analogy”다. 이를 실험 측정값으로 바꾸어 부르지 않고 별도로 기록했다. 상태 판정 표의 기준 물성은 따라서 EPI 응답의 `estimatedValue`다.

## 추천 반응 온도와 물질 상태 비교

ASKCOS v2 FP 상위 후보 1의 원본 온도 `316.8039430618286 K`를 `K − 273.15`로 바꾸어 **43.65 °C**로 비교했다. 다른 후보 온도는 2위 43.35 °C, 3위 8.67 °C다. 반응물과 생성물 모두 1순위 온도에 노출된다고 두고 융점·비점을 비교했다.

| 물질 | CAS | 융점 °C (선택값: ESTIMATED) | 끓는점 °C (선택값: ESTIMATED) | EPI `EVIDENCE` 융점 / 끓는점 °C (실험값으로 미분류) | ASKCOS 온도 °C | 온도에서의 상태 (ESTIMATED 기준) |
|---|---|---:|---:|---|---:|---|
| p-아미노페놀 | 123-30-8 | 53.5708 | 241.8360 | 187.5 / 284.0 | 43.65 | 고체 (43.65 < 융점) |
| 아세트산 무수물 | 108-24-7 | -95.0991 | 52.6180 | -73.0 / 139.5 | 43.65 | 액체 (융점 < 43.65 < 끓는점) |
| 아세트아미노펜 | 103-90-2 | 119.9227 | 340.6538 | 170.0 / 자료 없음 | 43.65 | 고체 (43.65 < 융점) |

`EVIDENCE` 값 설명: p-아미노페놀 융점 187.5 °C는 “Physprop calculated - based upon VP / Water Sol data”, 아세트산 무수물 융점 −73.0 °C는 “Ester slope analogy”, 아세트아미노펜 융점 170.0 °C는 “-N-C(=O) type slope analogy”로 응답에 기재되어 있었다. 다른 두 `EVIDENCE` 끓는점은 API 응답에서 각각 284.0 °C와 139.5 °C였고, `evidenceType`은 `UNSPECIFIED`였다. 값의 원문 분류와 출처는 JSON 파일을 확인한다.

## 원본 응답

`episuite_raw/`에 각 CAS별 검색 원문 `search_{CAS}.json`과 물성 원문 `properties_{CAS}.json`을 저장했다. 각각의 HTTP 상태는 같은 이름의 `.http_status.txt`에 기록했다. 응답 JSON 본문은 가공·재포맷하지 않았다.
