#!/bin/bash
echo "$(date) proxy monitor started"
while :
do
    echo "$(date) proxy checking at port ${POLIPO_PORT}"
    curl -x http://127.0.0.1:${POLIPO_PORT} http://ip.fm --fail
    if [ $? -ne 0 ];
    then
        echo "$(date) proxy down trying restart"
        pkill ss-local
        pkill polipo
        sleep 5
        curl -x http://127.0.0.1:${POLIPO_PORT} http://ip.fm --fail
        if [ $? -ne 0 ];
        then
            echo "$(date) fuck, no ok"
            curl -X POST https://sc.ftqq.com/${SC_KEY}.send --form "text=主人：项目代理挂啦${POLIPO_PORT}" --form "desp=代理挂啦${POLIPO_PORT} ${SS_METHOD}://${SS_PASSWORD}@${SS_SERVER}:${SS_SERVER_PORT}"
        else
            echo "$(date) proxy back online now"
        fi
    else
    echo "$(date) proxy feels good"
    fi
    sleep 120
done
echo "$(date) proxy monitor exited"
