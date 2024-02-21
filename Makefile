pipsetup:
	python3 -m venv venv
	venv/bin/pip install -r requirements.txt

do:
	venv/bin/python3 gort.py