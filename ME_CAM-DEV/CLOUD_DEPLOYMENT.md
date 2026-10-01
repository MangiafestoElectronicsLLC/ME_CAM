# ME_CAM Cloud Dashboard Deployment

The cloud dashboard is a separate process from the Pi camera agent. It stores account/device metadata in SQLite and uploaded events under `MECAM_DATA_DIR`; that directory must be on persistent storage. Event video is encrypted at rest with `MECAM_STORAGE_KEY`. Live frames and two-way audio buffers are transient in-memory data, not recordings.

## Standalone Windows App (No Replit)

From PowerShell in `ME_CAM-DEV`, start a private local dashboard:

```powershell
.\run_mecam.ps1
```

Open `http://127.0.0.1:8081`. On first start the launcher prints an owner setup key; enter it on the setup page, then create the owner account. The database, encrypted events, session secret, media key, and setup key remain in `ME_CAM-DEV/cloud_data` across restarts. Back up this directory securely; losing `.media-secret` makes stored clips unrecoverable.

For cameras on the same trusted home Wi-Fi, start LAN mode:

```powershell
.\run_mecam.ps1 -Lan
```

Open the printed private-LAN URL from a device on the same Wi-Fi. Allow inbound TCP port 8081 on the Windows Private network profile if Windows Firewall blocks it. Create a camera in Devices to get a one-time enrollment code, then from PowerShell run:

```powershell
.\ssh_install_pi.ps1 -PiHost pi@Device1.local -DashboardUrl http://<windows-private-ip>:8081 -AllowInsecureLan
```

Replace the host/IP with a printed LAN address. This mode sends the device token, microphone audio, and motion clips over plain HTTP, so use it only on a trusted private LAN. Do not port-forward this service or expose it to the public internet. Use the HTTPS deployment below for remote access.

## Render and me-cam.com

1. Push this repository to a Git provider and create a Render Blueprint from `render.yaml`.
2. Keep the `me-cam-data` persistent disk mounted at `/var/data`. The cloud app uses `/var/data/mecam.sqlite3` and `/var/data/events/`. Back up the persistent `MECAM_STORAGE_KEY` securely; losing it makes saved event videos unrecoverable.
3. In Render, add `me-cam.com` as the service's custom domain. Set the DNS records Render provides at the domain registrar and wait for Render to issue its TLS certificate.
4. Open `https://me-cam.com`. Use the generated `MECAM_SETUP_KEY` from the Render service environment and create the owner account. Keep the key private; after creating the owner, remove `MECAM_SETUP_KEY` from the service environment and redeploy.
5. Confirm `https://me-cam.com/healthz` returns `{"ok":true}` and the browser shows a valid HTTPS certificate.

Render's free services do not provide persistent disks. Do not deploy this service to ephemeral storage: videos and SQLite data would be lost on restart. The included 20 GB disk is a starting point; increase it to fit the expected event volume.

## Enroll the Pi

From the dashboard, create a camera enrollment code. The code is single-use and expires in 48 hours. The Pi must have Raspberry Pi OS, SSH enabled, network access to `me-cam.com`, and the agent installed with the enrollment code and `DASHBOARD_URL=https://me-cam.com` in `/etc/me_cam.conf`.

From PowerShell on the workstation, after the dashboard is deployed and the camera enrollment code is visible, run:

```powershell
.\ssh_install_pi.ps1 -PiHost pi@<camera-hostname-or-ip>
```

The script checks the HTTPS health endpoint, prompts for the one-time enrollment code without echoing it, and transfers the local agent files over SSH/SCP. The SSH user must be allowed to run `sudo`; the installer backs up the previous agent config before replacing it. It sets OV5647, 720p, motion recording, and audio defaults. Review the installed service with `ssh pi@<camera-hostname-or-ip> 'sudo journalctl -u me_cam -n 100 --no-pager'`.

The attached `me_cam_installer` package currently contains a v3.1.5 release manifest, while its release installer requires a signed v3.1.8-or-newer release. The PowerShell SSH path uses local source files instead of bypassing or weakening the remote signature gate; it includes a narrow fix that suppresses motion alerts when a clip could not be recorded. Automatic updates are disabled for this manually staged install until a signed release service is deployed.

The app exposes the device activation, status, heartbeat, motion upload, stream-command, and live-frame routes used by the Pi agent. Uploaded motion clips survive Pi/SD-card failure only after upload completes and only while the cloud persistent disk remains healthy; use an additional off-provider backup for irreplaceable footage.

