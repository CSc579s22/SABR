#!/bin/bash

USER="<usr>"
KEY_NAME="<ssh_key_filename>"  # The path is handled in the loop - only do the name
PORT_NUMBER=22
CLIENT_IPS=<<client IP address list>>

counter=0
for ip in $CLIENT_IPS
do
    mkdir dash_runtime${counter}
    scp -i ~/.ssh/${KEY_NAME} -P ${PORT_NUMBER} ${USER}@${ip}:/users/${USER}/astream_dash_bolao/ASTREAM_LOGS/DASH_RUNTIME_LOG_* dash_runtime${counter}/
    mkdir dash_buffer$(COUNTER)
    scp -i ~/.ssh/${KEY_NAME} -P ${PORT_NUMBER} ${USER}@${ip}:/users/${USER}/astream_dash_bolao/ASTREAM_LOGS/DASH_BUFFER_LOG_* dash_buffer${counter}/
    mkdir server_log$(COUNTER)
    scp -i ~/.ssh/${KEY_NAME} -P ${PORT_NUMBER} ${USER}@${ip}:/users/${USER}/astream_dash_bolao/ASTREAM_LOGS/SERVER_LOG_* server_log${counter}/
    counter=$((counter+1))
done
