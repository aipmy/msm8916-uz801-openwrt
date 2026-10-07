#!/bin/sh
# Modem Status LED Monitor Daemon for MSM8916 (JZ01-45-v33)
# States:
#   - SIM Missing / Error    : Fast Blink Red (100ms)
#   - Searching BTS / Modem  : Slow Blink Green (1000ms)
#   - Registered / Idle      : Solid Green
#   - Connected / Data Flow  : Netdev trigger on wwan0 (Real-time RX/TX activity)

LED_WAN="/sys/class/leds/green:wan"
LED_PWR="/sys/class/leds/red:power"

[ -d "$LED_WAN" ] || exit 0

while true; do
	# Cek status ModemManager
	STATUS=$(mmcli -m 0 --output-keyvalue 2>/dev/null | grep "modem.generic.state " | awk '{print $NF}')
	
	case "$STATUS" in
		"connected")
			CURRENT_TRIG=$(cat "$LED_WAN/trigger" | grep -o '\[.*\]' | tr -d '[]')
			if [ "$CURRENT_TRIG" != "netdev" ]; then
				echo netdev > "$LED_WAN/trigger"
				echo wwan0 > "$LED_WAN/device_name"
				echo 1 > "$LED_WAN/link"
				echo 1 > "$LED_WAN/rx"
				echo 1 > "$LED_WAN/tx"
				echo 1 > "$LED_WAN/brightness"
			fi
			;;
		"registered")
			echo default-on > "$LED_WAN/trigger"
			echo 1 > "$LED_WAN/brightness"
			;;
		"searching"|"enabling")
			echo timer > "$LED_WAN/trigger"
			echo 1000 > "$LED_WAN/delay_on"
			echo 1000 > "$LED_WAN/delay_off"
			;;
		"failed"|"unknown"|"disabled"|*)
			# SIM Error atau Modem Disconnect
			echo none > "$LED_WAN/trigger"
			echo 0 > "$LED_WAN/brightness"
			if [ -d "$LED_PWR" ]; then
				echo timer > "$LED_PWR/trigger"
				echo 150 > "$LED_PWR/delay_on"
				echo 150 > "$LED_PWR/delay_off"
			fi
			;;
	esac
	sleep 3
done
