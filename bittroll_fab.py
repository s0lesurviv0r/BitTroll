from fabric.api import *

# This fabric script allows installing/managing multiple BitTroll instances using Fabric
# See for more details on Fabric: http://www.fabfile.org/

def install():
	sudo('apt-get update')
	sudo('apt-get install git')
	run('git clone https://github.com/jacobzelek/bittroll.git')
	sudo('bittroll/prereqs.sh')

def update():
	run('cd bittroll; git pull')

# @fixme Doesn't work
@parallel
def start():
	run('cd bittroll; ./start.sh')

@parallel
def stop():
	run('bittroll/stop.sh')

def show_logs():
	run('cd bittroll; tail -100 output.log')

def version():
	run('cd bittroll; git log -n 1 --pretty=format:"%H"')
