#!/usr/bin/env bash

cd ~

ulimit -n 1048576

# Turn off power mgmt on the wifi
sudo iw wlan0 set power_save off


# Start pinging to keep alive
tmux has-session -t keepalive || (tmux new-session -d -s keepalive; tmux send-keys -t keepalive "~/ping_loop.sh" C-m)

# Start managing the lights
tmux has-session -t lights || (tmux new-session -d -s lights; tmux send-keys -t lights "./start-script.sh lights.py" C-m)

# Start reading the temperature
tmux has-session -t climate || (tmux new-session -d -s climate; tmux send-keys -t climate "./start-script.sh climate.py" C-m)

# Start controlling the fan (see enhanced-fanctl)
tmux has-session -t fanctl || (tmux new-session -d -s fanctl; tmux send-keys -t fanctl "./start-script.sh fan.py" C-m)

# Start the server
tmux has-session -t web || (tmux new-session -d -s web; tmux send-keys -t web "./start-script.sh main.py" C-m)
