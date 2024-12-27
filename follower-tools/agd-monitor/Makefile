
start:
	twistd3 -y agd-monitord.py
run:
	twistd3 -noy agd-monitord.py
stop:
	python3 ./stop.py twistd.pid
restart:
	-$(MAKE) stop
	$(MAKE) start

