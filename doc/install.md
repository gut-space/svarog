[doc](../README.md) > Installation

This system consists of two elements: station (which is intended to run on a Raspberry Pi with an SDR dongle, but can
be run on any Linux box) and a server (which is intended to be run in a place with good uplink connectivity). If
you are interested in running your own station, you most likely want to deploy just the station and use existing
server. Please contact someone from the satnogs team and we'll hook you up.

# Station installation

You need to install [Rasbian](https://www.raspbian.org/) on your Raspberry Pi. Please follow any Raspbian installation
instruction, such as [this one](https://www.raspberrypi.org/documentation/installation/installing-images/). Once
done, connect to your Pi and do the following as root:

1. **Install necessary dependencies**:

```
apt update
apt install python3-minimal git rtl-sdr sox imagemagick
```

Also, the following tools are needed:

1. noaa-apt - download Raspberry Pi binaries from https://noaa-apt.mbernardi.com.ar/download.html
2. medet - https://github.com/artlav/meteor_decoder, binaries available from: http://orbides.org/page.php?id=1023
3. meteor-demod - https://github.com/dbdexter-dev/meteor_demod

4. **Create svarog user (optional) **:

```
# useradd svarog
```

3. Now **switch to the svarog user (optional) **:
```
su - svarog
```

1. **Get the latest svarog code**. This and following steps should be done as the user you want to run
the process:

```
git clone https://github.com/gut-space/svarog
```

1. **Install python dependencies**:

```
cd satnogs/station
python3 setup.py install
```

This step will install necessary dependencies. It is a good practice to install them in virtual environment. However,
since the scripts will be called using crontab, it would've complicated the setup. If there is an exception
complaining about `'install_requires' must be a string or list of strings...`, make sure you have recent pip
version installed. You can update it by `pip install --upgrade pip pip-tools`.

6. **Station management**

There is a command line tool used to manage the station. You can run it with:

```
station/cli.py

usage: svarog [-h] {clear,plan,config} ...

positional arguments:
  {clear,plan,config}  commands
    clear              Clear all schedule receiving
    plan               Schedule planning receiving
    config             Configuration

optional arguments:
  -h, --help           show this help message and exit

```

You can use it to inspect your configuration, clear or schedule upcoming transmissions.

7. **Tweak your config**.

Run the cli command first:
```
python station/cli.py
```

It will create a tempate config for you. The config file is stored in ~/.config/satnogs-gut/config.yml. The recommended way of tweaking it is to use the cli.py command itself. For example, to set up your location, you can do:

```
python station/cli.py config location -lat 54.34 -lng 23.23 -ele 154
```

8. **Schedule observations**

Once your station coordinates are set, you can tell satnogs to schedule observations:

```
python station/cli.py plan --force
```

This should be done once. CLI will update the crontab jobs and will periodically add new ones. The `--force` command will conduct the scheduling now, rather than wait for 4am to do scheduling.

# Server installation

Server installation is a manual process. It is assumed that you already have running apache server. Here are the steps needed to get it up and running.

1. **Get the latest code**

```
git clone https://github.com/gut-space/svarog
```

2. **Install PostgreSQL**:

```
apt install postgresql postgresql-client
su - postgres
psql
CREATE DATABASE svarog;
CREATE USER svarog WITH PASSWORD 'secret'; -- make sure to use an actual password here
GRANT ALL PRIVILEGES ON DATABASE satnogs TO svarog;
```

Make sure to either run `setup.py` or run DB schema migration manually: `python3 migrate_db.py`.

3. **Modify your apache configuration**

The general goal is to have an apache2 running with WSGI scripting capability that runs Flask. See an [example
apache2 configuation](apache2/svarog.conf). You may want to tweak the paths and TLS configuration to use LetsEncrypt
or another certificate of your choice. Make sure the paths are actually pointing to the right directory.

Also, you should update the /etc/sudoers file to allow ordinary user (svarog) to restart apache server.
You should use `visudo` command to add the following line:

```
%svarog ALL= NOPASSWD: /bin/systemctl restart apache2
```

4. **Install Flask dependencies**

```
cd svarog/server
python3 -m virtualenv venv
source venv/bin/activate
python setup.py install
```

Sometimes it's necessary to explicitly say which python version to use: `python3 -m virtualenv --python=python3 venv`

This step will install necessary dependencies. It is a good practice to install them in virtual environment. If you don't have virtualenv
installed, you can add it with `sudo apt install python-virtualenv`
or similar command for your system. Alternatively, you may use venv.
However, make sure the virtual environment is created in venv directory.

You can start flask manually to check if it's working. This is not needed once you have apache integration complete.

```
cd server
./svarog-web.py
```
