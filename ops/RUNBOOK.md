# ILMA operations

Runtime database is **ilma**. Never use another project's database. Current host:
`/home/ubuntu/shared/all_projects/ilma`, venv `/home/ubuntu/venv`, app port 8001 on
loopback, public HTTPS through `cloudflared-app.service`. Keep one worker/replica:
admission counters are process-local; deploy shared ingress limits before scaling.

## Check and recover

```sh
systemctl status ilma-app.service
systemctl list-timers 'ilma-*'
journalctl -u ilma-app.service --since '15 minutes ago'
journalctl -t ilma-ops --since today
curl --fail http://127.0.0.1:8001/v1/health
curl --fail https://app.sumon.me/v1/health
```

Check the JSON `ok` field as well as HTTP status. The local monitor does both.
If local health succeeds but public health fails, inspect the Cloudflare tunnel.
If DB is unavailable, restore connection/access to **ilma**, not another database.
Do not paste `.env`, connection strings, provider bodies or recordings into logs.

After a tested code update: `sudo systemctl restart ilma-app.service`, check local
and public health, then test one typed request and one consented voice request.
Browser assets require a new index/service-worker version when changed.

## Backups and isolated restore

```sh
sudo systemctl start ilma-backup.service
sudo journalctl -u ilma-backup.service -n 10
```

Backups live outside the web root at `/var/lib/ilma-backups` (0700/0600). Seven
snapshots are kept. The dump selects only `ilma` and ignores unrelated MySQL
defaults. Retained diagnostic data is included while diagnostic capture is active.
These are local, unencrypted backups: configure an encrypted off-host destination
before claiming disaster recovery. Do not upload them to GitHub.

For an isolated drill, run the module with `PYTHONPATH` set to this project's api
and `DB_NAME=ilma`; supply `restore-check --file <private snapshot>`. It requires
permission to create/drop its newly generated `ilma_restore_check_<uuid>` database.
Keep those privileges out of the app account. On this host, the explicit
`--admin-socket /var/run/mysqld/mysqld.sock` option may be run as local root for the
drill. It never accepts the live database as a restore target and never drops a
pre-existing target. A drill is not authorization to restore over live data.

## Retention and failure signals

`ilma-voice-cleanup.timer` expires ordinary logs after 30 days and diagnostics
after seven days, including when capture is disabled or no requests arrive. A
200-sample diagnostic maximum also applies. Check its unit Result and journal.
Exported files and historical backups require separate deletion decisions.

`ilma-monitor.timer` runs every two minutes; failing jobs emit a local journal
error via `ilma-ops-alert@.service`. Configure an explicitly authorized external
alert destination before relying on unattended production response.

## Rollback and release gates

Record the deployed commit, retain a clean previous checkout and verify it on a
separate loopback port against the current schema before changing public traffic.
Keep secrets outside release archives. Do not use destructive Git resets or
directory synchronization that can delete `.env`. Do not roll back schema/data
blindly: imports and private diagnostic writes are not code changes.

The 27 October canary validated `26f729e` against the current schema. Public
traffic switching and off-host restore remain to rehearse. Production switch and
outstanding acceptance are tracked in `docs/RELEASE_HARDENING.md`.
