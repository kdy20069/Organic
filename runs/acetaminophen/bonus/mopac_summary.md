# MOPAC 양자 계산 요약

13주차 4.3 절차를 적용했다: 3D 중성 분자의 `CHARGES` 점검에서 이상 전하가 없는지 먼저 확인한 다음, `PM6 pKa CHARGE=0`으로 O–H 수소의 pKa를 계산했다. 3D 좌표는 RDKit ETKDG/MMFF94로 준비했으며, 아세트아미노펜은 제공된 PubChem CID 1983 conformer를 읽어 MMFF94로 정리했다. pKa는 실험값이 아닌 계산 추정값이다.

| 물질 | CHARGES 결과 | pKa 입력 | pKa 출력 | pKa (O–H H 원자 번호) | 종료 상태 |
|---|---|---|---|---:|---|
| p-아미노페놀 | `NO CHARGES FOUND.` | `mopac/p_aminophenol_pka.mop` | `mopac/p_aminophenol_pka.out` | 9.786 (H atom 13) | 두 실행 모두 exit code 0; pKa 작업 `JOB ENDED NORMALLY` |
| 아세트아미노펜 | `NO CHARGES FOUND.` | `mopac/acetaminophen_pka.mop` | `mopac/acetaminophen_pka.out` | 9.495 (H atom 12) | 두 실행 모두 exit code 0; pKa 작업 `JOB ENDED NORMALLY` |

전하 점검의 원본 입력·출력은 각각 `mopac/p_aminophenol_charges.mop`, `mopac/p_aminophenol_charges.out`, `mopac/acetaminophen_charges.mop`, `mopac/acetaminophen_charges.out`에 보존했다. `CHARGES` 계산이 “JOB STOPPED HERE BECAUSE KEYWORD `CHARGES` WAS USED”로 종료되는 것은 전하만 출력하고 계산을 멈추는 해당 키워드의 정상 동작이다.

아세트아미노펜 O–H pKa는 p-아미노페놀보다 계산상 약 0.29 낮다. 두 값의 차이는 모델 기반 비교이며, 이 계산만으로 실험 조건에서의 반응성이나 반응 선택성을 확정하지 않는다. MOPAC 출력에 Intel MKL SSE4.2 사용 중단 예정 경고가 있었지만, 계산은 모두 정상 종료했다.
