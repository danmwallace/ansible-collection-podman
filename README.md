# Ansible Collection — danmwallace.podman

Roles for running homelab services on Fedora Server using [Podman](https://podman.io/) and
systemd Quadlets. Every service role drops a `.container` unit file into
`/etc/containers/systemd/` and lets systemd manage the container lifecycle — no Compose
daemon required. Services are wired together through a shared `proxy_network` Quadlet network
and exposed via a Traefik reverse proxy for TLS termination.

## Requirements

- Ansible >= 2.16
- Fedora Server (tested on Fedora 42+; Quadlet support requires Podman 4.4+)
- Collection dependencies (from `galaxy.yml`):
  - `containers.podman >= 1.11.0`
  - `ansible.posix >= 1.5.0`
  - `community.general >= 8.0.0`

## Installation

```bash
ansible-galaxy collection install danmwallace.podman
```

Or pin it in `requirements.yml`:

```yaml
collections:
  - name: danmwallace.podman
    version: ">=0.1.0"
```

## Roles

| Role | Description |
| --- | --- |
| [`danmwallace.podman.common`](roles/common/README.md) | Base Fedora Server configuration for Podman homelab hosts |
| [`danmwallace.podman.traefik`](roles/traefik/README.md) | Deploy Traefik reverse proxy as a Podman Quadlet on Fedora |
| [`danmwallace.podman.arcane`](roles/arcane/README.md) | Deploy Arcane container management UI and Postgres as Podman Quadlet units on Fedora |
| [`danmwallace.podman.it_tools`](roles/it_tools/README.md) | Deploy IT-Tools developer utility suite as a Podman Quadlet on Fedora |
| [`danmwallace.podman.librechat`](roles/librechat/README.md) | Deploy LibreChat and its dependencies as Podman Quadlet units on Fedora |
| [`danmwallace.podman.n8n`](roles/n8n/README.md) | Deploy n8n workflow automation and Postgres as Podman Quadlet units on Fedora |
| [`danmwallace.podman.semaphore`](roles/semaphore/README.md) | Deploy Semaphore Ansible UI with Postgres as Podman Quadlets on Fedora |

## Example Playbook

```yaml
- hosts: fedora_vms
  become: true
  roles:
    - danmwallace.podman.common
    - danmwallace.podman.traefik
    - role: danmwallace.podman.n8n
      vars:
        n8n_hostname: agents.example.com
        n8n_encryption_key: "{{ vault_n8n_encryption_key }}"
        n8n_postgres_password: "{{ vault_n8n_postgres_password }}"
```

## License

MIT
