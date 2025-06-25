#!/bin/bash
cd /home/kavia/workspace/code-generation/voiceguard-113624-e5a37375/voice_monitor_dashboard_workspace/voice_monitor_dashboard
npm run build
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
   exit 1
fi

