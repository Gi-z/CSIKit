#!/usr/bin/env bash

Fs=$(echo "1 / $1" | bc -l)
if [ -z $Fs ]
then
	Fs=0.05
fi

sudo ping -I wlan0 -f -i $Fs 192.168.0.1