# Goal

This repository provides high-accuracy, two-tier PDF parsing (fast and accurate modes) built on MinerU and vLLM. The goal of this project is to be an open-source, reproducible, production-ready parser that delivers the highest practical accuracy while remaining maintainable, portable, and secure for downstream users.

This document lists recommended improvements, prioritized actions, exact files and commands to change, rationale, validation steps, and rollout guidance so maintainers can bring the repo to production-grade quality.

---

## Executive summary (high level)

- Keep the current baked-model option available for minimal cold-start latency, but make it explicit and controlled (separate `Dockerfile.prod` / build flag). Do not bake models accidentally into dev images.
- Enforce reproducibility and stability by pinning base images, pip packages, and MinerU releases. Produce a lockfile and provide pinned install commands.
- Harden Docker images: use multi-stage builds, non-root runtime user, and `.dockerignore` (already added).
- Keep GPU config modern (`device_requests`) and document compatible Docker/Toolkit versions.
- Add deterministic CI (build + smoke integration test) that verifies parsing correctness on a tiny sample PDF.
- Provide model provenance: HF repo names, revisions, and checksums used to produce high-accuracy results.

---

## Prioritized action list (what to do first)

1. Add `Dockerfile.prod` (multi-stage) and switch production builds to use pinned `mineru` wheel or pinned package version. Keep `Dockerfile.dev` for `pip install -e` editable installs.
2. Produce a `pyproject.lock` / `requirements.lock` or pinned `requirements.txt`. Commit the lockfile to the repo.
3. Add GitHub Actions CI workflow that:
   - Installs pinned dependencies
   - Runs unit tests
   - Builds `Dockerfile.prod` with `--no-cache` (optionally with baked models in a build arg) and runs a smoke-test parsing a small PDF; checks output contains expected tokens/metadata
4. Add `deploy/seed-hf-volume.sh` and `deploy/seed-job.yaml` (K8s) or `deploy/seed-compose.sh` to populate the `huggingface-cache` volume (documented). Keep baked-image option available as `BUILD_MODE=prefill` if required.
5. Add documentation `docs/DEPLOYMENT.md` that outlines exact steps for: GPU setup, prefill, pinning images, and release workflow (including how to pre-bake images with models and publish to a registry).
6. Add smoke-test sample PDF and a reproducible test runner for CI to use (small, permissively licensed sample).

---

## Detailed changes and why (with code and file targets)

### 1) Docker and image hygiene

- Files to add/modify:
  - `deploy/Dockerfile.prod` (new) — multi-stage, install pinned `mineru==<tag>`, optional build-arg `PREFILL_MODE=true|false`.
  - `deploy/Dockerfile.dev` (or keep `deploy/Dockerfile.accurate` for dev) — keep editable `pip install -e` for contributors.
  - `deploy/docker-compose.yml` — already updated to `device_requests`, add optional `build.args` to select `BASE_IMAGE` or `PREFILL_MODE`.

- Why:
  - Multi-stage builds keep runtime images small and remove build dependencies.
  - Production images should be deterministic (pin base images & packages) to ensure reproducible, high-accuracy results.

- Example `Dockerfile.prod` snippet (skeleton):

