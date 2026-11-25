# ASKCOS context_recommender 실행 준비 요약

대상 저장소: `/Users/kdy20069/Downloads/Organic/skill/context_recommender`

## 필요한 런타임

저장소 README는 Docker 또는 Singularity를 요구합니다. 현재 Mac은 Apple Silicon (`arm64`)이고 `docker`와 `singularity` CLI가 설치되어 있지 않습니다. README에 따르면 컨테이너 이미지는 사전 pull하는 방식이 아니라 저장소의 Dockerfile로 로컬 빌드합니다. Docker Desktop 설치 문서는 [Docker 공식 Mac 설치 안내](https://docs.docker.com/desktop/setup/install/mac-install/)를 참고하세요. 설치 페이지에서 Apple silicon용 DMG를 선택해야 합니다. Docker Desktop은 Docker Engine, CLI, Buildx, Compose를 포함합니다.

## ASKCOS 조건 모델 가중치

저장소 스크립트 `scripts/download_trained_models.sh`는 다음 두 압축 파일을 받아 풉니다.

| 모델 | 다운로드 주소 | 예상 로컬 디렉터리 |
|---|---|---|
| v1 | [v1.tar.gz (Dropbox)](https://www.dropbox.com/scl/fi/97g21iqzxz4gw4l83xjye/v1.tar.gz?rlkey=orny64sno8kd3cbspgbs53qd0&dl=1) | `/Users/kdy20069/Downloads/Organic/skill/context_recommender/app/resources/models/context/v1/` |
| v2 | [v2.tar.gz (Dropbox)](https://www.dropbox.com/scl/fi/9wft0zbxt6xhd3i3myvfo/v2.tar.gz?rlkey=1ltg6ie1vxc2ookeliotuliaq&dl=1) | `/Users/kdy20069/Downloads/Organic/skill/context_recommender/app/resources/models/context/v2/` |

저장소가 제공하는 자동 다운로드 명령은 작업 디렉터리를 저장소 루트로 두고 `sh scripts/download_trained_models.sh`입니다. 두 다운로드가 끝나면 압축 파일을 스크립트가 지정한 `app/resources/models/context/`에 각각 풉니다.

## 빌드·서비스 순서

1. 저장소 루트에서 `docker build -f Dockerfile -t registry.gitlab.com/mlpds_mit/askcosv2/askcos2_core/context_recommender:1.0-cpu .`
2. `sh scripts/download_trained_models.sh`
3. 저장소 루트에서 `sh scripts/serve_cpu_in_docker.sh`
4. `curl http://127.0.0.1:9901/health` 응답이 `{"message":"Alive!"}`인지 확인
5. 조건 추천은 저장소 README에 나온 v2 endpoint (`POST /api/v2/condition/FP`)를 사용. 이 아세트아미노펜 단계 입력은 `CC(=O)OC(C)=O.Nc1ccc(O)cc1>>CC(=O)Nc1ccc(O)cc1`, 알려진 reagent 목록 `[]`, 후보 수 `3`임.

상태 확인일: 2026-11-24. 이 환경에는 런타임과 모델 파일이 아직 없어 이번 ASKCOS 예측은 실행되지 않았습니다.
