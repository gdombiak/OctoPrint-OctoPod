---
layout: plugin

id: printoid
title: OctoPrint-Printoid
description: OctoPrint plugin for Printoid
author: Anthony Stéphan
license: Apache-2.0

date: 2020-04-25

homepage: https://github.com/anthonyst91/OctoPrint-Printoid
source: https://github.com/anthonyst91/OctoPrint-Printoid
archive: https://github.com/anthonyst91/OctoPrint-Printoid/archive/master.zip

# TODO
# Set this to true if your plugin uses the dependency_links setup parameter to include
# library versions not yet published on PyPi. SHOULD ONLY BE USED IF THERE IS NO OTHER OPTION!
#follow_dependency_links: false

# TODO
tags:
- printoid
- bed temperature
- print finished
- Android
- notifications

# TODO
screenshots:
- url: /assets/img/plugins/printoid/settings.png
  alt: Configure Notifications
  caption: Configure Notifications
- url: /assets/img/plugins/printoid/print_finished.jpg
  alt: Print Finished
  caption: Print Finished
- url: /assets/img/plugins/printoid/bed_cooled.jpg
  alt: Bed Cooled Down
  caption: Bed Cooled Down

# TODO
featuredimage: /assets/img/plugins/printoid/print_finished.jpg

---

This plugin sends immediate push notifications to your Android devices when:
* your print has finished. Notifications include a snapshot of your camera. If you
have multiple cameras then you can include a snapshot of any of them. Even if the
cameras are not connected to OctoPrint you can still make use of them
* bed has cooled down enough so you can remove your print
* bed has warmed up to target temperature for a specified period so you can start
printing knowing that bed's material won't expand anymore

If you are using [Printoid](https://play.google.com/store/apps/details?id=fr.yochi76.printoid.phones.premium)
to control your printer from any Android device then this plugin is a great addition.

This plugin is based on the plugin made by the developer of [OctoPod](https://itunes.apple.com/us/app/octopod-for-octoprint/id1412557625?mt=8)


## Installation

Installation is super easy. There is no need to change your router configuration, do
port forwarding or open holes in your firewall. Just follow these steps and you will
be up and running in no time.

1. Download and install this plugin as you would do with any other OctoPrint plugin
1. Download [Printoid](https://play.google.com/store/apps/details?id=fr.yochi76.printoid.phones.premium) from the App Store
1. Start [Printoid](https://play.google.com/store/apps/details?id=fr.yochi76.printoid.phones.premium) so
it can receive notifications. This step is required for testing the plugin
1. Go to OctoPrint settings and configure this plugin
  * If needed, update _Snapshot URL_ to point to the camera that will provide an image when your print is finished
  * Click on _Send test notification_ to confirm setup is operational
  * Configure _Bed Notifications_ to receive cooled down or warm up bed events
  * Save settings and enjoy
