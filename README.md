# OctoPrint-Printoid

[![Version](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=version&url=https://api.github.com/repos/anthonyst91/OctoPrint-Printoid/releases&query=$[0].name)]()
[![Released](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=released&url=https://api.github.com/repos/anthonyst91/OctoPrint-Printoid/releases&query=$[0].published_at)]()

This is the official plugin made for the [Printoid for OctoPrint](https://play.google.com/store/apps/details?id=fr.yochi76.printoid.phones.premium&utm_source=github&utm_medium=plugin) application.

It aims to send you push notifications to your device(s) on specific events on your OctoPrint server.
This plugin has been inspired by the great plugin made by the developer of [OctoPod](https://itunes.apple.com/us/app/octopod-for-octoprint/id1412557625?mt=8) for iOS.
He plugin (the original one) can be found [here](https://github.com/gdombiak/OctoPrint-OctoPod).
If you like the Printoid Plugin, then please support the developer of the OctoPod plugin, because he did an amazing work!

The plugin also has support for [IFTTT](https://ifttt.com/home). Build your own integration leveraging
events fired by this plugin. Enter your [IFTTT Key](https://ifttt.com/maker_webhooks) and create your Applets.
IFTTT setup guide can be found [here](https://github.com/gdombiak/OctoPrint-OctoPod/wiki/How-to-use-IFTTT%3F).

The Printoid Plugin communicates with Firebase Cloud Messaging server over a Google Cloud Function, located at the following URL:
	https://us-central1-firebase-printoid.cloudfunctions.net/printoidPluginGateway

This is the complete list of supported notifications:
1. Print finished or at specific progress percentages
2. The state of your printer is changing (to PRINTING, to PAUSED, to ERROR, and back to OPERATIONAL, for example)
3. Print reached specified layers (requires [DisplayLayerProgress plugin](https://plugins.octoprint.org/plugins/DisplayLayerProgress/))
4. Bed warmed up to target temp for a period of time. Helps get smooth first layers
5. Bed cooled down below specified threshold. Ideal to easily remove prints from bed
6. Extruder cooled down below specified threshold. Ideal to know when to turn printer off
7. Possible **thermal runaway** detected (bed, hotends or chamber)
8. Printer paused for user. This may happen when running out of filament or when doing manual multi color printing (M600)
9. [Palette 2 / Pro](https://www.mosaicmfg.com/products/palette-2) encountered a problem while printing
10. [MMU](https://shop.prusa3d.com/en/upgrades/183-original-prusa-i3-mk25smk3s-multi-material-2s-upgrade-kit-mmu2s.html#) requires user assistance (requires Prusa firmware)
11. Firmware errors. Get security alerts like thermal runaway, probing failed, min temp error, max temp error, etc.
12. RPi (or your preferred SoC) temperature is above the specified threshold

This plugin does not need your phone to be connected to the same network as your OctoPrint server to send the notifications.
You will be able to receive the notifications even if you are out of your home and/or connected to the cellular network (3G/4G/5G) for example.

This plugin does not need your network to be opened to the Internet. You do not need to do port forwarding, and you do not need to setup a VPN ;)

Printoid does not need to be opened on your device to receive the notifications from the plugin. The app can be killed and your phone can be sleeping, you will receive the notifications whatever happens!

## What CAN'T this plugin do for you?

This plugin is not a plugin to control your 3D printer remotely. Please be nice, don't yell at me because this was what you expected...
May be this will be possible in the future, but for the moment it would require me too much work.

This plugin only sends push to your device in order to show you notifications on your device for specific events.
This way it will not update the information contained in the app (at least for the moment).

## Setup

Install the plugin via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/anthonyst91/OctoPrint-Printoid/archive/master.zip

## Configuration

Once the plugin has been installed:

1. Open the _Settings_ panel of OctoPrint
2. Navigate to the _Plugins_ section and select _Printoid Notifications_
3. Open the Printoid application on your phone, and connect it to your OctoPrint server
4. Wait few seconds for the app to be fully refreshed
5. From the OctoPrint interface, click on the _Send test notification_ button
6. Check on your phone, you should receive your first notification!
7. The Printoid app is now paired with the Printoid plugin, you will receive notifications!

## Thanks

Special thanks to [JetBrains](https://www.jetbrains.com/) for providing a free license for open source development
with [PyCharm](https://www.jetbrains.com/pycharm/).
