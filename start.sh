FILE=nohup_pid.txt

if test -f "$FILE"; then
    echo "$FILE exist"
    echo "killng existing process"
    pid=$(<$FILE)
    kill -9 $pid
fi
nohup python3 src/main.py > nohup.log 2>&1 &
echo $! > $FILE