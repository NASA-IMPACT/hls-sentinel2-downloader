sudo yum update
aws configure set region us-west-2
sudo yum install git -y
sudo yum install python3 -y
sudo yum install -y python3-devel.x86_64
sudo yum install gcc -y

sudo cp /usr/share/zoneinfo/America/Chicago /etc/localtime
export RELEASE=1.35.0
wget https://github.com/aria2/aria2/releases/download/release-$RELEASE/aria2-$RELEASE.tar.gz
tar -xzvf aria2-$RELEASE.tar.gz
sudo yum install gcc-c++ openssl-devel libxml2-devel -y
pushd aria2-$RELEASE
./configure
make -j$(nproc)
sudo make install
popd



