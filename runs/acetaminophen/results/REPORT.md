# 아세트아미노펜 조건·수율 모델 실행 보고서

## 반응 입력

선택한 AiZynthFinder 상위 역합성 경로를 정방향으로 뒤집어 한 단계로 구성했다.

`CC(=O)OC(C)=O.Nc1ccc(O)cc1>>CC(=O)Nc1ccc(O)cc1` (모델 입력; 주생성물 기준)

아세트산 부산물까지 포함한 화학량론 식은 `CC(=O)OC(C)=O.Nc1ccc(O)cc1>>CC(=O)Nc1ccc(O)cc1.CC(=O)O`이다. 원본 AiZynthFinder 반응 노드에는 타깃 제품만 있어 조건 모델 입력은 그 형식을 보존했다. 상세 구조와 출처는 `route_reactions.json`에 있다.

## Parrot 조건 예측

Parrot USPTO 체크포인트를 내려받아 압축 해제했고, 체크포인트가 요구하는 USPTO condition-label map도 함께 설치했다. 전용 환경은 `/Users/kdy20069/miniconda3/envs/parrot-cpu` (conda-forge, Python 3.9.23, PyTorch 1.13.1, RDKit 2025.03.5, Transformers 4.18.0, tokenizers 0.12.1, SimpleTransformers 0.63.6, rxnfp 0.1.0)이다. Apple Silicon CPU에서 실제 추론이 성공했고, 원본 CSV에는 후보 15개가 저장됐다. 사용 명령은 저장소의 `inference.py`에 `--gpu -1 --num_workers 1 --inference_batch_size 8`을 전달했다. 상세 stdout/stderr와 종료코드는 `parrot_execution.log`에 보존했다.

원본 CSV의 상위 3개는 다음과 같다.

| 순위 | catalyst1 | solvent1 | solvent2 | reagent1 | reagent2 | score | 화학 검토 |
|---|---|---|---|---|---|---:|---|
| 1 | — | 물 (`O`) | — | — | — | -0.8904 | 아세트산 무수물은 물과 가수분해될 수 있어 경쟁 소모 주의. 수용액 아세틸화 조건 자체가 불가능하다는 뜻은 아님. |
| 2 | — | 에탄올 (`CCO`) | — | — | — | -2.5844 | 에탄올이 무수물에 의해 에틸 아세테이트로 아세틸화될 수 있어 경쟁 소비 우려. |
| 3 | — | DMF (`CN(C)C=O`) | — | — | — | -2.8837 | 분명한 직접 상호 반응 모순은 보이지 않음. 용매만 추천됐으며 촉매·시약은 비어 있어 별도 조건 완성은 필요. |

화학 검토는 모델 후보 성분의 구조에 근거한 주의 표시다. 모델 score는 beam-search 순위 점수로 확률이나 수율이 아니다. Parrot 공개 USPTO 설정은 온도를 예측하지 않는다. `parrot_raw.csv`는 15개 후보를 포함한 원본 출력이며 요약 표는 상위 3개만 옮겼다.

## ASKCOS v2 FP 조건 예측

v2 가중치 `v2.tar.gz`를 받아 `context_recommender/app/resources/models/context/v2/`에 풀었다. Apple Silicon Docker Engine(`linux/aarch64`)에서 저장소 기본 이미지 빌드는 `tensorflow-cpu==2.7.4` ARM64 wheel 부재로 실패했다. TensorFlow 2.7.4의 ARM64 배포판인 `tensorflow-aarch64==2.7.4`와 conda-forge `h5py`를 쓰는 임시 Dockerfile로 빌드해 서비스를 실행했다. 원본 Dockerfile은 바꾸지 않았다. 서비스 `/health`는 `{"message":"Alive!"}`를 반환했고, `POST /api/v2/condition/FP` 실제 응답 전체는 `askcos_raw.json`에 저장했다.

