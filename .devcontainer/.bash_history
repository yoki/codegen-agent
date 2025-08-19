cd /workspaces/synapse/
uv pip compile requirements.in -o requirements.txt
uv pip sync requirements.txt --system
jupyter lab --NotebookApp.token='' --NotebookApp.password='' --notebook-dir='/workspaces/synapse/working'
pip install -e /workspaces/synapse/src/data-agency
