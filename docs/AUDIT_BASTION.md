# Audit Bastion Runbook

## Purpose

The production audit panel stays behind private Cloud Run IAM.

For one-admin operational access we use a small bastion VM:
- machine type: `e2-micro`
- boot disk: `10 GB pd-standard`
- access path: `IAP TCP tunnel + OS Login`
- reverse proxy target: private Cloud Run `run.app`
- idle shutdown: `45 minutes`
- hard stop: daily at `23:30 UTC`

## Why the VM has an ephemeral public IP

The bastion still expects operators to connect through IAP only.

An ephemeral public egress IP is attached so the VM can reach:
- the private Cloud Run `run.app` URL
- Google Compute API for self-stop

This avoids adding Cloud NAT, which would materially increase the monthly fixed cost.
Inbound access still remains locked to TCP `22` from the IAP range.

## Start the bastion

The simplest operator flow is the local helper:

```bash
./scripts/bastion.sh
```

It prints the current bastion state and offers:
- `up` to start the VM if needed and open the IAP tunnel
- `down` to stop the VM

You can also call it directly:

```bash
./scripts/bastion.sh up
./scripts/bastion.sh down
```

Environment overrides are available when needed:
- `BASTION_INSTANCE_NAME`
- `BASTION_ZONE`
- `BASTION_LOCAL_PORT`
- `BASTION_REMOTE_PORT`

Manual `gcloud` commands remain valid as a fallback.

The VM is created in the stopped state. Start it before an audit session:

```bash
gcloud compute instances start openjobseu-audit-bastion \
  --zone=europe-north1-a
```

Wait until the VM status becomes `RUNNING`.

## Open the tunnel

Forward the local port `8888` to the bastion proxy:

```bash
gcloud compute ssh openjobseu-audit-bastion \
  --zone=europe-north1-a \
  --tunnel-through-iap \
  -- -L 8888:127.0.0.1:8888 -N
```

Then open:

```text
http://localhost:8888/internal/audit
```

The same tunnel also carries the audit JSON API used by the page.

## Stop behavior

The bastion stops automatically in two cases:
- no proxy activity for `45 minutes`
- nightly stop at `23:30 UTC`

You can still stop it manually after the session:

```bash
gcloud compute instances stop openjobseu-audit-bastion \
  --zone=europe-north1-a
```

## Troubleshooting

If the panel does not load:
- verify the VM is `RUNNING`
- verify the SSH tunnel command is still active
- check that `http://localhost:8888/internal/audit` responds locally
- inspect the bastion service logs:

```bash
gcloud compute ssh openjobseu-audit-bastion \
  --zone=europe-north1-a \
  --tunnel-through-iap \
  --command='sudo journalctl -u openjobseu-audit-bastion -n 100 --no-pager'
```

- inspect the idle-stop watchdog logs:

```bash
gcloud compute ssh openjobseu-audit-bastion \
  --zone=europe-north1-a \
  --tunnel-through-iap \
  --command='sudo journalctl -u openjobseu-audit-bastion-idle-stop.service -n 100 --no-pager'
```

If Cloud Run returns auth errors:
- confirm the bastion service account still has `roles/run.invoker`
- confirm the Cloud Run base URL did not change unexpectedly
- confirm the bastion startup script rendered the correct `CLOUD_RUN_BASE_URL`
