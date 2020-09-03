#!/usr/bin/env bash

#This script is usable on an IWL5300 system on which the Linux 802.11n CSI Tool is only partially installed.

sudo modprobe -r iwldvm
sudo modprobe -r iwlwifi
sudo modprobe -r mac80211
sudo modprobe iwlwifi connector_log=0x1
