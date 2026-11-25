---
name: organic-final-project
description: Prepare a reproducible organic-synthesis final-project report from molecule inputs, six synthesis models, raw run records, and optional bonus analyses. Use for chemistry-course projects that need evidence-linked DOCX or PDF deliverables.
---

# Organic Synthesis Final Project

Use this skill to run and document a course project from target structure through final report. Treat repository outputs, raw responses, logs, and environment manifests as the evidence. The acetaminophen files under `runs/acetaminophen/` are a worked local example, not values to copy into a different project.

## Required workflow

### 1. Confirm inputs and create a run record

1. Confirm the target name, identifier, source structure file, and its isomeric/canonical SMILES. If an SDF is supplied, parse it with RDKit and record the canonical SMILES; do not infer identity from the filename alone.
2. Save a one-line `target.smi` and keep the source structure file or a source path/hash in the run manifest.
3. Create a target-specific directory. Use separate subdirectories for model runs, results, bonus analyses, and final reports. Never overwrite an earlier run; use a new run ID or output folder.
4. Record system architecture, Python/Conda or uv environment, package versions, model/checkpoint paths and hashes, exact commands, timestamps, and exit codes in `environment_status.json` and per-model logs. Do not record API keys or copy them into config, manifests, or logs.

Suggested layout:

```text
runs/<target-id>/
  target.smi
  input/                       # source SDF and provenance, when available
  aizynthfinder/               # routes.json, stats.json, manifest, config, log
  synthex/                     # manifest, strategies.json, routes.json if produced, logs
  results/
    route_reactions.json
    askcos_raw.json
    parrot_raw.csv
    yieldbert_route_results.json
    drfp_route_results.json
    environment_status.json
    REPORT.md
  bonus/                       # EPI Suite, MOPAC, 2D/3D structures and analysis
  report/                      # final DOCX/PDF, maximum 20 pages
```

### 2. Run route, condition, and yield models

Run route planners first. Select a route based on the actual saved output, then convert its individual steps into forward reaction SMILES for the condition and yield models. Preserve the model's original reaction direction and any target-only product convention. If you add stoichiometric byproducts for explanation, keep that balanced equation separate from the exact model input.

For each attempted model, retain its original output and execution log. Mark the result `success`, `partial`, `failed`, or `not_run`/`out_of_domain`; include the exact stopping stage and error. For yield models, determine whether the reaction belongs to the checkpoint's training reaction family before inference. If not, record `applicable_as_yield_prediction: false`, `raw_model_output_percent: null`, and the reason. Never invent a prediction to fill a table.

### 3. Read raw records and write the result summary

Read raw JSON/CSV, route manifests, model configuration, and logs directly. In `REPORT.md`, distinguish raw model fields from translated names, rounded values, chemistry interpretation, and derived unit conversions. For example, ASKCOS temperature conversion is `°C = K - 273.15`; keep original Kelvin and score in the raw file. Model scores are not yields or calibrated probabilities unless the source explicitly defines them that way.

### 4. Link every conclusion to evidence

For each reported route, condition, yield, temperature, model version, and failure, identify the supporting file and (for online references) a direct source URL. Keep raw response files unmodified. A transformed table is a summary, not a replacement for the raw response. Keep distinction between experiment, model estimate, model output, chemical interpretation, and missing data.

### 5. Prepare bonus analyses

