| Package&nbsp;name | Supported&nbsp;targets |
| :--- | :--- |
| zrancid | el8, el9 |
<br/>

## Build:

The package can be built easily using the rpmbuild-docker script provided
in this repository. In order to use this script, _**a functional Docker
environment is needed**_, with ability to pull Rocky Linux (el9) images
from internet if not already downloaded.

```
$ ./rpmbuild-docker -d el8
$ ./rpmbuild-docker -d el9
```

## Prebuilt packages:

Builds of these packages are available on ZENETYS yum repositories:<br/>
https://packages.zenetys.com/latest/redhat/

## Setup:

**Requirements**

```
# dnf -y install epel-release
# crb enable

# cd /etc/yum.repos.d
# curl -OL https://packages.zenetys.com/latest/redhat/zenetys.repo
```

The zrancid package, as is, will most likely not work with SELinux enforcing, make sure it is disabled or permissive.

**Installation**

```
# dnf --setopt install_weak_deps=False install zrancid
```

**Usage**

To obtain a _zrancid_ shell when logged in as root, you may issue the following command:

```
# su - zrancid
```

**Provisioning**

First step is to add cloginrc templates so that RANCiD scripts can connect to devices. Those files are stored in the ~/etc/cloginrc/ directory. The content is basically [RANCiD cloginrc format](https://shrubbery.net/rancid/man/cloginrc.5.html) without the hostname field; see also ssh/telnet [cloginrc samples](./share) in zrancid share directory.

Example:

```
zrancid$ cat > ./etc/cloginrc/cisco.demo <<"EOF"
add user admin
add password "pass-ignored-use-my-ssh-key"
add method ssh
add sshcmd zrancid-ssh
add autoenable 1
EOF
```

If any SSH client configuration should be done, do it as usual in ~/.ssh/ (key, config).

Second step is to add devices. This can be done manually using the zrancid-add script, which is given a device name, a RANCiD type, a cloginrc template, an IP address and a potential jump host. Availaible RANCiD types are listed in `zrancid-add --help` output; prefer to use z-* types maintained by the zrancid project.

Example:

```
zrancid$ zrancid-add sw-core-01.demo z-cisco-ios ~/etc/cloginrc/cisco.demo 10.0.1.21
```

As well as provsionning RANCiD router.db, a per-device directory is created by zrancid-add, eg: ~/etc/hosts/sw-core-01.demo. Custom device cloginrc directives may be added in a cloginrc.local file to override the template; as opposed to add, reset can be used to remove a previous option.

**Testing**

Note: In the following zrancid-* commands, the argument is actually a regex pattern; the first matching device name is used in the case of zrancid-login.

Make sure you can get an interactive shell on the device:

```
zrancid$ zrancid-login sw-core-01.demo
```

Test executing commands on the device:

```
zrancid$ zrancid-exec sw-core-01.demo 'show int status'
```

Test and dump RANCiD output for the device:

```
zrancid$ zrancid-test sw-core-01.demo
```

Run backup for the device and store the result in Git:

```
zrancid$ zrancid-run sw-core-01.demo
```

**Misc**

This RPM package provides an easy way to deploy (z)RANCiD. You may also have a look at the [zrancid](https://github.com/zenetys/zrancid) project repository, which includes some [documentation](https://github.com/zenetys/zrancid/tree/master/doc). Most of it is covered here or done by the package.

Note regarding the documentation from the project's repository:

* the dedicated user is rancid instead of zrancid here;
* RANCiD types brought by zrancid are automatically installed and updated by the package;
* YaNA integration is just a matter of activating it (see below).

## YaNA integration:

See [zenetys/rpm-yana](https://github.com/zenetys/rpm-yana#setup) for YaNA installation.

In YaNA, an entity is like a zone, a site, a company branch or a customer from a service provider point of view; it is a way to organize scans. For proper integration in YaNA, devices must use the same hostname as displayed in the inventory, in lowercase without domain, then use the YaNA entity as domain.

Example:

* In YaNA, entity demo, ...
* switch with hostname SW-CORE-01.acme.corp is listed in the inventory.
* (z)RANCiD device name should be _sw-core-01.demo_

**Ttyd server**

Enable the ttyd server:

```
# systemctl restart zrancid-ttyd
# systemctl enable zrancid-ttyd
```

**Web server**

Here is a quick way of getting started using apache to serve the (z)RANCiD API and to access devices via ttyd:

```
# ln -s /opt/zrancid/share/zrancid.httpd.conf /etc/httpd/conf.d/60-zrancid.conf
# ln -s /opt/zrancid/share/zrancid-ttyd.httpd.conf /etc/httpd/conf.d/60-zrancid-ttyd.conf
# htpasswd -c -5 /etc/httpd/auth.htpasswd admin
# chmod 400 /etc/httpd/auth.htpasswd
# chown apache:root /etc/httpd/auth.htpasswd

# cat > /etc/httpd/conf.d/65-auth.conf <<"EOF"
RewriteEngine On
RewriteCond %{HTTPS} !=on
RewriteCond %{REMOTE_ADDR} !=127.0.0.1
RewriteRule (.*) https://%{HTTP_HOST}$1 [R=302,L]
<Location />
    AuthType basic
    AuthName "Authentification required"
    AuthBasicProvider file
    AuthUserFile /etc/httpd/auth.htpasswd
    Require valid-user
    RequestHeader set X-Remote-User expr=%{REMOTE_USER}
</Location>
EOF

# systemctl restart httpd
# systemctl enable httpd
```

**Web interface**

Edit `/etc/yana/yana-wui.json` to set the following configuration properties:

```
{
    [...]
    "BACKUP_ENABLED": true,
    "BACKUP_API_BASE_URL": "/zrancid",
    "TTYD_ENABLED": true,
    "TTYD_URL": "/zrancid/ttyd"
}
```

After refreshing YaNA web interface, the "Backups" menu entry gets added and two flag icons appear in front of devices registered in (z)RANCiD: the first gives quick access to RANCiD backups of the device, the other opens a terminal in a popup for remote access to the device.

A demo of YaNA integrating (z)RANCiD is available at https://tools.zenetys.com/yana. It includes backups of network devices and remote access via [ttyd](https://github.com/tsl0922/ttyd).
