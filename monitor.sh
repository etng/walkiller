#!/bin/bash
machine=`cat /etc/host_name`
echo "$(date) proxy monitor started"
echo "$(date) ${machine} wait for first check"
sleep 30
while :
do
    echo "$(date) proxy checking at port ${POLIPO_PORT}"
    curl -sSL -x http://127.0.0.1:${POLIPO_PORT} http://ip.fm --fail
    if [ $? -ne 0 ];
    then
        echo "$(date) proxy down trying restart"
        now=`date '+%Y-%m-%d %H:%M:%S'`
        pkill ss-local
        pkill polipo
        sleep 5
        curl -sSL -x http://127.0.0.1:${POLIPO_PORT} http://ip.fm --fail
        if [ $? -ne 0 ];
        then
            echo "$(date) fuck, no ok"
            if [ -n "${SC_KEY}" ]; then
                echo "notify with ftqq"
                curl -sSL -X POST https://sc.ftqq.com/${SC_KEY}.send --form "text=主人：项目代理挂啦${POLIPO_PORT}" --form "desp=${machine} ${now} 代理挂啦${POLIPO_PORT} ${SS_METHOD}://${SS_PASSWORD}@${SS_SERVER}:${SS_SERVER_PORT}"
            fi
            if [ -n "${DINGTALK_TOKEN}" ]; then
                echo "notify with dingding"
                curl -sSL "https://oapi.dingtalk.com/robot/send?access_token=${DINGTALK_TOKEN}" \
                -H 'Content-Type: application/json' \
                -d "{\"msgtype\": \"text\",\"text\": {\"content\": \"${DINGTALK_PREFIX} ${machine} ${now} ${POLIPO_PORT}代理挂啦 ${SS_METHOD}://${SS_PASSWORD}@${SS_SERVER}:${SS_SERVER_PORT}\"}}"
            fi
        else
            echo "$(date) proxy back online now"
        fi
    else
    echo "$(date) proxy feels good"
    fi
    sleep 120
done
echo "$(date) proxy monitor exited"
