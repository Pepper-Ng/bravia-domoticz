#
#       Sony Bravia Plugin
#       Author: Stef Hermans, 2019
#       Author original plugin: G3rard
#
"""
<plugin key="sonyremote" name="Sony TV Remote" author="stefhermans" version="1.2" wikilink="https://github.com/Stef-Hermans/bravia-domoticz" externallink="https://www.sony.com/electronics/bravia">
    <description>
Sony Bravia plugin.<br/><br/>
It will work on Sony Bravia models 2013 and newer.<br/>
Works with pre-shared key.<br/><br/>
Prerequisites:<br/>
* Enable remote start on your TV: [Settings] => [Network] => [Home Network Setup] => [Remote Start] => [On]<br/>
* Enable pre-shared key on your TV: [Settings] => [Network] => [Home Network Setup] => [IP Control] => [Authentication] => [Normal and Pre-Shared Key]<br/>
* Set pre-shared key on your TV: [Settings] => [Network] => [Home Network Setup] => [IP Control] => [Pre-Shared Key] => sony<br/>
* Give your TV a static IP address, or make a DHCP reservation for a specific IP address in your router.<br/>
* Determine the MAC address of your TV: [Settings] => [Network] => [Network Setup] => [View Network Status]<br/>
    </description>
    <params>
        <param field="Address" label="IP address" width="200px" required="true" default="192.168.1.191"/>
        <param field="Mode1" label="Pre-shared key (PSK)" width="200px" required="true" default="sony"/>
        <param field="Mode2" label="MAC address" width="200px" required="true" default="Android"/>
        <param field="Mode3" label="Volume bar" width="75px">
            <options>
                <option label="True" value="Volume"/>
                <option label="False" value="Fixed" default="true" />
            </options>
        </param>
        <param field="Mode5" label="Update interval (sec)" width="30px" required="true" default="30"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import datetime
import sys
import json

from bravia import BraviaRC

class BasePlugin:
    HttpConn = None
    nextConnect = 3
    outstandingPings = 0
    powerOn = False
    tvVolume = 0
    tvSource = 0
    tvControl = 0
    tvChannel = 10
    tvPlaying = {}
    SourceOptions3 = {}
    SourceOptions4 = {}
    SourceOptions5 = {}
    startTime = ''
    endTime = ''
    perc_playingTime = 0
    _tv = None
    _getState = None
  
    def onStart(self):
        global _tv

        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)

        self.SourceOptions3 =   {   "LevelActions"  : "||||||",
                                    "LevelNames"    : "Off|TV|HDMI1|HDMI2|HDMI3|HDMI4|Netflix",
                                    "LevelOffHidden": "true",
                                    "SelectorStyle" : "0"
                                }
        self.SourceOptions4 =   {   "LevelActions"  : "|||||",
                                    "LevelNames"    : "Off|Play|Stop|Pause|TV Pause|Exit",
                                    "LevelOffHidden": "true",
                                    "SelectorStyle" : "0"
                                }
        self.SourceOptions5 =   {   "LevelActions"  : "||||||||||",
                                    "LevelNames"    : "Off|CH1|CH2|CH3|CH4|CH5|CH6|CH7|CH8|CH9|--Choose a channel--",
                                    "LevelOffHidden": "true",
                                    "SelectorStyle" : "1"
                                }

        if Parameters["Mode3"] == "Volume" and 2 not in Devices:
            Domoticz.Device(Name="Volume", Unit=2, Type=244, Subtype=73, Switchtype=7, Image=8, Used=1).Create()
            Domoticz.Log("Volume device created")
        if Parameters["Mode3"] != "Volume" and 2 in Devices:
            Devices[2].Delete()
            Domoticz.Log("Volume device deleted")
        # TODO : For some reason the first device entry in Devices is fucked and will weirdly toggle states
        #        This device itself, now sitting in Utility tab, is obsolete but prevents useful devices from being bugged
        if 1 not in Devices:
            Domoticz.Device(Name="Info", Unit=1, Type=243, Subtype=19, Used=1).Create()
            Domoticz.Log("TV Status device created")
        if 3 not in Devices:
            Domoticz.Device(Name="Source", Unit=3, Type=244, Subtype=62, Switchtype=18, Image=2, Options=self.SourceOptions3, Used=1).Create()
            Domoticz.Log("Source device created")
        if 4 not in Devices:
            Domoticz.Device(Name="Control", Unit=4, Type=244, Subtype=62, Switchtype=18, Image=2, Options=self.SourceOptions4, Used=1).Create()
            Domoticz.Log("Control device created")
        if 5 not in Devices:
            Domoticz.Device(Name="Channel", Unit=5, Type=244, Subtype=62, Switchtype=18, Image=2, Options=self.SourceOptions5, Used=1).Create()
            Domoticz.Log("Channel device created")
        if 7 not in Devices:
            Domoticz.Device(Name="Status", Unit=7, Type=244, Subtype=73, Switchtype=17, Image=2, Used=1).Create()
        
        if 2 in Devices: self.tvVolume = Devices[2].nValue   #--> of sValue
        if 3 in Devices: self.tvSource = Devices[3].sValue
        if 4 in Devices: self.tvControl = Devices[4].sValue
        if 5 in Devices: self.tvChannel = Devices[5].sValue

        self.HttpConn = Domoticz.Connection(Name="HttpConn", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port="80")
        self.HttpConn.Connect()

        _tv = BraviaRC(self.HttpConn, Parameters["Address"], Parameters["Mode1"])
        
        # Set update interval, values below 10 seconds are not allowed due to timeout of 5 seconds in bravia.py script
        updateInterval = int(Parameters["Mode5"])
        if updateInterval > 30: updateInterval = 30
        elif updateInterval < 10: updateInterval = 10
        Domoticz.Debug("Update interval set to " + str(updateInterval) + " (minimum is 10 seconds)")
        Domoticz.Heartbeat(updateInterval)
        
        return True

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Connected successfully to: "+Connection.Address+":"+Connection.Port)
            _tv.printconf()
        else:
            Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
            for Key in Devices:
                UpdateDevice(Key, 0, Devices[Key].sValue) # Turn devices off in Domoticz
        return True

    def onDisconnect(self, Connection):
        Domoticz.Debug("Device has disconnected")
        return

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        Command = Command.strip()
        action, sep, params = Command.partition(' ')
        action = action.capitalize()
        params = params.capitalize()

        if self.powerOn == False:
            if Unit == 7:     # TV power switch
                if action == "On":
                    # Start TV when WOL is not available, only works on Android
                    if Parameters["Mode2"] == "Android":
                        Domoticz.Debug("No MAC address configured, TV will be started with setPowerStatus command (Android only)")
                        try:
                            _tv.turn_on_command()
                            self.tvPlaying = "TV starting" # Show that the TV is starting, as booting the TV takes some time
                            self.SyncDevices()
                        except Exception as err:
                            Domoticz.Debug("Error when starting TV with set PowerStatus, Android only (" +  str(err) + ")")
                    # Start TV using WOL
                    else:
                        try:
                            _tv.turn_on()
                            self.tvPlaying = "TV starting" # Show that the TV is starting, as booting the TV takes some time
                            self.SyncDevices()
                        except Exception as err:
                            Domoticz.Debug("Error when starting TV using WOL (" +  str(err) + ")")
        else:
            if Unit == 7:     # TV power switch
                if action == "Off":
                    _tv.turn_off()
                    self.tvPlaying = "Off"
                    self.SyncDevices()
                # Remote buttons (action is capitalized so chosen for Command)
                elif Command == "ChannelUp": _tv.send_req_ircc("AAAAAQAAAAEAAAAQAw==")       # ChannelUp
                elif Command == "ChannelDown": _tv.send_req_ircc("AAAAAQAAAAEAAAARAw==")     # ChannelDown
                elif Command == "Channels": _tv.send_req_ircc("AAAAAQAAAAEAAAA6Aw==")        # Display, shows information on what is playing
                elif Command == "VolumeUp": _tv.send_req_ircc("AAAAAQAAAAEAAAASAw==")        # VolumeUp
                elif Command == "VolumeDown": _tv.send_req_ircc("AAAAAQAAAAEAAAATAw==")      # VolumeDown
                elif Command == "Mute": _tv.send_req_ircc("AAAAAQAAAAEAAAAUAw==")            # Mute
                elif Command == "Select": _tv.send_req_ircc("AAAAAQAAAAEAAABlAw==")          # Confirm
                elif Command == "Up": _tv.send_req_ircc("AAAAAQAAAAEAAAB0Aw==")              # Up
                elif Command == "Down": _tv.send_req_ircc("AAAAAQAAAAEAAAB1Aw==")            # Down
                elif Command == "Left": _tv.send_req_ircc("AAAAAQAAAAEAAAA0Aw==")            # Left
                elif Command == "Right": _tv.send_req_ircc("AAAAAQAAAAEAAAAzAw==")           # Right
                elif Command == "Home": _tv.send_req_ircc("AAAAAQAAAAEAAABgAw==")            # Home
                elif Command == "Info": _tv.send_req_ircc("AAAAAgAAAKQAAABbAw==")            # EPG
                elif Command == "Back": _tv.send_req_ircc("AAAAAgAAAJcAAAAjAw==")            # Return
                elif Command == "ContextMenu": _tv.send_req_ircc("AAAAAgAAAJcAAAA2Aw==")     # Options
                elif Command == "FullScreen": _tv.send_req_ircc("AAAAAQAAAAEAAABjAw==")      # Exit
                elif Command == "ShowSubtitles": _tv.send_req_ircc("AAAAAQAAAAEAAAAlAw==")   # Input
                elif Command == "Stop": _tv.send_req_ircc("AAAAAgAAAJcAAAAYAw==")            # Stop
                elif Command == "BigStepBack": _tv.send_req_ircc("AAAAAgAAAJcAAAAZAw==")     # Pause
                elif Command == "Rewind": _tv.send_req_ircc("AAAAAgAAAJcAAAAbAw==")          # Rewind
                elif Command == "PlayPause": _tv.send_req_ircc("AAAAAgAAABoAAABnAw==")       # TV pause
                elif Command == "FastForward": _tv.send_req_ircc("AAAAAgAAAJcAAAAcAw==")     # Forward
                elif Command == "BigStepForward": _tv.send_req_ircc("AAAAAgAAAJcAAAAaAw==")  # Play

            if Unit == 2:     # TV volume
                if action == 'Set':
                    self.tvVolume = str(Level)
                    _tv.set_volume_level(self.tvVolume)
                elif action == "Off":
                    _tv.mute_volume()
                    UpdateDevice(2, 0, str(self.tvVolume))
                elif action == "On":
                    _tv.mute_volume()
                    UpdateDevice(2, 1, str(self.tvVolume))

            if Unit == 3:   # TV source
                if Command == 'Set Level':
                    if Level == 10: 
                        _tv.send_req_ircc("AAAAAQAAAAEAAAAkAw==") #TV
                        self.GetTVInfo()
                    if Level == 20:
                        _tv.send_req_ircc("AAAAAgAAABoAAABaAw==") #HDMI1
                        self.tvPlaying = "HDMI 1"
                    if Level == 30:
                        _tv.send_req_ircc("AAAAAgAAABoAAABbAw==") #HDMI2
                        self.tvPlaying = "HDMI 2"
                    if Level == 40:
                        _tv.send_req_ircc("AAAAAgAAABoAAABcAw==") #HDMI3
                        self.tvPlaying = "HDMI 3"
                    if Level == 50:
                        _tv.send_req_ircc("AAAAAgAAABoAAABdAw==") #HDMI4
                        self.tvPlaying = "HDMI 4"
                    if Level == 60:
                        _tv.send_req_ircc("AAAAAgAAABoAAAB8Aw==") #Netflix
                        self.tvPlaying = "Netflix"
                    self.tvSource = Level
                    self.SyncDevices()

            if Unit == 4:   # TV control
                if Command == 'Set Level':
                    if Level == 10: _tv.send_req_ircc("AAAAAgAAAJcAAAAaAw==") #Play
                    if Level == 20: _tv.send_req_ircc("AAAAAgAAAJcAAAAYAw==") #Stop
                    if Level == 30: _tv.send_req_ircc("AAAAAgAAAJcAAAAZAw==") #Pause
                    if Level == 40: _tv.send_req_ircc("AAAAAgAAABoAAABnAw==") #Pause TV
                    if Level == 50: _tv.send_req_ircc("AAAAAQAAAAEAAABjAw==") #Exit
                    self.tvControl = Level
                    self.SyncDevices()

            if Unit == 5:   # TV channels
                if Command == 'Set Level':
                    if Level == 10: _tv.send_req_ircc("AAAAAQAAAAEAAAAAAw==") #1
                    if Level == 20: _tv.send_req_ircc("AAAAAQAAAAEAAAABAw==") #2
                    if Level == 30: _tv.send_req_ircc("AAAAAQAAAAEAAAACAw==") #3
                    if Level == 40: _tv.send_req_ircc("AAAAAQAAAAEAAAADAw==") #4
                    if Level == 50: _tv.send_req_ircc("AAAAAQAAAAEAAAAEAw==") #5
                    if Level == 60: _tv.send_req_ircc("AAAAAQAAAAEAAAAFAw==") #6
                    if Level == 70: _tv.send_req_ircc("AAAAAQAAAAEAAAAGAw==") #7
                    if Level == 80: _tv.send_req_ircc("AAAAAQAAAAEAAAAHAw==") #8
                    if Level == 90: _tv.send_req_ircc("AAAAAQAAAAEAAAAIAw==") #9
                    # Level 100 = --Choose a channel--
                    self.tvChannel = Level
                    self.SyncDevices()

        return

    def onMessage(self, Connection, Data):        
        strData = Data["Data"].decode("utf-8", "ignore")
        Status = str(Data["Status"])
        Domoticz.Debug("HTTP Status: "+Status+", Content Type: " + Data['Headers']['Content-Type'])
        
        #if (Data['Headers']['Connection'] == "close"): 
            # Reconnect : True
        
        if (Data['Headers']['Content-Type'] == "application/json"):
            resp = json.loads(strData)        
        
            if ('result' in resp):
                results = resp.get('result')
                if ('type' in results[0] and results[0]['type'] == "IR_REMOTE_BUNDLE_TYPE_AEP_N" and results[1] is not None):
                    _tv.set_commands(results[1])
                    Domoticz.Debug("Commands set")
                    
                elif ('status' in results[0]):
                    if( self.outstandingPings >= 0):
                        self.outstandingPings = self.outstandingPings - 1
                    tvStatus = results[0]['status']
                    if tvStatus == 'active':                        # TV is on
                        self.powerOn = True
                        self.GetTVInfo()
                    else:                                           # TV is off or standby
                        self.powerOn = False
                    
                    self.SyncDevices()

                elif (self._getState == "TVInfo"):
                    # TODO : Source information is not updated
                    if resp is not None and not resp.get('error'):
                        self._getState = None
                        playing_content_data = results[0]
                        self.tvPlaying = {}
                        self.tvPlaying['programTitle'] = playing_content_data.get('programTitle')
                        self.tvPlaying['title'] = playing_content_data.get('title')
                        self.tvPlaying['programMediaType'] = playing_content_data.get('programMediaType')
                        self.tvPlaying['dispNum'] = playing_content_data.get('dispNum')
                        self.tvPlaying['source'] = playing_content_data.get('source')
                        self.tvPlaying['uri'] = playing_content_data.get('uri')
                        self.tvPlaying['durationSec'] = playing_content_data.get('durationSec')
                        self.tvPlaying['startDateTime'] = playing_content_data.get('startDateTime')

                        if self.tvPlaying['programTitle'] != None:      # Get information on channel and program title if tuner of TV is used
                            if self.tvPlaying['startDateTime'] != None: # Show start time and end time of program
                                self.startTime, self.endTime, self.perc_playingTime = _tv.playing_time(self.tvPlaying['startDateTime'], self.tvPlaying['durationSec'])
                                if (int(self.tvPlaying['dispNum']) < 10):
                                    self.tvChannel = 10*int(self.tvPlaying['dispNum'])

                                #str(int(self.tvPlaying['dispNum'])) + ': ' + 
                                self.tvPlaying = self.tvPlaying['title'] + ' - ' + self.tvPlaying['programTitle'] + ' [' + str(self.startTime) + ' - ' + str(self.endTime) +']'  
                                Domoticz.Debug("Program information: " + str(self.startTime) + "-" + str(self.endTime) + " [" + str(self.perc_playingTime) + "%]")
                            else:
                                self.tvPlaying = str(int(self.tvPlaying['dispNum'])) + ': ' + self.tvPlaying['title'] + ' - ' + self.tvPlaying['programTitle']

                            self.tvSource = 10
                            UpdateDevice(3, 1, str(self.tvSource))      # Set source device to TV
                            UpdateDevice(5, 1, str(self.tvChannel))
                            UpdateDevice(7, 1, self.tvPlaying)

                        else:                                           # No program info found
                            if self.tvPlaying['title'] != '':
                                self.tvPlaying = self.tvPlaying['title']
                            else:
                                self.tvPlaying = "Netflix"              # When TV plays apps, no title information (in this case '') is available, so assume Netflix is playing
                            if "/MHL" in self.tvPlaying:                # Source contains /MHL, that can be removed
                                self.tvPlaying = self.tvPlaying.replace("/MHL", "")
                            #UpdateDevice(1, 1, self.tvPlaying)
                            if "HDMI 1" in self.tvPlaying:
                                self.tvSource = 20
                                UpdateDevice(3, 1, str(self.tvSource))  # Set source device to HDMI1
                            elif "HDMI 2" in self.tvPlaying:
                                self.tvSource = 30
                                UpdateDevice(3, 1, str(self.tvSource))  # Set source device to HDMI2
                            elif "HDMI 3" in self.tvPlaying:
                                self.tvSource = 40
                                UpdateDevice(3, 1, str(self.tvSource))  # Set source device to HDMI3
                            elif "HDMI 4" in self.tvPlaying:
                                self.tvSource = 50
                                UpdateDevice(3, 1, str(self.tvSource))  # Set source device to HDMI4
                            elif "Netflix" in self.tvPlaying:
                                self.tvSource = 60
                                UpdateDevice(3, 1, str(self.tvSource))  # Set source device to Netflix

                        # Get volume information of TV
                        if Parameters["Mode3"] == "Volume":
                            _tv.get_volume_info()

                        # Update control and channel devices
                        UpdateDevice(4, 1, str(self.tvControl))
                        UpdateDevice(5, 1, str(self.tvChannel))

                    else:
                        Domoticz.Debug("No information from TV received (TV was paused and then continued playing from disk)")
                elif (isinstance(results[0],list)):
                    for result in results[0]:
                        if ('target' in result):
                            if (result['target'] == 'headphone'):
                                self.tvVolume = result['volume']
                                if self.tvVolume != None: UpdateDevice(2, 2, str(self.tvVolume))
                else:
                    Domoticz.Debug("Warning: onMessage event but unknown message type!")
                    DumpHTTPResponseToLog(Data)
            elif ('error' in resp):
                Domoticz.Debug("Remote device returned error: ")
                error = resp.get('error')
                Domoticz.Debug("Error code "+str(error[0])+": "+str(error[1]))            
            else:
                Domoticz.Debug("Warning: onMessage event but no known content in data!")
                DumpHTTPResponseToLog(Data)
        elif (Data['Headers']['Content-Type'] == 'text/xml; charset="utf-8"'):
            #DumpHTTPResponseToLog(Data)
            # TODO : Parse XML to verify IRCC command received correctly
            Domoticz.Debug("Remote command received")
            
        return True

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onHeartbeat(self):
        if (self.HttpConn.Connected()):
            if (self.outstandingPings > 6):
                self.HttpConn.Disconnect()
                self.nextConnect = 0
            else:
                _tv.get_power_status()
                self.outstandingPings = self.outstandingPings + 1
        else:
            self.outstandingPings = 0
            self.HttpConn.Connect()

        return
        
    def onStop(self):
        Domoticz.Debug("onStop called")
        return True

    def TurnOn(self):

        return

    def TurnOff(self):

        return
    def GetTVInfo(self):
        self._getState = "TVInfo"
        _tv.get_playing_info()

    def SyncDevices(self):
        # TV is off
        if self.powerOn == False:
            if self.tvPlaying == "TV starting":         # TV is booting and not yet responding to get_power_status
                UpdateDevice(7, 1, self.tvPlaying)
                UpdateDevice(3, 1, self.tvSource)
            else:                                       # TV is off so set devices to off
                self.tvPlaying = "Off"
                self.ClearDevices()
        # TV is on
        else:
            if self.tvPlaying == "Off":                 # TV is set to off in Domoticz, but self.powerOn is still true
                self.ClearDevices()
            else:                                       # TV is on so set devices to on
                if not self.tvPlaying:
                    Domoticz.Debug("No information from TV received (TV was paused and then continued playing from disk) - SyncDevices")
                else:
                    UpdateDevice(7, 1, self.tvPlaying)
                    UpdateDevice(3, 1, str(self.tvSource))
                if Parameters["Mode3"] == "Volume": 
                    UpdateDevice(2, 2, str(self.tvVolume))
                
                UpdateDevice(4, 1, str(self.tvControl))
                UpdateDevice(5, 1, str(self.tvChannel))

        return
    
    def ClearDevices(self):
        self.tvPlaying = "Off"
        UpdateDevice(7, 0, self.tvPlaying)
        UpdateDevice(1, 0, self.tvPlaying)          #Status
        if Parameters["Mode3"] == "Volume": UpdateDevice(2, 0, str(self.tvVolume))  #Volume
        self.tvSource = 0
        self.tvControl = 0
        self.tvChannel = 0
        UpdateDevice(3, 0, str(self.tvSource))      #Source
        UpdateDevice(4, 0, str(self.tvControl))     #Control
        UpdateDevice(5, 0, str(self.tvChannel))     #Channel
        
        return

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Settings count: " + str(len(Settings)))
    for x in Settings:
        Domoticz.Debug( "'" + x + "':'" + str(Settings[x]) + "'")
    Domoticz.Debug("Image count: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug( "'" + x + "':'" + str(Images[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Image:     " + str(Devices[x].Image))
    return
 
def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        #if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
        Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
    else:
        Domoticz.Debug("### Warning: "+str(Unit)+" not found in devices")
    return

def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Debug("HTTP Details ("+str(len(httpDict))+"):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Debug("--->'"+x+" ("+str(len(httpDict[x]))+"):")
                for y in httpDict[x]:
                    Domoticz.Debug("------->'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Debug("--->'" + x + "':'" + str(httpDict[x]) + "'")