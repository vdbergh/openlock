#!/bin/bash
# Create stale lock file!

cat <<EOF > test.lock
123
test.py
EOF

python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
python test.py &
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