- **Condition compatibility:** Check whether recommended components react with each other or consume a reactant. State a chemical conflict and why; distinguish a strong incompatibility from a caution or missing condition.
- **EPI Suite:** Query by CAS through `episuite.dev` or its API and save the actual JSON response. Select explicit `EXPERIMENTAL` values ahead of `ESTIMATED`; preserve other API classes such as `EVIDENCE` as labeled and do not silently call them experimental. If a query fails, report the failure without substituting another site's number. Compare the selected melting/boiling values with the ASKCOS temperature and state how phase was inferred.
- **MOPAC:** Follow the course 13th-week section 4.3. Prepare a 3D geometry, run `CHARGES` first, check the charge result, then run `PM6 pKa CHARGE=0` for O–H hydrogens only when the neutral structure check is clean. Save `.mop` and `.out` for both jobs, pKa atom number/value, exit code, and the exact `JOB ENDED NORMALLY` status. Label pKa as a calculation, not an experimental measurement.
- **3D accessibility:** A 3D SDF alone is only a structure input. Report approach-direction/CPK accessibility as performed only if actual view images or measurements exist. Otherwise write “not performed” and do not infer accessibility from the file's presence.
- **CPK 캡처 보고:** 학교 Windows PC의 Discovery Studio Visualizer 등 실제 도구에서 CPK 공간 채움 모형을 캡처한 이미지가 있으면, 보고서의 3D 접근성 항목에 실제 파일만 삽입한다. 이미지 파일 존재 여부는 렌더링 스크립트에서 확인하고, 존재하지 않는 이미지는 삽입하지 않는다. 원자 거리(Å), 주변 원자 개수, 반응 중심 원자의 정확한 좌표나 선택 반경 등은 실제 측정·캡처 파일에 기록된 값이 아니면 임의로 지어내지 않는다. 반응 중심을 강조한 표시(예: 특정 원자 색 변경)가 캡처 이미지에 드러나 있으면 그 시각적 노출 여부만 기술할 수 있고, 정량적 판단이나 미확인 거리·개수·서식을 만들어 넣지 않는다.

### 6. Write and verify the final report

Final reports are generated only from raw run records — not from reproduced or estimated values. When rewriting the Markdown source for the final render, keep every number, failure message, and applicability decision tied to the actual run files listed in this skill and in the run manifest. Do not normalize away failure details, model score semantics, or applicability decisions to make the report look cleaner.

Save the final file under `report/` as DOCX or PDF, no more than 20 pages. Include:

- A short executive summary of 3–4 sentences directly before Chapter 1 (`## 요약`), placed immediately after the metadata block and before the first content section. The summary must reflect only the actual run record: which models ran, which failed, which were out of domain, and the key numeric findings. Do not add new numbers or reinterpret failures in the summary.
- Why the molecule was selected.
- The chosen synthesis route and each step's forward reaction, condition candidates, yield result or applicability decision, and an integrated conclusion.
- Model performance and limitations, including exact failures, component conflicts, out-of-domain yield models, and relevant runtime/build issues evidenced by logs.
- RDKit 2D structure images for target and key intermediates/reactants, plus a 2D forward-reaction scheme embedded in the report.
- Bonus sections for EPI Suite phase comparison, MOPAC charge/pKa calculations, and 3D accessibility; mark an analysis not performed when its result is absent.
- Chapter 10 (재현성 정보) must include a single “사용한 모델과 저장소” summary table with exactly five columns: `역할 | 모델 | 저장소 | 버전·설정 | 실행`. Each row must state the model role, model name, official repository URL (no local or personal paths), version/checkpoint/configuration, and execution status (실행/실행(실패)/적용 불가(미실행) 등). The header pipe count and separator pipe count must match exactly (for 5 columns, `|---|---|---|---|---|`). This table replaces any long free-form list of the same information in Chapter 10.

Use the repository’s single CLI rendering script for final deliverables. The canonical script is `scripts/export_report_local.py`; keep `scripts/export_report.sh` and any duplicated `render_report.py`/`build_pdf.py` copies out of the active pipeline. The CLI form is:

```
python3 scripts/export_report_local.py SOURCE.md DEST.pdf [DEST.docx]
```

