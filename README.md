# 공개 Oncology 오믹스 데이터 모니터링 대시보드

공개 오믹스 데이터(특히 **공간전사체 / 공간단백체**, oncology 중심)의 **지형과 신규 유입을
현황만** 파악하기 위한 정적 대시보드입니다. 데이터를 받아 저장하지 않고 **메타데이터만**
수집해 테이블로 보여주며, 각 데이터셋은 원본 소스로 링크 아웃합니다.

**🔗 대시보드:** https://minsung1013.github.io/omics_data_dashboard/

## 목적
- 라이선스를 고려한 **모델 학습 사용 가능성(train-usability)** 판별
- 연구자·제약사의 **관심/수요 트렌드** 파악
- 매주 자동 갱신되는 **신규 데이터 모니터링**

## 수집 소스 (플러그인 구조)
| 소스 | 내용 | 라이선스 |
|---|---|---|
| **GEO** | NCBI GEO Series (oncology + spatial) | 미표기(open) |
| **Zenodo** | 논문 보충 데이터/코드 (명시적 라이선스) | CC-BY / 기타 |
| **CELLxGENE** | 큐레이션 sc/spatial (CZI) | CC-BY 4.0 |
| **HuBMAP** | CODEX/IMC/MERFISH/Xenium 등 **공간 단백체 포함** (primary dataset만) | CC-BY 4.0 |
| **ENA** | EBI ENA study-level (SRA 유럽 미러) | 미표기(open) |
| **GDC** | NCI GDC 프로젝트 (TCGA/CPTAC/TARGET 등 레퍼런스) | 혼합(open+controlled) |
| **figshare** | 논문 보충 데이터 (명시적 라이선스) | CC-BY / 기타 |
| **IDR** | Image Data Resource — 이미징/**공간 단백체**(IMC/CODEX/MIBI) | CC-BY 4.0 |
| **HTAN** | Human Tumor Atlas Network — atlas 단위(14) | CC-BY 4.0 |

`config.py`의 `SOURCES`에서 on/off 및 소스별 상한을 조정합니다.

> **HTAN**은 포털 매니페스트가 ~385MB라 매주 CI에선 기본 비활성(`enabled=False`)이며,
> 시드 시 1회만 수집합니다. `HTAN_MANIFEST`에 로컬 캐시 경로를 주면 재다운로드 없이 실행됩니다.
> **10x Genomics / SODB**는 공개 API가 없고(봇 차단/비공개 SPA) 안정적 수집이 어려워 보류했습니다.

## 중복 처리
- 소스별 고유 id로 1차 중복제거(동일 데이터셋 재수집 방지).
- 서로 다른 accession이지만 제목이 같은 레코드(ENA 재등록, GEO Super/SubSeries, 소스 간
  동일 연구 등)는 `possible_duplicate`로 **표시만** 하고 삭제하지 않음 → UI "중복 의심 숨기기"
  토글로 선택적으로 숨김.

## 라이선스 / 학습가능성 분류
원시 라이선스를 다음 `train_usability`로 매핑합니다 (`license.py`):
- `usable` — CC0 / 퍼블릭 도메인
- `attribution` — CC-BY (출처표기)
- `non_commercial` — CC-BY-NC (⚠ 상업적 학습 제외)
- `restricted` — controlled-access / consent 제한
- `unknown` — 미표기 (기본 사용 불가로 간주)

## 스코프
레코드는 **oncology 키워드** 또는 **공간(spatial) assay**에 해당할 때 유지됩니다
(공간 데이터는 비암이어도 포함). 키워드/플랫폼 매핑은 `config.py` 참고.

## 로컬 실행
```bash
pip install -r requirements.txt       # 또는: uv pip install -r requirements.txt
python harvest.py --since-days 540     # 초기 시드(넓은 기간)
python harvest.py                      # 이후 갱신(지난 실행 이후만)
cd docs && python -m http.server 8000  # http://localhost:8000
```
단일 소스 테스트: `python harvest.py --only GEO --cap 5 --self-test`

> macOS에서 사내망 TLS 가로채기로 `requests` 인증서 오류가 나면 시스템 CA를 지정:
> `export REQUESTS_CA_BUNDLE=$(security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > /tmp/ca.pem; security find-certificate -a -p /Library/Keychains/System.keychain >> /tmp/ca.pem; echo /tmp/ca.pem)`

## 자동 갱신
`.github/workflows/update.yml` 이 **매주 월요일 06:00 UTC**(및 수동 실행)에 `harvest.py`를
돌려 `docs/catalog.json`·`docs/meta.json`을 커밋 → GitHub Pages 자동 재배포.
(선택) 레포 시크릿 `NCBI_API_KEY` 설정 시 GEO rate limit 상향.

## 구조
```
config.py / license.py / tagging.py / util.py   # 스코프·분류·공통 유틸
sources/        # 소스별 어댑터 (base.py 인터페이스)
harvest.py      # 수집·병합·태깅 오케스트레이터
docs/           # GitHub Pages (index.html, app.js, style.css, catalog.json, meta.json)
```
