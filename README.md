# 유기합성 AI 기말 프로젝트 — 아세트아미노펜(Acetaminophen)

아세트아미노펜(`CC(=O)Nc1ccc(O)cc1`, CAS `103-90-2`)을 대상으로 합성 경로·조건·산출율 모델 6종과 물성·양자·3D 구조 분석을 수행하고, 이를 재현 가능한 스킬(`SKILL.md`)과 최종 보고서로 정리한 저장소입니다.

## 저장소 구조

- `report/acetaminophen_report.pdf`: 최종 보고서 (PDF, 10쪽)
- `report/acetaminophen_report.docx`: 최종 보고서 (DOCX)
- `report/report.md`: 보고서 원본 마크다운
- `skill/SKILL.md`: 6개 모델 실행·근거 연결·보고서 생성용 재사용 스킬 문서
- `skill/scripts/export_report_local.py`: Markdown → DOCX/PDF 변환 스크립트
- `runs/acetaminophen/`: 모델별 원본 실행 결과(`results/`, `aizynthfinder/`, `synthex/`) 및 가산점 분석 자료(`bonus/`)

*(참고: 외부 오픈소스 모델 저장소 6종과 대용량 가중치·데이터 파일, 개인 환경 설정은 `.gitignore`로 제외했으며, 각 모델 저장소 주소와 실행 절차는 `skill/SKILL.md`에 기록했습니다.)*

## 주요 실행 요약

| 구분 | 모델 / 도구 | 상태 | 핵심 결과 및 근거 위치 |
|---|---|---|---|
| 합성 경로 | AiZynthFinder 4.4.1 | 완료 | `is_solved=true` (46개 중 23개 해결), 최상위 1단계 경로(아세트산 무수물 + p-아미노페놀) 선택 (`runs/acetaminophen/aizynthfinder/`) |
| 합성 경로 | SynthEx (submission, Solar Pro 4) | 경로 구축 실패 | 전략 2건 생성 후 `routes` 단계 `ValueError`(`break_bond` 오류)로 중단 (`runs/acetaminophen/synthex/run2/`) |
| 합성 조건 | ASKCOS v2 FP | 완료 | Docker(Apple Silicon 임시 ARM64 빌드)로 상위 3개 후보 예측, 1순위 316.80 K(43.65 °C), 2순위 물 가수분해 충돌 확인 (`runs/acetaminophen/results/askcos_raw.json`) |
| 합성 조건 | Parrot | 완료 | CPU 추론으로 15개 후보 생성(온도 미예측), 물·에탄올 경쟁 반응 주의 (`runs/acetaminophen/results/parrot_raw.csv`) |
| 산출율 | Yield-BERT / DRFP | 적용 불가 판정 | 번들 체크포인트 학습 반응군(Buchwald–Hartwig C–N 커플링) 밖으로 판정하여 `null` 기록 (`runs/acetaminophen/results/`) |
| 가산점 분석 | EPI Suite / MOPAC / 2D·3D CPK | 완료 | EPI Suite API 물성 및 43.65 °C 상태 비교, MOPAC 전하 확인 및 O–H pKa 계산(9.786 / 9.495), RDKit 2D 구조·반응식 4장, Discovery Studio Visualizer 3D CPK·막대 모형 캡처 (`runs/acetaminophen/bonus/`) |

## 재현 및 보고서 확인

- 전체 모델 실행 절차와 해석 규칙은 [`skill/SKILL.md`](skill/SKILL.md)에서 확인할 수 있습니다.
- 최종 보고서는 [`report/acetaminophen_report.pdf`](report/acetaminophen_report.pdf) 또는 [`report/report.md`](report/report.md)에서 바로 열람할 수 있습니다.