- SOURCE.md is the Markdown source on disk; DEST.pdf is the required PDF; optional DEST.docx is created when provided.
- The script accepts only CLI arguments; do not hardcode personal paths like `/Users/<user>/...` in the script or in reports. Image, font, and model asset paths are resolved relative to the Markdown source directory or through the run manifest.
- When pandoc is available, the script builds DOCX with pandoc and converts to PDF with LibreOffice (soffice/libreoffice). When pandoc is absent, it builds DOCX directly with python-docx. When neither LibreOffice nor pandoc is available, it renders PDF directly with ReportLab.
- 한글 PDF 렌더링은 스크립트 실행 시 실제 시스템에 존재하는 한글 지원 TTF/TTC를 자동 탐색해 등록한다(예: macOS의 AppleSDGothicNeo/AppleGothic/NanumGothic 등). 반지름이 같은 폰트 묶음(ttc)은 스크립트에서 지원되는 첫 글리프를 사용한다. 렌더링 후에도 한글 깨짐(■ 등)이 없어야 하며, PDF 텍스트 추출 시 마크다운 원문과 대응되는 한글이 확인되어야 한다.
- 표 처리 규칙:
  - 헤더 열 수와 구분선 열 수를 정확히 일치시킨다. 예시: 헤더가 2열이면 `|---|---|`, 헤더가 5열이면 `|---|---|---|---|---|` 또는 값 정렬용 `|---:|---|---|---|---|` 등으로 열 수를 맞춘다.
  - 구분선 행(`|---:`, `|---`, `|----` 등)은 표 본문 셀 내용으로 나타나지 않아야 한다. 파싱 시 구분선 행은 열 수 확인용으로만 쓰고 표 셀 데이터에서 제외한다.
  - `**굵게**`는 마크다운 굵게 기호로 남기지 말고 본문·표에서 일반 텍스트로 변환한다. `` `코드` ``도 인라인 코드 표시에서 해제해 원본 문자열만 남긴다.
  - `<`, `>`, `&`는 XML/HTML 컨텍스트에서 사용할 때 반드시 이스케이프를 적용한다.
- 이미지 경로 규칙:
  - 최종 보고서의 Markdown 소스가 `report/` 디렉터리에 있고, 이미지 원본은 `runs/<target-id>/bonus/` 또는 해당 프로젝트 공통 `bonus/`에 있을 때, Markdown 소스 기준 상대 경로로 이미지를 지정한다. 예를 들어 보고서가 `report/report.md`이고 이미지가 `runs/acetaminophen/bonus/forward_reaction_scheme.png`에 있으면, Markdown에서는 `../runs/acetaminophen/bonus/forward_reaction_scheme.png`로 참조한다.
  - CPK·막대 모형 등 3D 뷰 캡처 이미지가 `bonus/`에 실제 존재할 때만 삽입하고, 없을 때는 “수행하지 않음”으로 처리한다. 보고서 원문(`.md`)에는 존재하지 않는 이미지 경로를 넣지 않는다.
- 이미지 삽입 전, 렌더링 스크립트는 실제 파일 존재 여부를 확인하고 존재하지 않으면 `[이미지 없음]` 대신 실패 플래그/로깅으로 보고한다. 표·본문·이미지가 모두 정상 삽입되지 않은 파일은 제출본으로 사용하지 않는다.
- 오타/표현 규칙: 보고서 원문을 재생성할 때 `에틸 아세틸레이트`와 같은 비표준 용어 대신 표준 명칭(`에틸 아세테이트` 등)을 사용한다. `조건 모델_input으로`, `성향 검토`처럼 언더스코어·번역체가 섞인 표기는 원문에 쓰지 않는다.
- 페이지 제한: 최종 파일은 DOCX 또는 PDF로 `report/` 아래에 저장하고, 최대 20쪽 이내여야 한다. 생성 후 텍스트 추출 및 렌더링 미리보기로 ① 한글 깨짐 없음, ② `[이미지 없음]` 문구 없음(이미지 4장 삽입 확인), ③ 표 구분선 노출 없음, ④ 20쪽 이내 여부를 확인한다.

렌더링 후에는 스크립트 출력만 믿지 말고, 실제 텍스트 추출과 렌더링 이미지로 위 네 가지를 직접 확인한다.

## Model references and project-specific operating notes

### A. Retrosynthesis: AiZynthFinder

