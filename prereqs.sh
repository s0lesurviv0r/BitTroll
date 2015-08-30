if hash apt-get 2>/dev/null; then
    if hash sudo 2>/dev/null; then
      sudo apt-get update
      sudo apt-get install python-libtorrent python-pip python-mysqldb python-flask python-requests python-tornado python-bcode
    fi
elif hash yum 2>/dev/null; then
      sudo yum update
      sudo yum install python-pip
      sudo yum install python-libtorrent-rasterbar
      sudo pip install flask
      sudo pip install tornado
      sudo pip install requests
      sudo pip install bcode
elif hash brew 2>/dev/null; then
      brew update
      brew install boost --build-from-source --with-python
    	brew install libtorrent-rasterbar --enable-python-binding --with-python --with-boost-python=mt
      sudo pip install flask
      sudo pip install tornado
      sudo pip install requests
      sudo pip install bcode
fi
