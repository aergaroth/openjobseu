locals {
  audit_bastion_name                 = "openjobseu-audit-bastion"
  audit_bastion_zone                 = "${var.region}-a"
  audit_bastion_port                 = 8888
  audit_bastion_idle_timeout_seconds = 2700
}

data "google_compute_image" "audit_bastion_image" {
  family  = "debian-12"
  project = "debian-cloud"
}

resource "google_service_account" "audit_bastion_sa" {
  account_id   = "audit-bastion"
  display_name = "Audit bastion runtime"
  description  = "Runs the audit bastion reverse proxy and self-stop watchdog."
}

resource "google_project_iam_custom_role" "audit_bastion_operator" {
  role_id     = "auditBastionOperator"
  title       = "Audit Bastion Operator"
  description = "Allows the single admin and scheduler to inspect, start, and stop the audit bastion instance."

  permissions = [
    "compute.instances.get",
    "compute.instances.list",
    "compute.instances.start",
    "compute.instances.stop",
    "compute.zoneOperations.get",
  ]

  depends_on = [
    google_project_iam_member.github_deploy_iam_role_admin,
  ]
}

resource "google_project_iam_custom_role" "audit_bastion_self_stop" {
  role_id     = "auditBastionSelfStop"
  title       = "Audit Bastion Self Stop"
  description = "Allows the bastion VM to stop itself after an idle timeout."

  permissions = [
    "compute.instances.get",
    "compute.instances.stop",
    "compute.zoneOperations.get",
  ]

  depends_on = [
    google_project_iam_member.github_deploy_iam_role_admin,
  ]
}

resource "google_project_iam_custom_role" "audit_bastion_firewall_admin" {
  role_id     = "auditBastionFirewallAdmin"
  title       = "Audit Bastion Firewall Admin"
  description = "Allows GitHub deploy automation to manage only the bastion firewall rule in the default network."

  permissions = [
    "compute.firewalls.create",
    "compute.firewalls.delete",
    "compute.firewalls.get",
    "compute.firewalls.list",
    "compute.firewalls.update",
    "compute.globalOperations.get",
    "compute.networks.get",
    "compute.networks.updatePolicy",
  ]

  depends_on = [
    google_project_iam_member.github_deploy_iam_role_admin,
  ]
}

resource "google_compute_firewall" "audit_bastion_iap_ssh" {
  name    = "openjobseu-audit-bastion-iap-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["audit-bastion"]

  depends_on = [
    google_project_iam_member.github_deploy_audit_bastion_firewall_admin,
  ]
}

