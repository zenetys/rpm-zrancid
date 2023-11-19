# Supported targets: el9

%{!?zrancid_version: %define zrancid_version 1.0.0}
#define zrancid_revision 1234567

%define zenetys_git_source() %{lua:
    local version_source = 'https://github.com/zenetys/%s/archive/refs/tags/v%s.tar.gz#/%s-%s.tar.gz'
    local revision_source = 'http://git.zenetys.loc/data/projects/%s.git/snapshot/%s.tar.gz#/%s-%s.tar.gz'
    local name = rpm.expand("%{1}")
    local iname = name:gsub("%W", "_")
    local version = rpm.expand("%{"..iname.."_version}")
    local revision = rpm.expand("%{?"..iname.."_revision}")
    if revision == '' then print(version_source:format(name, version, name, version))
    else print(revision_source:format(name, revision, name, revision)) end
}

Name: zrancid
Version: %{zrancid_version}
Release: 1%{?zrancid_revision:.git%{zrancid_revision}}%{?dist}.zenetys
Summary: (z)RANCiD, scripts to play with... RANCiD
Group: Applications/System
License: MIT
URL: https://github.com/zenetys/zrancid

Source0: %zenetys_git_source zrancid

# zrancid
Source10: zrancid.cron
Source11: zrancid.httpd
Source12: apache-zrancid.sudoers

# zrancid-ttyd
Source50: zrancid-ttyd.httpd
Source51: zrancid-ttyd.service
Source52: zrancid-ttyd.tmpfiles
Source53: zrancid-ttyd-handler
Source54: zrancid-ttyd-zrancid.sudoers

BuildArch: noarch

# zrancid-ttyd
# standard
BuildRequires: systemd

# zrancid
# standard
Requires(post): git
Requires:       openssh-clients
Requires:       sudo
Requires:       telnet
Requires(post): util-linux
%if 0%{?rhel} >= 9
Requires:       util-linux-core
%endif
# epel
Requires:       perl(Hash::Merge::Simple)
Requires(pre):  rancid

# zrancid-ttyd
# zenetys
Requires:       ttyd

%description
(z)RANCiD is a set of helper scripts for RANCiD.

%prep
%setup -c -T

mkdir zrancid
tar xvzf %{SOURCE0} --strip-components 1 -C zrancid

%install
# zrancid
install -d -m 0755 %{buildroot}/opt
cp -RT zrancid %{buildroot}/opt/zrancid

install -D -m 0644 %{SOURCE10} %{buildroot}/%{_sysconfdir}/cron.d/zrancid
install -D -m 0644 %{SOURCE11} %{buildroot}/opt/zrancid/share/zrancid.httpd.conf
install -D -m 0400 %{SOURCE12} %{buildroot}/%{_sysconfdir}/sudoers.d/apache-zrancid

install -d -m 0700 %{buildroot}/%{_localstatedir}/lib/zrancid

# zrancid-ttyd
install -D -m 0644 %{SOURCE50} %{buildroot}/opt/zrancid/share/zrancid-ttyd.httpd.conf
install -D -m 0644 %{SOURCE51} %{buildroot}/%{_unitdir}/zrancid-ttyd.service
install -D -m 0644 %{SOURCE52} %{buildroot}/%{_tmpfilesdir}/zrancid-ttyd.conf
install -D -m 0755 %{SOURCE53} %{buildroot}/%{_datadir}/zrancid-ttyd/zrancid-ttyd-handler
install -D -m 0400 %{SOURCE54} %{buildroot}/%{_sysconfdir}/sudoers.d/zrancid-ttyd-zrancid

%pre
# zrancid
if ! getent group zrancid >/dev/null; then
    groupadd -r zrancid
fi
if ! getent passwd zrancid >/dev/null; then
    useradd -r -g zrancid -G rancid -d %{_localstatedir}/lib/zrancid \
        -s /bin/bash zrancid
fi

# zrancid-ttyd
if ! getent group zrancid-ttyd >/dev/null; then
    groupadd -r zrancid-ttyd
fi
if ! getent passwd zrancid-ttyd >/dev/null; then
    useradd -r -g zrancid-ttyd -d %{_datadir}/zrancid-ttyd \
        -s /sbin/nologin zrancid-ttyd
fi

%post
# zrancid
su - zrancid -c $'
set -xe
umask 0027
if ! [ -f ~/.bashrc ]; then
    cp /etc/skel/.bash{rc,_profile} ~/
    cat >> ~/.bashrc <<"EOF"
umask 0027
export PATH="$PATH:/opt/zrancid/bin"
source ~/.bash.zrancid
alias cp="cp -iv"
alias mv="mv -iv"
alias rm="rm -iv"
alias rmdir="rmdir -v"
EOF
fi
if ! [ -f ~/.bash.zrancid ]; then
    cat >> ~/.bash.zrancid <<"EOF"
# NOTE: This file is sourced both bash ~/.bashrc for interactive shells and
# NOTE: by $ZRANCID_ETC_DIR/zrancid.conf for zrancid scripts

# Legacy ssh support, eg: sha1; see also /opt/zrancid/share/ssh-legacy.ssh.conf
#export OPENSSL_CONF=/opt/zrancid/share/ssh-legacy.openssl-rh-crypto.conf
EOF
fi
mkdir -p ~/etc/{auto,cloginrc,hosts}
mkdir -p ~/data{,/logs}
if ! [ -f ~/etc/rancid.conf ]; then
    /opt/zrancid/share/fork-rancid-conf > ~/etc/rancid.conf
fi
if ! [ -f ~/etc/zrancid.conf ]; then
    cat > ~/etc/zrancid.conf <<"EOF"
source ~/.bash.zrancid
export YANA_BASEURL=http://127.0.0.1:4444
export YANA_CURL_OPTIONS="-x \x27\x27"
EOF
fi
if ! [ -d ~/data/default ]; then
    rancid-cvs -f ~/etc/rancid.conf default
    ln -s /opt/zrancid/lib/pre-commit-hook ~/data/default/.git/hooks/pre-commit
fi
mkdir -p -m 0700 ~/.ssh
if ! [ -f ~/.ssh/config ]; then
    cat > ~/.ssh/config <<"EOF"
Host *
    KexAlgorithms +diffie-hellman-group14-sha1,diffie-hellman-group1-sha1
EOF
fi
'
# update /etc/rancid/rancid.types.conf
/opt/zrancid/share/register-types

# zrancid-ttyd
%systemd_post zrancid-ttyd.service

%preun
# zrancid-ttyd
%systemd_preun zrancid-ttyd.service

%postun
# zrancid-ttyd
%systemd_postun_with_restart zrancid-ttyd.service

%triggerin -- rancid
if [ $1 -eq 1 -a $2 -eq 1 ]; then
    echo 'zrancid: Disabling /etc/cron.d/rancid tasks by default.'
    sed -i -e 's,^,# ,' /etc/cron.d/rancid || true
fi

%posttrans
cat <<"EOF"
%{name}: Note this RPM does not require httpd; sample apache configurations
%{name}: are available in /opt/zrancid/share/zrancid{,-ttyd}.httpd.conf.

%{name}: Due to RH default crypto policy, if legacy ssh support is needed
%{name}: (eg: sha1) and you do not want to change the global crypto policy
%{name}: (man update-crypto-policies), you can set an OPENSSL_CONF variable
%{name}: in environment and add some configuration in ~/.ssh/config. Put the
%{name}: environment variable in ~/.bash.zrancid so it applies both to
%{name}: interactive shells and zrancid scripts.
%{name}: See comments in ~/.bash.zrancid and the following files for more:
%{name}: - /opt/zrancid/share/ssh-legacy.openssl-rh-crypto.conf
%{name}: - /opt/zrancid/share/ssh-legacy.ssh.conf
EOF

%files
# zrancid
%config(noreplace) %{_sysconfdir}/cron.d/zrancid
%{_sysconfdir}/sudoers.d/apache-zrancid
/opt/zrancid
%attr(-, zrancid, zrancid) %{_localstatedir}/lib/zrancid

# zrancid-ttyd
%{_sysconfdir}/sudoers.d/zrancid-ttyd-zrancid
%{_datadir}/zrancid-ttyd
%{_unitdir}/zrancid-ttyd.service
%{_tmpfilesdir}/zrancid-ttyd.conf
