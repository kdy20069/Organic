# 아세트아미노펜 가산점 분석 준비물

## ASKCOS · Parrot 조건 후보 요약

정방향 반응은 아세트산 무수물 + p-아미노페놀 → 아세트아미노펜이다. ASKCOS v2 FP의 상위 3개와 Parrot 상위 3개는 각각 `../results/REPORT.md`의 실제 원응답을 바탕으로 요약했다. ASKCOS 온도는 K에서 °C로 `K − 273.15` 변환했다. Parrot USPTO 설정은 온도를 예측하지 않는다.

| 모델·순위 | 조건 성분 | 온도 (°C) | 성분 충돌 검토 |
|---|---|---:|---|
| ASKCOS 1 | 아세트산 무수물, p-아미노페놀 | 43.65 | 두 입력 반응물만 제시. 아민 아세틸화와 양립 가능; 조건에 따라 페놀성 O-아세틸화가 경쟁할 수 있음. |
| ASKCOS 2 | 아세트산 무수물, p-아미노페놀, 물 | 43.35 | **충돌:** 물이 아세트산 무수물을 가수분해해 아세틸화제를 소모할 수 있음. |
| ASKCOS 3 | 아세트산 무수물, p-아미노페놀, 디클로로메탄, 트리에틸아민 | 8.67 | 뚜렷한 직접 충돌은 없음; 용매·산 포집 염기로 해석 가능. |
| Parrot 1 | 물 (solvent1) | 예측 없음 | 아세트산 무수물의 가수분해 경쟁 가능성. |
| Parrot 2 | 에탄올 (solvent1) | 예측 없음 | 무수물과 반응해 에틸 아세테이트를 만들 수 있어 경쟁 소비 우려. |
| Parrot 3 | DMF (solvent1) | 예측 없음 | 뚜렷한 직접 반응 모순은 확인되지 않음. 촉매·시약 없이 용매만 예측. |

모델 score는 수율이나 성공 확률이 아니다. 조건은 학습 데이터 기반 후보이므로 실제 실험값으로 취급하지 않는다.

## CAS 및 EPI Suite 비교용 빈 표

CAS 번호는 [PubChem 4-aminophenol](https://pubchem.ncbi.nlm.nih.gov/compound/403), [acetic anhydride](https://pubchem.ncbi.nlm.nih.gov/compound/7918), [acetaminophen CID 1983](https://pubchem.ncbi.nlm.nih.gov/compound/1983) 레코드를 기준으로 확인했다. 아래 물성 칸은 EPI Suite 조회 후 채울 수 있게 비워 뒀다. 조건 온도는 선택한 ASKCOS 1순위의 예측값이다.

| 물질 | CAS | 녹는점 (°C, EPI Suite) | 끓는점 (°C, EPI Suite) | 비교 온도 (ASKCOS, °C) | 반응 온도에서의 상태·검토 |
|---|---|---:|---:|---:|---|
| p-아미노페놀 | 123-30-8 |  |  | 43.65 |  |
| 아세트산 무수물 | 108-24-7 |  |  | 43.65 |  |
| 아세트아미노펜 | 103-90-2 |  |  | 43.65 |  |

## 생성한 구조 파일

- 2D PNG: `acetaminophen_2d.png`, `p_aminophenol_2d.png`, `acetic_anhydride_2d.png`
- 정방향 반응식 도식: `forward_reaction_scheme.png` (부산물 아세트산 포함)
- Discovery Studio Visualizer용 3D SDF: `3d_structures/p_aminophenol.sdf`, `3d_structures/acetic_anhydride.sdf`. 두 파일 모두 수소를 명시적으로 포함하고 3D 좌표를 갖는다.
- MOPAC 계산 파일과 pKa 결과: `mopac_summary.md` 및 `mopac/` 아래 `.mop`·`.out` 파일.
