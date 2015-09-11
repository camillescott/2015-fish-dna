test: FORCE
	./pipeline -n 4 --resources test/resources.json --config test/config.json --work-dir _test/

list: FORCE
	./pipeline list

FORCE:
