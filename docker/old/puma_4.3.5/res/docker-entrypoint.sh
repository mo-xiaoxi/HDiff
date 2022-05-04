echo fs.inotify.max_user_watches=524288 | tee -a /etc/sysctl.conf && sysctl -p
if [ $? -eq 0 ]; then
	exec "$@"
else
	echo "Error: You need to run this image in privileged mode."
fi