```dockerfile
ARG BASE_IMAGE="vllm/vllm-openai:v0.10.2"
FROM ${BASE_IMAGE} as base
# (install apt deps, etc.)

FROM base as builder
COPY pyproject.toml /app/
# install build deps and wheel, build wheel for MinerU and our package
RUN python3 -m pip wheel -w /wheels .

FROM ${BASE_IMAGE}
COPY --from=builder /wheels /wheels
RUN python3 -m pip install /wheels/* --no-index
# copy entrypoint and runtime files
COPY deploy/entrypoint-accurate.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

- How to build (example, pinning base image digest recommended):

```powershell
# build with pinned base (replace <digest> with actual sha256)
docker build --build-arg BASE_IMAGE='vllm/vllm-openai@sha256:<digest>' -f deploy/Dockerfile.prod -t two_tier/accurate:prod .
```


### 2) MinerU & dependency reproducibility

- Files to update:
  - `pyproject.toml` or `requirements.txt` — pin exact versions for all external packages (transformers, torch, vllm, mineru if from PyPI)
  - Add `requirements.lock` or `poetry.lock` / `pipfile.lock` depending on package manager.

- Why:
  - MinerU internals changed across versions (we saw module and signature mismatches). Pinning prevents runtime surprises and ensures the same model/processing code is used for accuracy.

- Actionable step:
  - Decide on a MinerU release (e.g., `mineru==X.Y.Z`) and update Dockerfile to `pip install mineru==X.Y.Z`. Alternatively, build and install a local wheel from the checked-out submodule in CI and tag that wheel.

- If you must keep the submodule editable for development, do so only in `Dockerfile.dev` and explicitly exclude that in `Dockerfile.prod`.


### 3) Model management and provenance

- Maintain a model registry file `models/MODELS_USED.yaml` that contains:
  - model id (huggingface repo name), revision (tag/sha), file names used, and sha256 checksum of the model file(s)

Example `models/MODELS_USED.yaml`:

```yaml
- name: Qwen-2.0
  hf_id: "Qwen/Qwen-2.0"
  revision: "v1.2.3"
  files:
    - name: model.safetensors
      sha256: "<sha256>"
- name: TableMaster
  hf_id: "table-master/tm-v1"
  revision: "main"
  files:
    - name: tm.bin
      sha256: "<sha256>"