- Repository: [MolecularAI/aizynthfinder](https://github.com/MolecularAI/aizynthfinder)
- **Input:** target `.smi` file or SMILES string; YAML config points to expansion policy, optional filter policy, and stock files.
- **Run:** with the installed environment and local config/assets, follow the repository CLI pattern. The verified acetaminophen command was `aizynthcli --config config-course.yml --smiles target.smi --policy uspto --filter uspto --stocks zinc --output routes.json`.
- **Outputs:** preserve `routes.json`, `stats.json`, `config-course.yml`, `manifest.json`, asset manifest/checksums, and `run.log`. In the local run, 23 routes were solved and the top one-step disconnection used acetic anhydride plus p-aminophenol; the run reported ZINC stock membership, not experimental availability or feasibility.
- **Interpretation:** this is retrosynthesis. Convert the selected route node to forward reaction SMILES explicitly and record any direction reversal. A purchasable-stock flag is not evidence that the reaction works.

### B. Retrosynthesis: SynthEx (submission branch)

- Repository: [schwallergroup/synthex/tree/submission](https://github.com/schwallergroup/synthex/tree/submission)
- **Input:** target SMILES, target ID, manuscript config, and an LLM provider. The local Solar Pro 4 profile used Upstage's OpenAI-compatible service; keep `UPSTAGE_API_KEY` in the process environment/secret store only. The repository's standard setup uses uv and Python 3.11; the manuscript workflow and external credentials/assets are described in `instructions.md`.
- **Run:** `uv sync --python 3.11 --frozen --extra manuscript`, then `uv run --env-file .env synthex plan '<TARGET_SMILES>' --target-id <ID> --config <SOLAR_PRO4_CONFIG> --output <NEW_RUN_DIR>`. Validate config and external assets before a live model call. Use a fresh output directory; a directory with an existing `manifest.json` is not a new run.
- **Outputs:** keep `manifest.json`, `strategies.json`, `routes.json` if generated, stage logs, and config. The acetaminophen run created strategies but no route: `execution2.log` records `Route Builder exhausted 2 proposals for step 2`, `break_bond` on maps 2 and 8, and `no bond exists between atoms 1 and 7` (exit code 2). Its first offline attempt also logged DNS failure. Report these as failed stages; do not show a synthesized route.
- **Interpretation:** LLM strategy/route proposals and internal Critic/Editor agreement are not laboratory validation. Preserve generated steps and validation failures.

### C. Conditions: ASKCOS context_recommender

- Repository: [mlpds_mit/askcosv2/context_recommender](https://gitlab.com/mlpds_mit/askcosv2/context_recommender)
- **Input:** forward reaction SMILES, known `reagents` list, and `n_conditions`; v2 FP accepts JSON at `POST /api/v2/condition/FP`. Example acetaminophen input: `{"smiles":"CC(=O)OC(C)=O.Nc1ccc(O)cc1>>CC(=O)Nc1ccc(O)cc1","reagents":[],"n_conditions":3}`.
- **Run:** README workflow builds the CPU image locally from `Dockerfile` (or Singularity definition), downloads trained models via `sh scripts/download_trained_models.sh`, starts the service with `sh scripts/serve_cpu_in_docker.sh`, checks `/health`, then calls the endpoint. Save the original response JSON. Stop the container after inference when requested or when finished.
- **Outputs:** retain downloaded archive/model path, image tag/build log, health response, request payload, `askcos_raw.json`, and summarized candidates in `REPORT.md`. Include candidate components/roles/amounts, Kelvin and converted Celsius, and score.
- **Interpretation/limits:** predicted agents can be chemically incompatible; evaluate component-component conflicts. A score is not a yield or probability. In the verified Apple Silicon run, the stock Dockerfile failed because `tensorflow-cpu==2.7.4` had no Linux/aarch64 wheel. A local workaround replaced it with `tensorflow-aarch64==2.7.4` and added conda-forge `h5py=3.11`; inference then succeeded, with a SciPy/NumPy version warning. Treat this as a tested local workaround, not an upstream-supported build. The local run returned top-2 water with acetic anhydride, a hydrolysis conflict.

### D. Conditions: Parrot

- Repository: [wangxr0526/Parrot](https://github.com/wangxr0526/Parrot)
- **Input:** one forward reaction SMILES per line in a text file; inference YAML selects the checkpoint and dataset condition-label mapping. The verified config was `configs/config_inference_use_uspto.yaml` and checkpoint directory `outputs/Parrot_train_in_USPTO_Condition_enhance`.
- **Run:** create/use the repository's compatible Python/PyTorch environment and required checkpoint/label-map assets, then run from repository root: `python inference.py --config_path configs/config_inference_use_uspto.yaml --input_path <INPUT.txt> --output_path <OUTPUT.csv> --num_workers 1 --inference_batch_size 8 --gpu -1`. The verified local CPU environment was `parrot-cpu` with Python 3.9.23, PyTorch 1.13.1, RDKit 2025.03.5, Transformers 4.18.0, SimpleTransformers 0.63.6, and rxnfp 0.1.0.
- **Outputs:** preserve input text, full CSV (15 candidates in the local run), config/checkpoint provenance, and stdout/stderr log. The project run stored `parrot_input.txt`, `parrot_raw.csv`, and `parrot_execution.log`.
- **Interpretation/limits:** the verified USPTO config has `use_temperature: false`; Parrot does not predict temperature. Its beam-search score is not a yield/probability. Check for reactions between solvents/reagents and the route reactants. Local inference succeeded despite `pip check` legacy rxnfp version warnings; report that limitation rather than hiding it.

### E. Yield: Yield-BERT / rxn_yields

- Repository: [rxn4chemistry/rxn_yields](https://github.com/rxn4chemistry/rxn_yields)
- **Input:** forward reaction SMILES as text with `reactants>>products`; this is a regression model, not a route planner. The repository's README describes legacy Python 3.6, RDKit 2020.03.3 and tmap setup; use a compatible isolated environment and the intended checkpoint.
- **Run:** the repository exposes its SimpleTransformers model API; its training/evaluation examples load `SmilesClassificationModel("bert", checkpoint, num_labels=1, use_cuda=False)` and call `.predict([reaction_smiles])`. Keep the chosen checkpoint/split and prediction output with the run record. The local Buchwald–Hartwig checkpoint was `trained_models/buchwald_hartwig/FullCV_01_split_2768/checkpoint-1730-epoch-10`.
- **Outputs:** store raw prediction and applicability decision in `yieldbert_route_results.json`; include reaction SMILES, checkpoint, domain assessment, and raw percent or `null` if not run.
- **Interpretation/limits:** the bundled checkpoints represent specific reaction families/datasets. The acetaminophen anhydride acetylation has no aryl halide, Pd, or Buchwald–Hartwig coupling, so local protocol correctly marked it out of domain and did not predict a yield. Do not report a fabricated percentage.

### F. Yield: DRFP + regression

- Repository: [reymond-group/drfp](https://github.com/reymond-group/drfp)
- **Input:** forward reaction SMILES. The library encodes the difference between reactant and product molecular n-grams; the repository CLI accepts a file of reaction SMILES (`drfp reactions.txt fingerprints.pkl -d 2048`).
- **Run:** install the repository/package environment, create fingerprints with the same settings as the trained model (`2048` bits, radius `3`, rings enabled for the local Buchwald–Hartwig feature set), then load the matching XGBoost model. Local assets were `models/buchwald-hartwig-xgb-model.json` and `models/model_data/FullCV_01-2048-3-true.pkl` plus its map. Only predict if the reaction is within the documented training family and preprocessing matches.
- **Outputs:** retain the fingerprint/settings, exact model path/version, raw regression output, and decision in `drfp_route_results.json`.
- **Interpretation/limits:** DRFP itself is a fingerprint generator; a yield value requires a separately trained regression model. The local bundled model is Buchwald–Hartwig-specific. The acetaminophen acetylation was marked out of domain and not run. Do not treat a fingerprint alone as a yield prediction.

## Verified acetaminophen record: use as an example of evidence handling

The local run demonstrates the needed distinctions:

- AiZynthFinder: `is_solved=true`, 23 solved routes, one-step top route; see `runs/acetaminophen/aizynthfinder/manifest.json`, `routes.json`, `stats.json`, and `run.log`.
- SynthEx: Solar Pro 4 strategy stage ran, route construction failed; see `runs/acetaminophen/synthex/run2/manifest.json` and `execution2.log`.
- ASKCOS: v2 FP inference succeeded after the Apple Silicon build workaround; full raw response is `runs/acetaminophen/results/askcos_raw.json` and environment/build details are in `environment_status.json`.
- Parrot: CPU inference succeeded; original full candidate CSV and execution log are in `results/parrot_raw.csv` and `parrot_execution.log`.
- Yield-BERT and DRFP: both were not run because acetaminophen formation is outside the bundled Buchwald–Hartwig C–N coupling domain; route result JSONs retain false applicability and null raw prediction.
- Bonus files include EPI Suite API JSON, MOPAC `.mop`/`.out`, and 3D SDFs. They do not by themselves establish a measured reaction outcome or a completed CPK accessibility analysis.