모델 입력은 `CC(=O)OC(C)=O.Nc1ccc(O)cc1>>CC(=O)Nc1ccc(O)cc1`, `reagents=[]`, `n_conditions=3`이다. 온도 변환은 °C = K − 273.15이다.

| 순위 | 후보 성분 (모델 역할/양 그대로) | 온도 (K) | 온도 (°C) | score | 화학 검토 |
|---|---|---:|---:|---:|---|
| 1 | 아세트산 무수물 (REACTANT, 1.3159), p-아미노페놀 (REACTANT, 1.0000) | 316.8039 | 43.6539 | 0.113133 | 추가 용매·촉매·시약 후보가 없음. 아민 아세틸화로 설명 가능한 조합이다. 다만 무수물 과량·조건에 따라 페놀성 OH의 O-아세틸화가 경쟁할 수 있어 선택성은 실험 확인이 필요하다. |
| 2 | 아세트산 무수물 (REACTANT, 1.3062), p-아미노페놀 (REACTANT, 1.0000), 물 (성분 역할 미지정, 119.5522) | 316.5035 | 43.3535 | 0.028005 | **강한 충돌:** 물은 아세트산 무수물을 가수분해해 아세틸화제를 소모한다. 모델이 큰 양으로 제시했으므로 그대로 재현할 조건으로 보기 어렵다. |
| 3 | 아세트산 무수물 (REACTANT, 1.1415), p-아미노페놀 (REACTANT, 1.0000), 디클로로메탄 (성분 역할 미지정, 25.5039), 트리에틸아민 (성분 역할 미지정, 1.7188) | 281.8193 | 8.6693 | 0.024417 | 뚜렷한 직접 반응 모순은 확인되지 않았다. 디클로로메탄은 용매로, 트리에틸아민은 산 포집 염기로 해석 가능한 조합이다. 온도는 디클로로메탄의 끓는점보다 낮다. |

모델이 제공하지 않은 성분 역할은 임의로 단정하지 않고 “미지정”으로 표기했다. 성분 양은 모델 원응답 값을 반올림해 보고했으며 score는 수율이나 성공 확률이 아니다. 예측 후 메모리 절약을 위해 `context_recommender` 컨테이너를 정지했다.

### 실행 환경 기록

- Docker Desktop에서 ARM64 이미지 빌드와 서비스 실행에 성공했다. 기본 Dockerfile 빌드 오류 및 ARM64 대체 빌드 내용은 `environment_status.json`에 기록했다.
- Python 3.8 / RDKit 2020.09.5 / TensorFlow ARM64 2.7.4로 실행했다. 빌드 중 SciPy 1.7.3과 NumPy 1.24.4 버전 범위 경고가 있었지만 모델 로딩 및 API 예측은 완료됐다.
- 컨테이너는 예측 후 종료했다.

## 수율 모델 적용성

이번 단계는 아릴 할라이드와 아민의 Pd 촉매 Buchwald–Hartwig 커플링이 아니라, 무수물로 아민을 아실화하는 반응이다. 따라서 두 수율 모델 모두 학습 반응군 밖이다. 13주차 절차에 따라 수율 예측을 실행하거나 해석하지 않았고, 두 결과 파일에서 `applicable_as_yield_prediction`을 false, 원본 출력값을 null로 기록했다.

- Yield-BERT: Buchwald–Hartwig FullCV_01 체크포인트 파일은 있으나 적용 불가.
- DRFP: Buchwald–Hartwig XGBoost 체크포인트는 있으나 적용 불가.

## Parrot 환경 주의

Parrot CPU 추론은 완료됐지만 `pip check`에는 rxnfp의 구형 고정 메타데이터(`scipy==1.4.1`, `scikit-learn==0.23.1`, `matplotlib==3.2.2`)와 현재 Apple Silicon 바이너리 버전 간 불일치가 남는다. 해당 패키지 API는 이번 추론에서 실제로 import/사용되어 결과 CSV가 생성됐다. `tokenizers 0.12.1`은 conda-forge의 Apple Silicon 빌드를 사용했다.
