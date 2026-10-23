# TVs seen in the field

If your TV isn't here, add a row from your run.

What the first reports from real TVs showed. «Home switch» is `optimize/install.sh launcher`;
«Screensaver from ADB» is whether Android starts our screensaver over ADB (where it doesn't, `shot.sh` shows our
app's preview of the same page and `measure.sh` writes «not measured»). Times are the whole `optimize/run.sh`.

| TV | Android | Home switch | Screensaver from ADB | ADB | Watch out for | Typical time |
|---|---|---|---|---|---|---|
| TCL Smart TV Pro G08 | 14 | works (launcherx + setupwraith off) | no, preview only | 5555; the first probe may hang, run it again | a Wi-Fi drop during the switch: the safety switch restores the stock home and `optimize/install.sh launcher` retries the switch by itself (once) | 11 min |
| TCL Smart TV Pro G05, G07, BeyondTV4 | 11 | works | yes | 5555 | `com.tcl.smartalexa` ships off outside Alexa's regions, expected | 14 min |
| TCL UnionTV | 9 | works | yes | 5555 | – | 15 min |
| Skyworth SWTV-20AE-PRO | 11 | works (tvlauncher off) | no | 5555, an occasional timeout that retries by itself | – | 14 min |
| Skyworth SWTV-24AE-4K | 14 | works | no | port 5555 closed: pair once through Wireless debugging, then `adb tcpip 5555`; the port disappears after every reboot | reconnect after each restart; APK uploads slow | 39 min |
| Xiaomi MiTV-MOOR2 | 11 | works | no | 5555 | screenshots may fail | 17 min |

## On the computer

- **macOS:** Homebrew's Python 3.12 or 3.13 (`brew install python@3.12`). python.org's Python has no certificates
  and the system 3.9 can't load the ADB package; `optimize/setup.sh` picks a good one and sets up the certificates.
- **Windows:** clone into a short folder such as `C:\CAF TV`; Git and Python come from winget
  (`winget install -e --id Git.Git`, `winget install -e --id Python.Python.3.12`); run every script in Git Bash.
