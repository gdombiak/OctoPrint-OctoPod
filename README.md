# OctoPrint-OctoPod

[![Version](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=version&url=https://api.github.com/repos/gdombiak/OctoPrint-OctoPod/releases&query=$[0].name)]()
[![Released](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=released&url=https://api.github.com/repos/gdombiak/OctoPrint-OctoPod/releases&query=$[0].published_at)]()

This plugin sends immediate push notifications to your iOS devices running
[OctoPod](https://itunes.apple.com/us/app/octopod-for-octoprint/id1412557625?mt=8) once a
print has finished, made certain print progress, thermal runaway was detected, print reached specified layers,
bed reached target temp, bed cooled down or MMU requires user assistance. Push notifications when print is finished
include a snapshot of the configured camera. If you have multiple cameras then you can include
a snapshot of any of them. Even if the cameras are not connected to OctoPrint you can still
include a snapshot of the camera.

This plugin is required for updating Live Activities on your iPhone and iPad. iOS 16.2 is required
for this new feature to work.

The plugin also has support for [IFTTT](https://ifttt.com/home). Build your own integration leveraging
events fired by this plugin. Enter your [IFTTT Key](https://ifttt.com/maker_webhooks) and create your Applets.
IFTTT setup guide can be found [here](https://github.com/gdombiak/OctoPrint-OctoPod/wiki/How-to-use-IFTTT%3F).

This is the complete list of supported notifications:
1. Print finished (includes camera snapshot) or at specific progress percentages
2. Print reached specified layers (requires [DisplayLayerProgress plugin](https://plugins.octoprint.org/plugins/DisplayLayerProgress/))
3. Bed warmed up to target temp for a period of time. Helps get smooth first layers
4. Bed cooled down below specified threshold. Ideal to easily remove prints from bed
5. Extruder cooled down below specified threshold. Ideal to know when to turn printer off
6. Possible **thermal runaway** detected (bed, hotends or chamber)
7. Printer paused for user. This may happen when running out of filament or when doing manual multi color printing (M600)
8. [Palette 2 / Pro](https://www.mosaicmfg.com/products/palette-2) encountered a problem while printing
9. [MMU](https://shop.prusa3d.com/en/upgrades/183-original-prusa-i3-mk25smk3s-multi-material-2s-upgrade-kit-mmu2s.html#) requires user assistance (requires Prusa firmware)
10. Firmware errors. Get security alerts like thermal runaway, probing failed, min temp error, max temp error, etc.
11. RPi (or your preferred SoC) temperature is above the specified threshold

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/gdombiak/OctoPrint-OctoPod/archive/master.zip

## Configuration

Once plugin has been installed, go to _Settings_ and under _Plugins_ you will find a new
entry _OctoPod Notifications_. You must complete the field _Notification Server URL_ (use
default value) and optionally complete the field _Snapshot URL_ if you want a snapshot in
the notification. Update Bed, MMU and other notifications as needed.

You can test the configuration before saving it by using the _Send test notification_ button.

## Changelog

**[0.3.19]** (06/01/2025)
- NEW: OctoPod notification server status now visually indicated in OctoPod Settings

**[0.3.18]** (01/20/2025)
- NEW: Added support for [PrintTimeGenius plugin](https://plugins.octoprint.org/plugins/PrintTimeGenius/). Progress notifications will report correct progress
- NEW: 'Printer paused for user' notification is now sent for [M0 and M1 gcode commands](https://marlinfw.org/docs/gcode/M000-M001.html)
- FIXED: Ensure 'Notification Server URL' has no trailing slash

**[0.3.17]** (11/24/2024)
- NEW: Turn on HomeAssistant light when room is dark before taking snapshot. Requires [OctoLight Home Assistant plugin](https://plugins.octoprint.org/plugins/octolightHA/)
- NEW: Added support to receive notifications at specific heights
- IMPROVED: Added compatibility with Pillow 10.0.0 or later

**[0.3.16]** (11/26/2023)
- NEW: Added option to disable repeating bed temp notifications. Thanks [Jack Dalton](https://github.com/jackdalton2)
- NEW: Send notification when not enough filament when starting a new print - requires Spool Manager plugin

**[0.3.15]** (3/19/2023)
- NEW: Added support for updating Live Activities on iPhones. Requires OctoPod 3.26 to be released soon
- IMPROVED: Better detection of RPi temperature. Thanks [Braxton Schafer](https://github.com/bjschafer)

**[0.3.14]** (8/06/2022)
- IMPROVED: Alert notifications include better details. Thanks [Ivan Dombiak](https://github.com/ivannnito) & Arkadiusz Miśkiewicz
- IMPROVED: Receive pause notification when M25 is detected. Thanks [Ivan Dombiak](https://github.com/ivannnito)

**[0.3.13]** (4/16/2022)
- IMPROVED: Pause notification now detects M600/M601 when printing from OctoPrint. Prusa Mini users can now receive notifications when printer paused

**[0.3.12]** (12/29/2021)
- IMPROVED: Thermal runaway now plays nicely when printer paused waiting for user
- FIXED: OctoPrint will no longer freeze forever while waiting to obtain a camera snapshot
- FIXED: Removed double / in URL when connecting to APNS Proxy server

**[0.3.11]** (10/10/2021)
- NEW: Added klipper PAUSE compatibility to PausedForUser. Thanks [Mark Nebelung](https://github.com/mnebelung)
- FIXED: Print complete notification had a typo in Dutch translation. Thanks [devosthomas](https://github.com/devosthomas)
- FIXED: Use CSS class specific for octopod to not conflict with OctoPrint. Thanks [Sven Samoray](https://github.com/thelastWallE)

**[0.3.10]** (08/30/2021)
- FIXED: Notifications in Simplified Chinese now show proper translation. Thanks paul-tian
- FIXED: Notifications in Lithuanian now show proper translation

**[0.3.9]** (08/29/2021)
- NEW: Added support to delay notification when print is complete
- FIXED: Progress notification at 25%, 50% and 75% now include camera snapshot
- FIXED: Progress notification at 25%, 50% and 75% now respect camera orientation
- FIXED: UI formatting that broke formatting of other OctoPrint setting pages

**[0.3.8]** (08/28/2021)
- Use Marlin defaults to prevent false thermal runaway alerts. Defaults are also configurable from UI. Thanks bonjipoo
- Migration error thrown on fresh install with latest OctoPi install and Python 3. Thanks Pizzahd88

**[0.3.7]** (08/25/2021)
- NEW: Send notification with picture for first X (up to 10) layers for early catch of failed prints. Requires DisplayLayerProgress plugin
- NEW: Added Chinese simplified（简体中文）Translation. Thanks 零更酱 / clementatt
- Fixed false thermal runaway alert when temp briefly goes up while cooling down. Thanks Daniele Nicolucci

**[0.3.6]** (08/23/2021)
- Fixed false thermal runaway alert when target did not change but actual temp briefly cooled down

**[0.3.5]** (08/20/2021)
- Added 'advanced' thermal runaway detection. Thanks Josh Wright for all your help testing!!!
- Fixed another incorrect thermal runaway alert notification. Thanks Brian Porter

**[0.3.4]** (08/12/2021)
- Fixed incorrect thermal runaway alert notification. Thanks Brian Porter

**[0.3.3]** (08/10/2021)
- New notification for thermal runaway protection. Thanks Juha Kuusama for the idea!
- Configure your preferred notification sound. Thanks AuroraDigitalSystems for the idea! Requires OctoPod 3.12 (to be released)
- Added Dutch translation - Thanks Ihsan Topcu. Requires OctoPod 3.12 (to be released)

**[0.3.2]** (07/09/2021)
- Added new notification when hotend reached target temperature. Default is off
- Added new IFTTT event ```octopod-tool0-warmed``` when hotend reached target temperature. Default is off
- Fixed Python2 incompatibility. Plugin works again with Python 2

**[0.3.1]** (07/05/2021)
- Added support for 3rd party plugins to send push notifications. [Documentation](https://github.com/gdombiak/OctoPrint-OctoPod/wiki/How-to-send-push-notifications-from-3rd-party-plugins%3F)

**[0.3.0]** (02/07/2021)
- Added new notification when temperature of RPi is too hot
- You can now rotate/flip camera as needed

**[0.2.9]** (10/10/2020)
- Added support for new "Print again" button in push notification. Requires OctoPod 3.7

**[0.2.8]** (09/28/2020)
- Added IFTTT support

**[0.2.7]** (09/20/2020)
- User can now see and delete any registered device

**[0.2.6]** (04/30/2020)
- Fixed sending notification when image resolution was too big
- Send Test notification was ignoring entered unsaved snapshot URL

**[0.2.5]** (03/21/2020)
- Print notifications can be configured to be sent at different progress percentages
- Added new notification when print reaches specified layers (requires [DisplayLayerProgress plugin](https://plugins.octoprint.org/plugins/DisplayLayerProgress/) and OctoPod 3.2 or later)
- Added Russian translation. Thanks Alexey Tsykov

**[0.2.4]** (12/05/2019)
- Plugin is now compatible with upcoming OctoPrint 1.4.0 and Python 3

**[0.2.3]** (10/19/2019)
- Added French translation. Thanks Sébastien Laading

**[0.2.2]** (08/23/2019)
- Send notification when Palette 2 encountered a problem while printing
- (bug fix) Fixed HTML warning since 2 elements share the same id

**[0.2.1]** (08/03/2019)
- Send notification when extruder (tool0) cooled down below threshold once print finished
- Added Swedish translation. Thanks Jonas Bohdén

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

[0.3.19]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.19
[0.3.18]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.18
[0.3.17]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.17
[0.3.16]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.16
[0.3.15]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.15
[0.3.14]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.14
[0.3.13]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.13
[0.3.12]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.12
[0.3.11]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.11
[0.3.10]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.10
[0.3.9]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.9
[0.3.8]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.8
[0.3.7]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.7
[0.3.6]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.6
[0.3.5]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.5
[0.3.4]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.4
[0.3.3]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.3
[0.3.2]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.2
[0.3.1]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.1
[0.3.0]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.3.0
[0.2.9]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.9
[0.2.8]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.8
[0.2.7]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.7
[0.2.6]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.6
[0.2.5]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.5
[0.2.4]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.4
[0.2.3]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.3
[0.2.2]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.2
[0.2.1]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.1
[0.2.0]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.2.0
[0.1.3]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.1.3
[0.1.2]: https://github.com/gdombiak/OctoPrint-OctoPod/tree/0.1.2

## Thanks

Special thanks to [JetBrains](https://www.jetbrains.com/) for providing a free license for open source development
with [PyCharm](https://www.jetbrains.com/pycharm/).
