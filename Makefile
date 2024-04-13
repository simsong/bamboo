# Makefile for Planttracer web application
# - Creates CI/CD environment in GitHub
# - Manages deployemnt to AWS Linux
# - Updated to handle virtual environment.

PYLINT_FILES=$(shell /bin/ls *.py  | grep -v bottle.py | grep -v app_wsgi.py)
PYLINT_THRESHOLD=9.5

################################################################
# Manage the virtual environment
A   = . venv/bin/activate
REQ = venv/pyvenv.cfg
PY=python3.12
PYTHON=$(A) ; $(PY)
PIP_INSTALL=$(PYTHON) -m pip install --no-warn-script-location
venv/pyvenv.cfg:
	$(PY) -m venv venv

venv:
	$(PY) -m venv venv

################################################################
#

# By default, PYLINT generates an error if your code does not rank 10.0.
# This makes us tolerant of minor problems.

all:
	@echo verify syntax and then restart
	make pylint
	make touch

check:
	make pylint
	make pytest

touch:
	touch tmp/restart.txt

pylint: $(REQ)
	$(PYTHON) -m pylint --rcfile .pylintrc --fail-under=$(PYLINT_THRESHOLD) --verbose $(PYLINT_FILES)

freeze:
	$(PYTHON) -m pip freeze > requirements.txt

clean:
	find . -name '*~' -exec rm {} \;
	/bin/rm -rf __pycache__ */__pycache__


eslint:
	(cd static;make eslint)

pytest:
	$(PYTHON) -m pytest bamboo/tests

pytest-debug:
	$(PYTHON) -m pytest -v --log-cli-level=DEBUG

pytest-debug1:
	@echo run in debug mode but stop on first error
	$(PYTHON) -m pytest -v --log-cli-level=DEBUG --maxfail=1

debug:
	$(PYTHON) flask --app flask_app run --debug


################################################################
# Installations are used by the CI pipeline:
# Generic:
install-python-dependencies: $(REQ)
	$(PYTHON) -m pip install --upgrade pip
	if [ -r requirements.txt ]; then $(PIP_INSTALL) -r requirements.txt ; else echo no requirements.txt ; fi

install-chromium-browser-ubuntu: $(REQ)
	sudo apt-get install -y chromium-browser
	chromium --version

install-chromium-browser-macos: $(REQ)
	brew install chromium --no-quarantine

# Includes ubuntu dependencies
install-linux: $(REQ)
	echo on GitHub, we use this action instead: https://github.com/marketplace/actions/setup-ffmpeg
	which ffmpeg || sudo apt install ffmpeg
	$(PYTHON) -m pip install --upgrade pip
	if [ -r requirements-linux.txt ]; then $(PIP_INSTALL) -r requirements-linux.txt ; else echo no requirements-linux.txt ; fi
	if [ -r requirements.txt ];        then $(PIP_INSTALL) -r requirements.txt ; else echo no requirements.txt ; fi

# Includes MacOS dependencies managed through Brew
install-macos:
	brew update
	brew upgrade
	brew install python3
	brew install ffmpeg
	$(PYTHON) -m pip install --upgrade pip
	if [ -r requirements-macos.txt ]; then $(PIP_INSTALL) -r requirements-macos.txt ; else echo no requirements-macos.txt ; fi
	if [ -r requirements.txt ];       then $(PIP_INSTALL) -r requirements.txt ; else echo no requirements.txt ; fi

# Includes Windows dependencies
install-windows:
	$(PYTHON) -m pip install --upgrade pip
	if [ -r requirements-windows.txt ]; then $(PIP_INSTALL) -r requirements-windows.txt ; else echo no requirements-windows.txt ; fi
	if [ -r requirements.txt ];         then $(PIP_INSTALL) -r requirements.txt ; else echo no requirements.txt ; fi


create_localdb:
	@echo Creating local database, exercise the upgrade code and write credentials to etc/credentials.ini using etc/github_actions_mysql_rootconfig.ini
	$(PYTHON) dbmaint.py --create_client=$$MYSQL_ROOT_PASSWORD                 --writeconfig etc/github_actions_mysql_rootconfig.ini
	$(PYTHON) dbmaint.py --rootconfig etc/github_actions_mysql_rootconfig.ini  --createdb actions_test --schema etc/schema_0.sql --writeconfig etc/credentials.ini
	$(PYTHON) dbmaint.py --rootconfig etc/github_actions_mysql_rootconfig.ini  --upgradedb actions_test --loglevel DEBUG
	$(PYTHON) -m pytest -x --log-cli-level=DEBUG tests/dbreader_test.py

remove_localdb:
	@echo Removing local database using etc/github_actions_mysql_rootconfig.ini
	$(PYTHON) dbmaint.py --rootconfig etc/github_actions_mysql_rootconfig.ini --dropdb actions_test --writeconfig etc/credentials.ini
	/bin/rm -f etc/credentials.ini

coverage:
	$(PYTHON) -m pip install --upgrade pip
	$(PIP_INSTALL) codecov pytest pytest_cov
	$(PYTHON) -m pytest -v --cov=. --cov-report=xml tests
