### Scheduled task

On OSX, use `launchctl` to schedule this program to run every Tuesday morning at 2am.

1. Create package
2. Store package in ~/Library/3gs
3. Store .plist file in ~/Library/LaunchAgents
4. Run commands below to manually trigger scheduled task

OSX Manual Launch Commands

```zsh
$ cd ~/Library/LaunchAgents
$ launchctl unload path/to/some.plist     # Unload / stop task
$ launchctl load path/to/some.plist       # Load / resume task
$ launchctl list path/to/some.plist       # List task info
$ sudo launchctl list                     # List "root" tasks
$ launchctl list                          # List user tasks
```

Alternatively there are helpers scripts to schedule / unschedule:
```zsh
$ ./scripts/schedule-task.sh # set up scheduled proc (runs every tuesday at 9am)
$ ./scripts/unschedule-task.sh # clears schedule proc
```

Logs are stored in `/tmp/cbs-sports-scraper/stdout.log` and `/tmp/cbs-sports-scraper/stderr.log`

### Remember!

Open laptop and check for email on Tuesday mornings.
