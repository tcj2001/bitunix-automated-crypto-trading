bash -c "\
apt-get install -y python3.9 python3.9-distutils python3-pip wget unzip dos2unix && \
ln -sf /usr/bin/python3.9 /usr/bin/python3 && \
python3 -m pip install --upgrade pip && \
mkdir bitunix && cd bitunix && \
wget https://github.com/tcj2001/bitunix-automated-crypto-trading/archive/refs/tags/Ver1.0.tar.gz -O bitunix.tar.gz && \
mkdir code && \
tar --strip-components=1 -xvzf bitunix.tar.gz -C code
cd code
pip3 install -r requirements.txt
cp sampleenv .env
"