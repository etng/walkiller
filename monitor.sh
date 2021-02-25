#!/bin/bash -e
echo "proxy monitor started"
while :
do
    echo "proxy checking at port ${POLIPO_PORT}"
    curl -x http://127.0.0.1:${POLIPO_PORT} http://ip.fm
    if [ $? -ne 0 ];
    then
        echo "proxy down trying restart"
        pkill ss-local
        pkill polipo
        sleep 5
        curl -x http://127.0.0.1:${POLIPO_PORT} http://ip.fm
        if [ $? -ne 0 ];
        then
            echo "fuck, no ok"
            curl -X POST https://sc.ftqq.com/${SC_KEY}.send --form "text=主人：项目代理挂啦${POLIPO_PORT}" --form "desp=代理挂啦${POLIPO_PORT}"
        else
            echo "proxy back online now"
        fi
    else
    echo "proxy feels good"
    fi
    sleep 120
done
echo "proxy monitor exited"