resource "google_compute_instance" "audit_bastion" {
  name         = local.audit_bastion_name
  machine_type = "e2-micro"
  zone         = local.audit_bastion_zone
  tags         = ["audit-bastion"]

  desired_status = "TERMINATED"

  boot_disk {
    initialize_params {
      image = data.google_compute_image.audit_bastion_image.self_link
      size  = 10
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"

    # Keep an ephemeral egress IP to avoid the recurring cost of Cloud NAT.
    # Inbound access still stays limited to IAP SSH via firewall rules.
    access_config {}
  }

  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
    serial-port-enable     = "TRUE"
    bastion-port           = tostring(local.audit_bastion_port)
    bastion-idle-timeout   = tostring(local.audit_bastion_idle_timeout_seconds)
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -euo pipefail

    install -d -m 0755 /opt/openjobseu

    cat >/opt/openjobseu/bastion_proxy.py <<'PY'
    import json
    import os
    import socket
    import threading
    import time
    import urllib.error
    import urllib.parse
    import urllib.request
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


    CLOUD_RUN_BASE_URL = os.environ["CLOUD_RUN_BASE_URL"].rstrip("/")
    PROXY_HOST = "127.0.0.1"
    PROXY_PORT = int(os.environ.get("PROXY_PORT", "8888"))
    STATE_PATH = "/var/lib/openjobseu-audit-bastion/state.json"
    METADATA_HEADERS = {"Metadata-Flavor": "Google"}
    LOCK = threading.Lock()


    def ensure_state_dir():
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)


    def update_last_activity():
        ensure_state_dir()
        payload = {"last_activity": int(time.time())}
        tmp_path = f"{STATE_PATH}.tmp"
        with LOCK:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            os.replace(tmp_path, STATE_PATH)


    def fetch_identity_token():
        audience = urllib.parse.quote(CLOUD_RUN_BASE_URL, safe="")
        url = (
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            f"service-accounts/default/identity?audience={audience}&format=full"
        )
        request = urllib.request.Request(url, headers=METADATA_HEADERS)
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")


    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _proxy(self):
            update_last_activity()

            target_url = f"{CLOUD_RUN_BASE_URL}{self.path}"
            body = None
            if self.command in {"POST", "PUT", "PATCH"}:
                content_length = int(self.headers.get("Content-Length", "0") or "0")
                body = self.rfile.read(content_length) if content_length else None

            token = fetch_identity_token()
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"host", "authorization", "connection"}
            }
            headers["Authorization"] = f"Bearer {token}"

            request = urllib.request.Request(
                target_url,
                data=body,
                headers=headers,
                method=self.command,
            )

            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = response.read()
                    self.send_response(response.status)
                    for header, value in response.getheaders():
                        if header.lower() in {"connection", "transfer-encoding", "server", "date"}:
                            continue
                        self.send_header(header, value)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    if payload:
                        self.wfile.write(payload)
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                self.send_response(exc.code)
                for header, value in exc.headers.items():
                    if header.lower() in {"connection", "transfer-encoding", "server", "date"}:
                        continue
                    self.send_header(header, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
            except Exception as exc:
                payload = str(exc).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        def do_GET(self):
            self._proxy()

        def do_POST(self):
            self._proxy()

        def do_PUT(self):
            self._proxy()

        def do_PATCH(self):
            self._proxy()

        def do_DELETE(self):
            self._proxy()

        def log_message(self, fmt, *args):
            return


    def main():
        update_last_activity()
        server = ThreadingHTTPServer((PROXY_HOST, PROXY_PORT), ProxyHandler)
        server.serve_forever()


    if __name__ == "__main__":
        main()
    PY

    cat >/opt/openjobseu/idle_stop.py <<'PY'
    import json
    import os
    import time
    import urllib.error
    import urllib.request


    PROJECT_ID = os.environ["PROJECT_ID"]
    ZONE = os.environ["INSTANCE_ZONE"]
    INSTANCE_NAME = os.environ["INSTANCE_NAME"]
    STATE_PATH = "/var/lib/openjobseu-audit-bastion/state.json"
    IDLE_TIMEOUT_SECONDS = int(os.environ.get("IDLE_TIMEOUT_SECONDS", "2700"))
    METADATA_HEADERS = {"Metadata-Flavor": "Google"}


    def read_last_activity():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except FileNotFoundError:
            return int(time.time())
        return int(payload.get("last_activity", int(time.time())))


    def fetch_access_token():
        request = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers=METADATA_HEADERS,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["access_token"]


    def stop_self():
        token = fetch_access_token()
        url = (
            "https://compute.googleapis.com/compute/v1/projects/"
            f"{PROJECT_ID}/zones/{ZONE}/instances/{INSTANCE_NAME}/stop"
        )
        request = urllib.request.Request(
            url,
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, timeout=30):
            return


    def main():
        if int(time.time()) - read_last_activity() < IDLE_TIMEOUT_SECONDS:
            return

        try:
            stop_self()
        except urllib.error.HTTPError as exc:
            if exc.code not in {400, 409}:
                raise


    if __name__ == "__main__":
        main()
    PY

    cat >/etc/default/openjobseu-audit-bastion <<EOF
    CLOUD_RUN_BASE_URL=${local.run_uri}
    PROXY_PORT=${local.audit_bastion_port}
    PROJECT_ID=${var.project_id}
    INSTANCE_ZONE=${local.audit_bastion_zone}
    INSTANCE_NAME=${local.audit_bastion_name}
    IDLE_TIMEOUT_SECONDS=${local.audit_bastion_idle_timeout_seconds}
    EOF

    cat >/etc/systemd/system/openjobseu-audit-bastion.service <<'EOF'
    [Unit]
    Description=OpenJobsEU audit bastion reverse proxy
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    EnvironmentFile=/etc/default/openjobseu-audit-bastion
    ExecStart=/usr/bin/python3 /opt/openjobseu/bastion_proxy.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    EOF

    cat >/etc/systemd/system/openjobseu-audit-bastion-idle-stop.service <<'EOF'
    [Unit]
    Description=OpenJobsEU audit bastion idle stop watchdog
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=oneshot
    EnvironmentFile=/etc/default/openjobseu-audit-bastion
    ExecStart=/usr/bin/python3 /opt/openjobseu/idle_stop.py
    EOF

    cat >/etc/systemd/system/openjobseu-audit-bastion-idle-stop.timer <<'EOF'
    [Unit]
    Description=Run OpenJobsEU audit bastion idle stop watchdog every 5 minutes

    [Timer]
    OnBootSec=5m
    OnUnitActiveSec=5m
    Unit=openjobseu-audit-bastion-idle-stop.service

    [Install]
    WantedBy=timers.target
    EOF

    systemctl daemon-reload
    systemctl enable --now openjobseu-audit-bastion.service
    systemctl enable --now openjobseu-audit-bastion-idle-stop.timer
  EOT

  service_account {
    email  = google_service_account.audit_bastion_sa.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  scheduling {
    automatic_restart   = false
    on_host_maintenance = "MIGRATE"
    preemptible         = false
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  depends_on = [
    google_project_iam_member.github_deploy_instance_admin,
    google_project_iam_member.github_deploy_audit_bastion_user,
    google_compute_firewall.audit_bastion_iap_ssh,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "audit_bastion_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.this.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.audit_bastion_sa.email}"
}

resource "google_project_iam_member" "audit_bastion_self_stop" {
  project = var.project_id
  role    = google_project_iam_custom_role.audit_bastion_self_stop.name
  member  = "serviceAccount:${google_service_account.audit_bastion_sa.email}"
}

resource "google_project_iam_member" "audit_bastion_scheduler_operator" {
  project = var.project_id
  role    = google_project_iam_custom_role.audit_bastion_operator.name
  member  = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

resource "google_project_iam_member" "audit_bastion_admin_operator" {
  project = var.project_id
  role    = google_project_iam_custom_role.audit_bastion_operator.name
  member  = "user:${var.allowed_auth_email}"
}

resource "google_project_iam_member" "audit_bastion_admin_iap" {
  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = "user:${var.allowed_auth_email}"
}

resource "google_project_iam_member" "audit_bastion_admin_oslogin" {
  project = var.project_id
  role    = "roles/compute.osLogin"
  member  = "user:${var.allowed_auth_email}"
}

resource "google_cloud_scheduler_job" "audit_bastion_stop" {
  name             = "openjobseu-audit-bastion-stop"
  region           = var.scheduler_region
  schedule         = "30 23 * * *"
  time_zone        = "UTC"
  attempt_deadline = "30s"

  http_target {
    http_method = "POST"
    uri         = "https://compute.googleapis.com/compute/v1/projects/${var.project_id}/zones/${local.audit_bastion_zone}/instances/${local.audit_bastion_name}/stop"

    oauth_token {
      service_account_email = google_service_account.scheduler_sa.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}
