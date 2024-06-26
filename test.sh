# Create stale lock file!
# touch test.lock

python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &

sleep 4

python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &

sleep 5

# Exactly one python process should be running!
ps waux |grep python |grep test.py

wait
