#!/bin/bash

USER="<usr>"
KEY_NAME="<ssh_key_filename>"  # The path is handled in the loop - only do the name
PORT_NUMBER=22
CLIENT_IPS=(<<raw client IP address separated by spaces>>)

counter=0
for ip in "${CLIENT_IPS[@]}"
do
    if [ -d "dash_runtime${counter}" ]
    then
        rm -r dash_runtime${counter}
    fi
    if [ -d "dash_buffer${counter}" ]
    then
        rm -r dash_buffer${counter}
    fi
    if [ -d "server_log${counter}" ]
    then
        rm -r server_log${counter}
    fi
    mkdir dash_runtime${counter}
    scp -i ~/.ssh/${KEY_NAME} -P ${PORT_NUMBER} ${USER}@${ip}:/users/${USER}/astream_dash_bolao/ASTREAM_LOGS/DASH_RUNTIME_LOG_* dash_runtime${counter}/
    mkdir dash_buffer${counter}
    scp -i ~/.ssh/${KEY_NAME} -P ${PORT_NUMBER} ${USER}@${ip}:/users/${USER}/astream_dash_bolao/ASTREAM_LOGS/DASH_BUFFER_LOG_* dash_buffer${counter}/
    mkdir server_log${counter}
    scp -i ~/.ssh/${KEY_NAME} -P ${PORT_NUMBER} ${USER}@${ip}:/users/${USER}/astream_dash_bolao/ASTREAM_LOGS/SERVER_LOG_* server_log${counter}/
    counter=$((counter+1))
done
