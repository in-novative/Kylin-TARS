cd "$(dirname "$0")"
export PYTHONPATH=$PWD:$PYTHONPATH
dbus-run-session -- bash -c '
    python -m mcp_server.mcp_server &
    sleep 1
    python -m mcp_client.mcp_client
'