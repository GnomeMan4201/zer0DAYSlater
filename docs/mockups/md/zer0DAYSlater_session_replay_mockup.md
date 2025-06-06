# zer0DAYSlater session replay mockup

```shell
> replay

[+] Replaying deception campaign: tripwire_session_0423

───────────────────────────────
[1] Commit: "hotfix connection logic"
     ↳ IOC injected: hardcoded IP (45.13.12.203)
     ↳ Tag: ZDS-IOC-99

[2] CI Trigger:
     ↳ Build ran with modified test.sh
     ↳ Decoy token triggered outbound webhook

[3] Tripwire Hit:
     ↳ Sinkhole connected
     ↳ Alert forwarded to dummy SOC API

[4] Cleanup:
     ↳ IOC removed
     ↳ Report generated, zipped, archived

───────────────────────────────
[✓] Campaign complete. Risk: Minimal, Exposure: 3.2 mins

```
