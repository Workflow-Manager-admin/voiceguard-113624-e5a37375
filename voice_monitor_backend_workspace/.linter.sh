#!/bin/bash
cd /home/kavia/workspace/code-generation/voiceguard-113624-e5a37375/voice_monitor_backend_workspace/voice_monitor_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

