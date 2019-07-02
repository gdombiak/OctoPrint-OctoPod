# OctoPrint-OctoPod

[![Version](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=version&url=https://api.github.com/repos/gdombiak/OctoPrint-OctoPod/releases&query=$[0].name)]()
[![Released](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=released&url=https://api.github.com/repos/gdombiak/OctoPrint-OctoPod/releases&query=$[0].published_at)]()

This plugin sends immediate push notifications to your iOS devices running 
[OctoPod](https://itunes.apple.com/us/app/octopod-for-octoprint/id1412557625?mt=8) once a 
print has finished, bed reached target temp, bed cooled down or MMU requires user assistance. 
Push notifications when print is finished include a snapshot of the configured camera. If 
you have multiple cameras then you can include a snapshot of any of them. Even if the 
cameras are not connected to OctoPrint you can still include a snapshot of the camera.

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/gdombiak/OctoPrint-OctoPod/archive/master.zip

## Configuration

Once plugin has been installed, go to _Settings_ and under _Plugins_ you will find a new
entry _OctoPod Notifications_. You must complete the field _Notification Server URL_ (use 
default value) and optionally complete the field _Snapshot URL_ if you want a snapshot in 
the notification. Update Bed and MMU Notifications as needed.

You can test the configuration before saving it by using the _Send test notification_ button.

## Changelog

**[0.2.0]** (06/30/2019)
- Send notification when printer paused for user
- Send notification for firmware errors (e.g. runaway temp, min temp error, max temp error, probing failed, etc.)
- Send notification when OctoPrint lost connection to printer
- Notifications are now displayed even if the iOS app was killed by user
- (bug fix) Not all iOS devices were receiving bed or MMU events
- (bug fix) Sometimes Print Finished notification is displayed twice
- (bug fix) Log level is not restored after a restart

**[0.1.3]** (06/16/2019)
- Send MMU Notification when user assistance is required. Requires Prusa firmware.

**[0.1.2]** (05/28/2019)
- Initial Release

[0.2.0]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.0
[0.1.3]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.1.3
[0.1.2]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.1.2
