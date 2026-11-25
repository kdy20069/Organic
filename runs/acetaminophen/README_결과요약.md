# 아세트아미노펜 합성 경로 모델 실행 결과

- 입력 구조: `Conformer3D_COMPOUND_CID_1983.sdf` (PubChem CID 1983)
- RDKit canonical SMILES: `CC(=O)Nc1ccc(O)cc1`
- 타깃 파일: `target.smi`

## 모델 실행 준비 상태

| 폴더 | 현 상태 | 확인 근거 / 추가 작업 |
|---|---|---|
| AiZynthFinder | **실행 가능, 이번 검색 성공** | Python 3.10 환경, AiZynthFinder 4.4.1, pip check 통과. USPTO ONNX/템플릿/filter 및 ZINC stock 자산 해시가 manifest와 일치. |
| SynthEx | **API 연결 및 전략 생성 가능, 완전 경로는 실패** | Python 3.11 전용 환경과 Solar Pro 4/Upstage 설정 및 인증이 작동. 전략 생성은 성공했으나 생성 경로의 ReactionJSON/결합 검증 실패. |
| context_recommender | **추가 설치/설정 필요** | 저장소만 있음. `data/tfx/models.config` 외 훈련 모델 체크포인트 없음. README의 `scripts/download_trained_models.sh` 및 의존성/서비스 설정 필요. |
| Parrot | **추가 설치/데이터 필요** | 소스·일부 데이터/분석 pickle은 있음. `outputs`에 모델 가중치 없음(keep 파일만). README 지시 모델·데이터 다운로드와 Conda/PyTorch 환경 필요. |
| rxn_yields | **모델 파일은 있으나 즉시 실행 불가** | 여러 USPTO/Suzuki/Buchwald-Hartwig 체크포인트 존재. 전용 의존성·rxnfp pretrained base/model 설정을 맞춘 환경 구성 및 입력 반응 포맷 확인 필요. 합성경로 탐색 모델은 아님. |
| drfp | **특정 분석 모델 파일 있음, 일반 실행 준비는 추가 설정 필요** | DRFP/XGBoost pickle 및 Buchwald-Hartwig 모델은 있음. 패키지 의존성 환경 구성 필요. 반응 fingerprint/조건·수율 분석 도구이며 합성경로 탐색기는 아님. |

## AiZynthFinder 결과

실제 명령으로 검색했고 `is_solved=true`, solved 경로 23개, 총 경로 46개, 검색 시간 3.324초, 검색 노드 74개였습니다. 상위 경로는 한 단계로 아세트아미노펜을 아세트산 무수물(`CC(=O)OC(C)=O`)과 p-아미노페놀(`Nc1ccc(O)cc1`)로 분해하며 두 전구체가 설정한 ZINC stock에 있었습니다. 이는 모델의 stock 도달 결과이며 실험 검증을 뜻하지 않습니다.

## SynthEx (Solar Pro 4) 결과

Upstage OpenAI-compatible API로 Solar Pro 4를 실제 호출했습니다. 전략 생성 checkpoint는 만들어졌지만 경로 단계에서 두 제안이 모두 실패했습니다. manifest에 기록된 첫 오류는 `Route Builder exhausted 2 proposals for step 2`이며 구체적으로 `break_bond`가 map 2와 8 사이에 존재하지 않는 결합을 끊으려 했습니다. 성공한 `routes.json` 또는 분석 결과는 생성되지 않았습니다. 실행 폴더의 `manifest.json`, `strategies.json`, `execution2.log`를 확인하세요.

첫 번째 오프라인 시도도 별도 `run/manifest.json` 및 `execution.log`에 남겼습니다. 오류는 `<urlopen error [Errno 8] nodename nor servname provided, or not known>`였고 이후 네트워크 허용 재실행에서 API 접근과 전략 생성이 성공했습니다.

## 생성 파일

- `aizynthfinder/routes.json`: AiZynthFinder 원본 결과 전체
- `aizynthfinder/stats.json`: 원본 routes.json의 `data[0]`에서 통계 필드만 추출
- `aizynthfinder/manifest.json`, `run.log`: 설정/자산 해시 및 실행 기록
- `synthex/run2/manifest.json`, `strategies.json`, `execution2.log`: 실제 Solar Pro 4 실행 및 실패 기록