```

- Why:
  - For high-accuracy results, model weights and revisions must be auditable and reproducible. Users can download the same artifacts and reproduce results or verify regression.

- Commands for verifying checksums after download (example):

```powershell
python - <<'PY'
import hashlib, sys
f = 'path/to/model.safetensors'
h = hashlib.sha256(open(f,'rb').read()).hexdigest()
print(h)
PY
```


### 4) GPU & runtime configuration

- `deploy/docker-compose.yml` already changed to use `device_requests`. Add documentation about minimal required host setup:
  - Docker Engine >= 20.10
  - NVIDIA Container Toolkit installed (link to NVIDIA docs)
  - `nvidia-docker2` / proper `nvidia-container-runtime` configuration if required by host

- Validate GPU availability during startup (health check): the `startup_event` already writes device-mode and logs GPU detection — extend to attempt loading a small model artifact to ensure device compatibility if GPU is requested.


### 5) CI: build + smoke-test

- Add `.github/workflows/ci.yml` with these steps:
  - Checkout
  - Cache pip dependencies (based on `requirements.lock`)
  - Run unit tests (`pytest -q`) — the repo already has tests in `tests/`.
  - Build `Dockerfile.prod` with build-arg to use CPU base image variant (or `--build-arg PREFILL=false`) and `--no-cache`.
  - Run container and POST a small sample PDF to `/parse` and assert JSON response shape (contains `metadata.pages` and non-empty `markdown`). Fail on mismatch.

- Why:
  - Continuous validation ensures the code and pinned dependencies produce expected outputs and guards against accidental regressions that reduce accuracy.

- Example smoke-test snippet (bash):

```bash
CONTAINER=$(docker run -d -p 8005:8005 two_tier/accurate:prod)
# wait for health
sleep 8
# POST sample.pdf
RESP=$(curl -s -F "file=@tests/fixtures/sample.pdf" http://localhost:8005/parse)
if echo "$RESP" | jq -e '.metadata.pages > 0 and (.markdown | length > 10)' >/dev/null; then
  echo "smoke ok"
else
  echo "smoke failed: $RESP"; exit 1
fi
docker rm -f $CONTAINER
```


### 6) Tests and sample data

- Add a tiny permissively-licensed PDF in `tests/fixtures/sample.pdf` for CI smoke tests.
- Expand unit tests around the wrapper code to assert that `parse_pdf` returns the required keys even when the MinerU backend switches between vLM and pipeline (eg: simulate pipeline by monkeypatching mineru calls).


### 7) Observability & logging

- Ensure structured logging includes a correlation ID for requests and that large traces are stored in logs for debugging (avoid leaking model secrets).
- Extend health check to include: models loadable and a tiny parse function succeeds (smoke check) — useful for readiness probes.


### 8) Security & secrets

- Never bake `HF_TOKEN` into images. Use runtime secrets (Kubernetes secret / compose env-file excluded from repo / CI secrets).
- Document the exact scope of the HF token (read-only recommended) and where to place it in `docker-compose.yml` or `k8s` manifests.


### 9) Documentation and Release

- Add `docs/DEPLOYMENT.md` describing two production workflows:
  - `prefill` image: pre-bake models into image for lowest latency (publish image to registry). Steps: build with `PREFILL=true`, push to registry.
  - `seeded-volume` image: small image plus separate volume prefill process (preferred for maintainability). Steps: run `deploy/seed-hf-volume.sh` to populate named volume or `kubectl job` to populate PVC.

- Add `IMPROVEMENTS.md` (this file) and `RELEASE.md` with exact build+push steps, including pinned digests.


## Validation and acceptance tests (how to confirm the changes maintain or increase accuracy)

1. Local regression test:
   - Build `Dockerfile.prod` with pinned mineru and pinned base image.
   - Run the container and POST `tests/fixtures/sample.pdf`.
   - Compare `markdown` output to a golden-file (for high-accuracy features you can permit fuzzy text comparison or token subset checks).

2. CI smoke test as described above. CI must fail if expected keys are absent or pages=0 or `markdown` is shorter than a threshold.

3. For numeric accuracy checks (optional): add a small suite of documents and calculate F1/precision metrics between parsed structures and human-labeled golden data. This is heavier but appropriate for a project prioritizing accuracy.


## Rollout plan (recommended)

1. Add `Dockerfile.prod` and `Dockerfile.dev`. Keep current `deploy/Dockerfile.accurate` as `Dockerfile.dev` or rename it.
2. Add `models/MODELS_USED.yaml`, `tests/fixtures/sample.pdf`, `deploy/seed-*.sh` and `deploy/seed-job.yaml`.
3. Add `pyproject.lock` or pinned requirements and update `deploy/Dockerfile.prod` to use the lockfile during build.
4. Add GitHub Actions `ci.yml` with the smoke tests.
5. Run CI and iterate on any failures.
6. Once green, tag a release, build a pinned image with digests, and push to registry. Publish release notes listing model provenance and pinned dependency versions.

---

## Estimated effort and priority (very approximate)

- High priority (0-2 days):
  - Add `Dockerfile.prod` multi-stage, pin MinerU, pin base image (small code edits). Add `models/MODELS_USED.yaml`.
  - Add `.github/workflows/ci.yml` basic smoke test (may require some CI time to debug).

- Medium priority (2-5 days):
  - Add seed scripts, docs for deployment, and small unit/integration tests.
  - Add model checksum verification and automation for seeding.

- Low priority (5-10 days):
  - Add heavy metric-based accuracy tests across multiple documents (requires labeled ground truth and tooling).
  - Add dedicated model service support (vLLM service) and advanced operational tooling.

---

## Immediate next steps (concrete)

1. Decide how you want to manage MinerU: (A) keep local submodule for development and publish a pinned PyPI release for production, or (B) build a wheel in CI from the submodule and install that wheel in `Dockerfile.prod`.
2. I can implement Option (1) quickly: create `Dockerfile.prod` and update `deploy/*` docs, plus add a minimal GH Actions workflow that builds and smoke-tests the image.

If you want me to start, choose one of the following immediate tasks and I will scaffold the files and push them in this repo:
- Task A: Create `deploy/Dockerfile.prod`, `deploy/seed-compose.sh`, and a minimal `docs/DEPLOYMENT.md`.
- Task B: Add `models/MODELS_USED.yaml`, `tests/fixtures/sample.pdf` (smoke file), and a GitHub Actions `ci.yml` that runs unit tests and the smoke parse test.
- Task C: Replace editable `pip install -e` with pinned wheel install in `deploy/Dockerfile.accurate` and add `Dockerfile.dev` that keeps editable installs for contributors.

Tell me which task to start with and I'll add a short TODO plan and implement it.