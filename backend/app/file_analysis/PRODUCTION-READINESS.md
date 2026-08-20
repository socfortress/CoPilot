# File Analysis — production readiness checklist

Status of the two-tier File Analysis feature (Tier 1 static inspection + Tier 2
CAPE detonation + multi-tenant gateway) against a real production launch.

Legend: ✅ done · 🟡 partial · ⬜ not started · 🔒 needs an infra/human decision

---

## 🔴 Hard blockers — before ANY production traffic

- ✅ **Tier-1 container isolation verified.** `inspector/verify_isolation.sh` passes
  **7/7** against `ghcr.io/socfortress/copilot-inspector:latest` (no network,
  read-only root, non-root uid 10001, all caps dropped, tmpfs writable, sentinel
  produces JSON, no leftover containers).
- 🟡 **Run the production container stack.** Isolation is proven, but the running
  environment is still the **dev host stack** with `INSPECTOR_MODE=service`
  (`hardened:false`, in-process). Production must run `INSPECTOR_MODE=container`
  with the docker-socket-proxy (`inspector-runner/docker-compose.fragment.yml`).
- ⬜ **Rebuild + deploy prod images from branch 974.** The published
  `ghcr.io/socfortress/*` backend/frontend images are **stale** (no File Analysis
  routes). CI must rebuild backend/frontend/inspector/inspector-runner from this
  branch and deploy. (wkhtmltopdf is already in the backend Dockerfile → PDF works.)
- ✅ **Code committed & pushed** to branch 974 (RAM-only handling, PDF report,
  Live-Session removal, Sandbox-Setup removal). `scheduler.py` intentionally excluded.
- 🔒 **Merge to main via PR + review.** Branch 974 is not merged.
- 🟡 **Gateway under version control.** Now a local git repo (`sandbox-gateway/`);
  ⬜ still needs a **remote** (private GitHub repo) so it survives box loss.

## 🟠 Before external (multi-tenant) clients

- 🔒 **Make the gateway reachable.** DNS `<gateway-domain> → <PUBLIC_IP>`, open
  `:443`/`:80` on the Hetzner firewall (currently VPN-only). Caddy auto-issues the
  cert on first request. See `sandbox-gateway/DEPLOY.md`.
- ⬜ **End-to-end test with a real second CoPilot** (not just unit tests + a status
  smoke test).
- ⬜ **Capacity / throughput.** One Windows guest, cold-boot per run → all clients
  serialize. Add guests / a fair queue before real multi-client load.
- ⬜ **Sample retention/purge policy.** Client samples persist in CAPE's binaries
  store indefinitely — define retention + deletion per data agreements.

## 🟡 Reliability & reproducibility

- ✅ **CAPE box runbook** — hand-applied host config documented in
  `sandbox-gateway/DEPLOY.md` (transient disk, egress block, INetSim, routing,
  cold-boot patch, gateway + Caddy). ⬜ Convert to IaC/scripts eventually.
- ⬜ **Monitor detonation latency.** A ~1h reporting stall was seen once; add
  alerting on report turnaround.
- ⬜ **Backups** for MinIO (results/previews) and the gateway SQLite.

## 🟢 Quality / validation

- 🟡 **Detection validation.** Verified on a real DarkGate sample (→ malicious via
  config extraction) + benign files. ⬜ The inert malicious-pattern **fixture
  battery** (true/false-positive regression) was postponed.
- ✅ **Test suites green** — backend file_analysis 30 passed / 1 skipped;
  gateway 10 passed; frontend `vue-tsc` clean.

## Follow-ups (non-blocking)

- ⬜ `customer_user` read-only scope (admin/analyst covered today).
- ⬜ Event 11 auto-trigger; Graylog `data_sandbox_*` detection rules + dashboard;
  AI analyst summary (copilot-mcp, display-only).
- ⬜ Optional: gVisor/Kata runtime for VM-grade Tier-1 isolation.

---

## Recommended path

1. Rebuild + deploy prod images from branch 974 with `INSPECTOR_MODE=container`;
   re-run `verify_isolation.sh` against the deployed image.
2. **Controlled single-tenant pilot on our own infra** — gated on the 🔴 items.
3. Give the gateway a remote; add DNS + firewall; e2e-test one real client.
4. Open to external clients after capacity + retention are addressed.
