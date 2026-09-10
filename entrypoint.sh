#!/bin/sh
echo "[entrypoint] Script to be run: ${SCRIPT}"

# Check if allowed script:
case "$SCRIPT" in
  run_corine_europe_stats_areas.py|run_corine_stats_real_areas.py)
    echo "[entrypoint] Script is allowed!"
    ;;
  *)
    echo "[entrypoint] Script is not allowed!"
    exit 1
    ;;
esac

# Print args, for debugging:
echo "[entrypoint] Args passed to script: ${@}"

# Run python script:
python "/src/${SCRIPT}" "$@"

