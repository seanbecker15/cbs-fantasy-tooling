launchctl unload ~/Library/LaunchAgents/com.cbs-sports.scraper.plist
cp schedule/com.cbs-sports.scraper.plist ~/Library/LaunchAgents
chmod 644 ~/Library/LaunchAgents/com.cbs-sports.scraper.plist
launchctl load ~/Library/LaunchAgents/com.cbs-sports.scraper.plist
