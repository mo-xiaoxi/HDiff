#	Introduction for Weblogic Setup

##	On your host

1. First, build a weblogic docker.

   ```bash
   docker build -t weblogic .
   docker create --name=weblogic -p 20022:22 -p 7001:7001 weblogic
   docker start weblogic
   ```

2. Download jdk and weblogic core.

   JDK: We use jdk-8u311-linux-x64.tar.gz for test

   Weblogic: We use fmw_12.2.1.4.0_wls_quick.jar for test

3. Clone these files into your docker.

   ```bash
   docker cp ./jdk-8u311-linux-x64.tar.gz weblogic:/home/ubuntu/jdk/
   docker cp ./fmw_12.2.1.4.0_wls_quick.jar weblogic:/home/ubuntu/weblogic/
   ```

   

##	On the docker container

1. Use ssh to login your docker container. The password is `toor`.

   ```
   ssh -p 20022 ubuntu@127.0.0.1
   ```

2. Decompress your jdk files.

   ```
   cd jdk && tar -zxvf jdk-8u311-linux-x64.tar.gz
   ```

3. Append environment variables for java into your profile file and then use `source .profile` to reload.

   ```
   export JAVA_HOME=/home/ubuntu/jdk/jdk1.8.0_311
   export JRE_HOME=$JAVA_HOME/jre
   export PATH=$PATH:$JAVA_HOME/bin:$JRE_HOME/bin
   ```

4. Install weblogic.

   ```
   cd ~/weblogic && java -jar fmw_12.2.1.4.0_wls_quick.jar
   ```

5. Wait for weblocgic installation complete.

6. Create your domain.

   ```
   ~/weblogic/wls12214/oracle_common/common/bin/wlst.sh ~/base_domain/createDomain.py
   ```

7. Start Weblogic.

   ```
   cd ~/base_domain && nohup ./startWebLogic.sh &
   ```

8. Visit the admin page at http://localhost:7001/console. Use `weblogic/moxiaoxi.666` to login as admin.
9. Click the "Deployment" on the left side and then click the install button. Upload the ROOT.war then install it.
10. Visit http://localhost:7001 to check if the whole setup is completed.