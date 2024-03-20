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

clean:
	find . -name '*~' -exec rm {} \;
	/bin/rm -rf __pycache__ */__pycache__


eslint:
	(cd static;make eslint)


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
