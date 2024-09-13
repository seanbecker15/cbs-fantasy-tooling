### Scheduled task

On OSX, use `launchctl` to schedule this program to run every Tuesday morning at 2am.

1. Create package
2. Store package in ~/Library/3gs
3. Store .plist file in ~/Library/LaunchAgents
4. Run commands below to manually trigger scheduled task

OSX Manual Launch Commands

```bash
$ cd ~/Library/LaunchAgents
$ launchctl unload path/to/some.plist     # Unload / stop task
$ launchctl load path/to/some.plist       # Load / resume task
$ launchctl list path/to/some.plist       # List task info
$ sudo launchctl list                     # List "root" tasks
$ launchctl list                          # List user tasks
```

Logs are stored in `/tmp/cbs-sports-scraper/stdout.log` and `/tmp/cbs-sports-scraper/stderr.log`

### Remember!

Open laptop and check for email on Tuesday mornings.
