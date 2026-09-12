# TnVenv

Create a Python virtual environment — batteries included. Running bare 'tn-venv' creates ./.venv with sensible defaults.

```bash
tn-venv                          # create ./.venv with pip, current Python
tn-venv .venv -p 3.12            # pick a specific interpreter version
tn-venv /tmp/x --system-site-packages
tn-venv --with requests -r dev-requirements.txt
tn-venv --setuptools --wheel --pip latest --upgrade-pip
tn-venv --no-pip --activators powershell,batch
tn-venv --list-pythons           # show every interpreter tn-venv can find
```
