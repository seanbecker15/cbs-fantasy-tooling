launchctl unload ~/Library/LaunchAgents/com.cbs-sports.scraper.plist
cp schedule/com.cbs-sports.scraper.plist ~/Library/LaunchAgents
launchctl load ~/Library/LaunchAgents/com.cbs-sports.scraper.plist
