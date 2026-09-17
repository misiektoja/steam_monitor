"""Exercise partial setup failures through real wizard and filesystem paths."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

SETUP_SCRIPT = r'''
"""Drive actual sibling setup flows with operator answers and real filesystem faults."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch
root=Path(sys.argv[1]).resolve()
name='steam_monitor'
source=root/(name+".py")
work=Path(sys.argv[2]).resolve()
work.mkdir(parents=True,exist_ok=True)
(work/"config").mkdir(exist_ok=True)
(work/"secrets").mkdir(exist_ok=True)
config=work/"config/monitor.conf"
env=work/"secrets/.env"
env.parent.chmod(0o700)
original="CLEAR_SCREEN=False\n"
config.write_text(original)
env.write_text("SMTP_PASSWORD=synthetic-old\nKEEP=retained\n")
spec=importlib.util.spec_from_file_location(name,source)
gm=importlib.util.module_from_spec(spec)
sys.modules[name]=gm
spec.loader.exec_module(gm)
for key in gm.SECRET_KEYS:os.environ.pop(key,None)
os.chdir(work)
count=0
# Supplies operator decisions without replacing any wizard helper
def answer(prompt=""):
    global count
    count+=1
    if count>100:raise RuntimeError("Unexpected prompt loop")
    text=prompt.lower()
    if "continue without" in text or "rebuild it" in text or "replace" in text and "config" in text:
        result="y"
    elif "webhook" in text and "[y/n]" in text:
        result="y"
    elif "[y/n]" in text:
        result="n" if any(s in text for s in ["email","webhook","doctor","again","authorize","spotify","start monitoring"]) else ""
    else:
        result=""
    print("PROMPT:",prompt,"ANSWER:",repr(result),flush=True)
    return result
# Declines entering authentication during this save-failure scenario
def secret(prompt=""):
    print("SECRET_PROMPT:",prompt,flush=True)
    return "https://discord.com/api/webhooks/123456789/synthetic-test-token" if "url" in prompt.lower() else ""
# Blocks all socket traffic during the offline setup
def offline(*args,**kwargs):
    raise OSError("Network is offline for this scenario")
armed=True
# Makes the secret destination unwritable at the first actual configuration replacement
def fault(event,args):
    global armed
    if armed and event=="os.rename" and Path(args[1])==config:
        armed=False
        env.parent.chmod(0o500)
sys.addaudithook(fault)
kwargs={"config_file":str(config),"env_file":str(env),"input_func":answer,"getpass_func":secret,"interactive":True}
kwargs["initial_target"]="76561201960435530"
try:
    with patch.object(socket.socket,"connect",offline),patch.object(socket.socket,"connect_ex",offline):
        result=gm.run_setup_wizard(**kwargs)
        print("WIZARD_EXIT:",result)
except BaseException as exc:
    print("WIZARD_EXCEPTION:",type(exc).__name__,str(exc))
finally:
    env.parent.chmod(0o700)
    print("FAULT_REACHED:",not armed)
    print("CONFIG_CHANGED:",config.read_text()!=original)
    print("OLD_SECRET_RETAINED:","synthetic-old" in env.read_text())
'''


@pytest.mark.skipif(os.name != "posix", reason="This failure uses POSIX directory permissions")
# Identifies saved configuration and recovery steps after a real dotenv write failure
def test_partial_setup_save_reports_the_saved_configuration(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-c", SETUP_SCRIPT, str(root), str(tmp_path)], cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "FAULT_REACHED: True" in result.stdout
    assert "CONFIG_CHANGED: True" in result.stdout
    assert "OLD_SECRET_RETAINED: True" in result.stdout
    assert "WIZARD_EXIT: 1" in result.stdout
    assert "Configuration was saved to" in result.stdout
    assert "Setup is incomplete and monitoring was not started" in result.stdout
    assert "run --setup again" in result.stdout
