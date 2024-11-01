# hpc_campaign_connector
SSH tunnel and port forwarding using paramiko.

This is a service that needs to started on the local machine, so that ADIOS can ask for connections to remote hosts, as specified in the remote host configuration. 

Example: `python3 ./hpc_campaign_connector.py -c ~/.config/adios2/hosts.yaml -p  30000`

Note that ADIOS currently looks for this service on fixed port 30000
