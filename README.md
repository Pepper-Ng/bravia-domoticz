# bravia-domoticz
A Domoticz plugin to control Bravia TV

## Installation

### Remote control
To make the remote controller working, domoticz.js has to be edited since it is hardcoded in there. Unfortunately, domoticz is not set-up to re-use this remote control for other plugins then the ones it was originally intended for (Kodi and Panasonic), but luckily this file can easily be changed to include the functionality.
Open file `~/domoticz/www/js/domoticz.js`
In function `ShowMediaRemote` add `HWType.indexOf('sony')>=0`  to the first if statement.

The complete if-statement should look something like the following:

    if (HWType.indexOf('Sony') >= 0 || HWType.indexOf('Kodi') >= 0 || HWType.indexOf('Panasonic') >= 0) {

This enables the remote to show up when the remote button is pressed.
To have the buttons on the remote send codes correctly to the plugin, the ajax calls to json.htm have to be added as well. Look for function `click_media_remote` and within statement `if (devIdx.length > 0) {` add to the if-else structure:

    if (HWType.indexOf('Sony') >= 0) {
        $.ajax({
            url: "json.htm?type=command&param=switchlight&idx=" + devIdx + "&switchcmd=" + action,
			async: true,
			dataType: 'json',
			//			 success: function(data) { $.cachenoty=generate_noty('info', '<b>Sent remote command</b>', 100); },
			error: function () { $.cachenoty = generate_noty('error', '<b>Problem sending remote command</b>', 1000); }
		});
    }
Now your remote should function properly! A copy of domoticz.js can be found in the repository, but care should be taken if copying it directly since this file might differ across different domoticz versions.