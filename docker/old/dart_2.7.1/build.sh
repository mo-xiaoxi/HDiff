if [ ! -f "res/dart_2.7.1-1_amd64.deb" ]; then
	wget https://storage.googleapis.com/dart-archive/channels/stable/release/2.7.1/linux_packages/dart_2.7.1-1_amd64.deb
	mv dart_2.7.1-1_amd64.deb res/
fi
docker build -t dart2_7_1 .
