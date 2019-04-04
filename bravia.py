try:
    import Domoticz
except ImportError:
    import fakeDomoticz as Domoticz

import logging
import base64
import collections
import json
import socket
import struct

from datetime import datetime
import time
import sys

class BraviaRC:
    httpConn = None

    def __init__(self, connection, host, psk, mac=None):
        self.httpConn = connection
        self._host = host
        self._psk = psk
        self._mac = mac
        self._cookies = None
        self._commands = []

    def _jdata_build(self, method, params):
        if params:
            ret = json.dumps({"method": method, "params": [params], "id": 1, "version": "1.0"})
        else:
            ret = json.dumps({"method": method, "params": [], "id": 1, "version": "1.0"})
        print(ret)
        return ret

    def printconf(self):
        Domoticz.Debug("Host: "+str(self._host)+" PSK: "+self._psk);
        if (self.httpConn):
            if (self.httpConn.Connected()):
                Domoticz.Log("Connected successfully to: "+self.httpConn.Name+" "+self.httpConn.Address+":"+self.httpConn.Port)
            else:
                Domoticz.Debug("No connection!")
        else:
            Domoticz.Debug("No instance!")

    def send_req_ircc(self, code):
        """Send an IRCC command via HTTP to Sony Bravia."""
        if (self.httpConn.Connected()):
            headers = { 'X-Auth-PSK': self._psk, 'Soapaction': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"', \
                        'Host': self._host, 'Content-Type': 'application/x-www-form-urlencoded' } # 'Connection': 'close'
            data = ("<?xml version=\"1.0\"?><s:Envelope xmlns:s=\"http://schemas.xmlsoap.org" +
                "/soap/envelope/\" " +
                "s:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\"><s:Body>" +
                "<u:X_SendIRCC " +
                "xmlns:u=\"urn:schemas-sony-com:service:IRCC:1\"><IRCCCode>" +
                code+"</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>")
            try:
                self.httpConn.Send({"Verb":"POST", "URL":"/sony/IRCC", "Headers": headers, "Data": data})
                return true
            except Exception as exception_instance:
                Domoticz.Debug("[bravia_send_req_ircc] Exception: " + str(exception_instance))
                return false
        else:
            Domoticz.Debug("No connection...")
        return false
        
    def bravia_req_json(self, url, params, log_errors=True):
        """Send request command via HTTP json to Sony Bravia."""
        if (self.httpConn.Connected()):
            headers = { 'X-Auth-PSK': self._psk, 'Content-Type': 'application/x-www-form-urlencoded', 'Host': self._host } # 'Connection': 'close' 
            try:
                self.httpConn.Send({"Verb": "POST", "URL": "/"+url, "Headers": headers, "Data": params})
                return true
            except Exception as exception_instance:
                Domoticz.Debug("[bravia_send_req_ircc] Exception: " + str(exception_instance))
                return false
        else:
            Domoticz.Debug("No connection...")
        return false
    
    def send_command(self, command):
        """Sends a command to the TV."""
        self.send_req_ircc(self.get_command_code(command))
        
    def get_source(self, source):
        return true
    #    """Returns list of Sources."""
    #    original_content_list = []
    #    content_index = 0
    #    while True:
    #        resp = self.bravia_req_json("sony/avContent",
    #                                    self._jdata_build("getContentList", {"source": source, "stIdx": content_index}))
    #        if not resp.get('error'):
    #            if len(resp.get('result')[0]) == 0:
    #                break
    #            else:
    #                content_index = resp.get('result')[0][-1]['index']+1
    #            original_content_list.extend(resp.get('result')[0])
    #        else:
    #            break
    #    return original_content_list

    def load_source_list(self):
        return true
    #    """Load source list from Sony Bravia."""
    #    original_content_list = []
    #    resp = self.bravia_req_json("sony/avContent",
    #                                self._jdata_build("getSourceList", {"scheme": "tv"}))
    #    if not resp.get('error'):
    #        results = resp.get('result')[0]
    #        for result in results:
    #            if result['source'] in ['tv:dvbc', 'tv:dvbt']:  # tv:dvbc = via cable, tv:dvbt = via DTT
    #                original_content_list.extend(self.get_source(result['source']))

    #    resp = self.bravia_req_json("sony/avContent",
    #                                self._jdata_build("getSourceList", {"scheme": "extInput"}))
    #    if not resp.get('error'):
    #        results = resp.get('result')[0]
    #        for result in results:
    #            if result['source'] == 'extInput:hdmi':  # hdmi input
    #            ###if result['source'] in ('extInput:hdmi', 'extInput:composite', 'extInput:component'):  # physical inputs
    #            ###new version, see https://github.com/aparraga/braviarc/commit/d9d26b802ffd669bae40f26160689173b0ce77c8
    #                resp = self.bravia_req_json("sony/avContent",
    #                                            self._jdata_build("getContentList", {"source": "extInput:hdmi"}))
    #                                            ###self._jdata_build("getContentList", result))
    #                if not resp.get('error'):
    #                    original_content_list.extend(resp.get('result')[0])

    #    return_value = collections.OrderedDict()
    #    for content_item in original_content_list:
    #        return_value[content_item['title']] = content_item['uri']
    #    return return_value

    def get_playing_info(self):
        """Get information on program that is shown on TV."""
        if (self.httpConn.Connected()):
            if (self.bravia_req_json("sony/avContent", self._jdata_build("getPlayingContentInfo", None))):
                return true
        return false
    #    return_value = {}
    #    resp = self.bravia_req_json("sony/avContent", self._jdata_build("getPlayingContentInfo", None))
        
    #    if resp is not None and not resp.get('error'):
    #        playing_content_data = resp.get('result')[0]
    #        return_value['programTitle'] = playing_content_data.get('programTitle')
    #        return_value['title'] = playing_content_data.get('title')
    #        return_value['programMediaType'] = playing_content_data.get('programMediaType')
    #        return_value['dispNum'] = playing_content_data.get('dispNum')
    #        return_value['source'] = playing_content_data.get('source')
    #        return_value['uri'] = playing_content_data.get('uri')
    #        return_value['durationSec'] = playing_content_data.get('durationSec')
    #        return_value['startDateTime'] = playing_content_data.get('startDateTime')
    #    return return_value

    def get_power_status(self):
        """Get power status: off, active, standby."""
        if (self.httpConn.Connected()):
            if(self.bravia_req_json("sony/system", self._jdata_build("getPowerStatus", None), False)):
                return true
        return false
    #    return_value = 'off' # by default the TV is turned off
    #    try:
    #        resp = self.bravia_req_json("sony/system", self._jdata_build("getPowerStatus", None), False)
    #        if resp is not None and not resp.get('error'):
    #            power_data = resp.get('result')[0]
    #            return_value = power_data.get('status')
    #    except:  # pylint: disable=broad-except
    #        pass
    #    return return_value

    def _refresh_commands(self):
        if (self.httpConn.Connected()):
            if (self.bravia_req_json("sony/system", self._jdata_build("getRemoteControllerInfo", None))):
                return true
        return false
        #resp = 
        """if not resp.get('error'):
            self._commands = resp.get('result')[1]
        else:
            Domoticz.Debug("[bravia_refresh_commands] JSON request error: " + json.dumps(resp, indent=4))"""

    def set_commands(self, commands):
        self._commands = commands
            
    def get_command_code(self, command_name):
        if len(self._commands) == 0:
            self._refresh_commands()
        for command_data in self._commands:
            if command_data.get('name') == command_name:
                return command_data.get('value')
        return None

    def get_volume_info(self):
        """Get volume info."""
        #resp = 
        return self.bravia_req_json("sony/audio", self._jdata_build("getVolumeInformation", None))
        """if not resp.get('error'):
            results = resp.get('result')[0]
            for result in results:
                if result.get('target') == 'speaker':
                    return result
        else:
            Domoticz.Debug("[get_volume_info] JSON request error:" + json.dumps(resp, indent=4))
        return None"""
        
    def get_system_info(self):
        #return_value = {}
        #resp = 
        return self.bravia_req_json("sony/system", self._jdata_build("getSystemInformation", None))
        """if resp is not None and not resp.get('error'):
            #print('=>', resp, '<=')
            system_content_data = resp.get('result')[0]
            return_value['product'] = system_content_data.get('product')
            return_value['region'] = system_content_data.get('region')
            return_value['language'] = system_content_data.get('language')
            return_value['model'] = system_content_data.get('model')
            return_value['serial'] = system_content_data.get('serial')
            return_value['macAddr'] = system_content_data.get('macAddr')
            return_value['name'] = system_content_data.get('name')
            return_value['generation'] = system_content_data.get('generation')
            return_value['area'] = system_content_data.get('area')
            return_value['cid'] = system_content_data.get('cid')
        return return_value"""

    def get_network_info(self):
        """Not available in newer sony Bravia TVs, get_system_info will return MAC"""
        #return_value = {}
        #resp = 
        return self.bravia_req_json("sony/system", self._jdata_build("getNetworkSettings", None))
        """if resp is not None and not resp.get('error'):
            #print('=>', resp, '<=')
            network_content_data = resp.get('result')[0]
            print("ddf")
            return_value['mac'] = network_content_data[0]['hwAddr']
            return_value['ip'] = network_content_data[0]['ipAddrV4']
            return_value['gateway'] = network_content_data[0]['gateway']
        return return_value"""
        
    def set_volume_level(self, volume):
        """Set volume level, range 0..100."""
        self.bravia_req_json("sony/audio", self._jdata_build("setAudioVolume", {"target": "speaker",
                                                                                "volume": volume}))    
    def turn_on_WOL(self):
        """Turn the media player on using WOL."""
        self._wakeonlan()
        
    def turn_on_command(self):
        """Turn the media player on using command. Only confirmed working on Android, can be used when WOL is not available."""
        #if self.get_power_status() != 'active':
        #self.send_req_ircc(self.get_command_code('TvPower'))
        self.send_req_ircc("AAAAAQAAAAEAAAAVAw==")
        #self.bravia_req_json("sony/system", self._jdata_build("setPowerStatus", {"status": "true"}))
            
    def turn_on(self):
        """Normal turn on"""
        self.turn_on_command()
        
    def turn_off(self):
        """Turn off media player."""
        #self.send_req_ircc(self.get_command_code('PowerOff'))
        self.send_req_ircc("AAAAAQAAAAEAAAAvAw==")
    def volume_up(self):
        """Volume up the media player."""
        #self.send_req_ircc(self.get_command_code('VolumeUp'))
        self.send_req_ircc("AAAAAQAAAAEAAAASAw==")

    def volume_down(self):
        """Volume down media player."""
        #self.send_req_ircc(self.get_command_code('VolumeDown'))
        self.send_req_ircc("AAAAAQAAAAEAAAATAw==")

    def mute_volume(self): #--> def mute_volume(self, mute):
        """Send mute command."""
        #self.send_req_ircc(self.get_command_code('Mute'))
        self.send_req_ircc("AAAAAQAAAAEAAAAUAw==")

    def select_source(self, source):
        """Set the input source."""
        if source in self._content_mapping:
            uri = self._content_mapping[source]
            self.play_content(uri)

    def play_content(self, uri):
        """Play content by URI."""
        self.bravia_req_json("sony/avContent", self._jdata_build("setPlayContent", {"uri": uri}))

    def media_play(self):
        """Send play command."""
        #self.send_req_ircc(self.get_command_code('Play'))
        self.send_req_ircc("AAAAAgAAAJcAAAAaAw==")

    def media_pause(self):
        """Send media pause command to media player."""
        #self.send_req_ircc(self.get_command_code('Pause'))
        self.send_req_ircc("AAAAAgAAAJcAAAAZAw==")
        
    def media_tv_pause(self):
        """Send media pause command to TV."""
        #self.send_req_ircc(self.get_command_code('TvPause'))
        # Non existent
        
    def media_stop(self):
        """Send stopcommand to media player."""
        #self.send_req_ircc(self.get_command_code('Stop'))
        self.send_req_ircc("AAAAAgAAAJcAAAAYAw==")

    def media_next_track(self):
        """Send next track command."""
        #self.send_req_ircc(self.get_command_code('Next'))
        self.send_req_ircc("AAAAAgAAAJcAAAA9Aw==")

    def media_previous_track(self):
        """Send the previous track command."""
        #self.send_req_ircc(self.get_command_code('Prev'))
        self.send_req_ircc("AAAAAgAAAJcAAAA8Aw==")
        
    def calc_time(self, *times):
        """Calculate the sum of times, value is returned in HH:MM."""
        totalSecs = 0
        for tm in times:
            timeParts = [int(s) for s in tm.split(':')]
            totalSecs += (timeParts[0] * 60 + timeParts[1]) * 60 + timeParts[2]
        totalSecs, sec = divmod(totalSecs, 60)
        hr, min = divmod(totalSecs, 60)
        if hr >= 24: #set 24:10 to 00:10
            hr -= 24
        return ("%02d:%02d" % (hr, min))
    
    def playing_time(self, startDateTime, durationSec):
        """Give starttime, endtime and percentage played."""
        #get starttime (2017-03-24T00:00:00+0100) and calculate endtime with duration (secs)
        date_format = "%Y-%m-%dT%H:%M:%S"
        try:
            playingtime = datetime.now() - datetime.strptime(startDateTime[:-5], date_format)
        except TypeError:
            #https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
            #playingtime = datetime.now() - datetime.fromtimestamp(time.mktime(time.strptime(startDateTime[:-5], date_format)))
            playingtime = datetime.now() - datetime(*(time.strptime(startDateTime[:-5], date_format)[0:6]))
        try:
            starttime = datetime.time(datetime.strptime(startDateTime[:-5], date_format))
        except TypeError:
            #starttime = datetime.time(datetime.fromtimestamp(time.mktime(time.strptime(startDateTime[:-5], date_format))))
            starttime = datetime.time(datetime(*(time.strptime(startDateTime[:-5], date_format)[0:6])))
        
        duration = time.strftime('%H:%M:%S', time.gmtime(durationSec))
        endtime = self.calc_time(str(starttime), str(duration))
        starttime = starttime.strftime('%H:%M')
        #print(playingtime.seconds, tvplaying['durationSec'])
        perc_playingtime = int(round(((playingtime.seconds / durationSec) * 100),0))
        return str(starttime), str(endtime), str(perc_playingtime)
        
    def send_testpacket(self):
        """Sends a test packet to verify functionality of Domoticz Connection / Send"""
        if(self.httpConn.Connected()):
            headers = { 'X-Auth-PSK': 'sony', \
                        'Content-Type': 'application/x-www-form-urlencoded', \
                        'Host': '192.168.0.20' }
            content = '{"params": [], "id": 1, "method": "getRemoteControllerInfo", "version": "1.0"}'
            #getPowerStatus
            #getSystemInformation
            try:
                self.httpConn.Send({"Verb": "POST", "URL": "/sony/system", "Headers": headers, "Data": content})
            except Exception as exception_instance:
                Domoticz.Debug("[bravia_send_req_ircc] Exception: " + str(exception_instance))
        else:
            Domoticz.Debug("No connection...");