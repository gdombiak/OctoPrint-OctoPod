# OctoPrint-Printoid

[![Version](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=version&url=https://api.github.com/repos/anthonyst91/OctoPrint-Printoid/releases&query=$[0].name)]()
[![Released](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=released&url=https://api.github.com/repos/anthonyst91/OctoPrint-Printoid/releases&query=$[0].published_at)]()

This plugin sends immediate push notifications to your Android devices running
[Printoid for OctoPrint](https://play.google.com/store/apps/details?id=fr.yochi76.printoid.phones.premium&utm_source=github&utm_medium=plugin) once a
print has finished, made certain print progress, reached specified layers, bed reached target temp,
bed cooled down or MMU requires user assistance. Push notifications when print is finished
include a snapshot of the configured camera. If you have multiple cameras then you can include
a snapshot of any of them. Even if the cameras are not connected to OctoPrint you can still
include a snapshot of the camera.

It is based on the great plugin made by the developer of OctoPod of iOS:
[OctoPod](https://itunes.apple.com/us/app/octopod-for-octoprint/id1412557625?mt=8)
[OctoPrint-OctopPod plugin](https://github.com/gdombiak/OctoPrint-OctoPod)

This is the complete list of supported notifications:
1. Print finished (includes camera snapshot) or at specific progress percentages
1. Print reached specified layers (requires [DisplayLayerProgress plugin](https://plugins.octoprint.org/plugins/DisplayLayerProgress/))
1. Bed warmed up to target temp for a period of time. Helps get smooth first layers
1. Bed cooled down below specified threshold. Ideal to easily remove prints from bed
1. Extruder cooled down below specified threshold. Ideal to know when to turn printer off
1. Printer paused for user. This may happen when running out of filament or when doing manual multi color printing (M600)
1. [Palette 2 / Pro](https://www.mosaicmfg.com/products/palette-2) encountered a problem while printing
1. [MMU](https://shop.prusa3d.com/en/upgrades/183-original-prusa-i3-mk25smk3s-multi-material-2s-upgrade-kit-mmu2s.html#) requires user assistance (requires Prusa firmware)
1. Firmware errors. Get security alerts like thermal runaway, probing failed, min temp error, max temp error, etc.

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/anthonyst91/OctoPrint-Printoid/archive/master.zip

## Configuration

Once plugin has been installed, go to _Settings_ and under _Plugins_ you will find a new
entry _Printoid Notifications_. You must complete the field _Notification Server URL_ (use
default value) and optionally complete the field _Snapshot URL_ if you want a snapshot in
the notification. Update Bed, MMU and other notifications as needed.

You can test the configuration before saving it by using the _Send test notification_ button.
