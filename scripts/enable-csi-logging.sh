#!/bin/bash
sudo modprobe -r iwldvm
sudo modprobe -r iwlwifi
sudo modprobe -r mac80211
sudo modprobe iwlwifi connector_log=0x1
