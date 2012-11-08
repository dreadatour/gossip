%define __prefix /usr/local

Summary:       Log files proccessing
Name:          gossip
Version:       0.1
Release:       1%{?dist}
License:       Apache Software License 2.0
Group:         MAILRU
Prefix:        %{_prefix}
BuildRoot:     %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:     x86_64

Url:           https://github.com/dreadatour/gossip

BuildRequires: python2.7
BuildRequires: python2.7-devel

Requires:      python2.7


%description
Log files proccessing


%prep
if [ -d %{buildroot}%{__prefix}/%{name} ];
then
    echo "Cleaning out stale build directory" 1>&2
    %{__rm} -rf %{buildroot}%{__prefix}/%{name}
fi


%build
# creating virtual environment
virtualenv --distribute %{buildroot}%{__prefix}/%{name}

# create directory for source files
mkdir %{buildroot}%{__prefix}/%{name}/src

# clone repository with source files
git clone git://github.com/dreadatour/gossip.git %{buildroot}%{__prefix}/%{name}/src/%{name}

# remove git-files
rm -rf %{buildroot}%{__prefix}/%{name}/src/%{name}/.git*

# install requirements
%{buildroot}%{__prefix}/%{name}/bin/pip install -r %{buildroot}%{__prefix}/%{name}/src/%{name}/requirements/base.txt

# install gossip into virtualenv
pushd %{buildroot}%{__prefix}/%{name}/src/%{name}/
%{buildroot}%{__prefix}/%{name}/bin/python setup.py install
popd

# do not include *.pyc in rpm
find %{buildroot}%{__prefix}/%{name}/ -type f -name "*.py[co]" -delete

# fix python path
find %{buildroot}%{__prefix}/%{name}/ -type f \
    -exec sed -i 's:'%{buildroot}'::' {} \;


%install
# init.d file
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/%{name}/src/%{name}/contrib/gossip.init %{buildroot}%{_initrddir}/%{name}

# chmod binaries
chmod +x %{buildroot}%{__prefix}/%{name}/bin/*

# compile py files
%{buildroot}%{__prefix}/%{name}/bin/python -m compileall -qf %{buildroot}%{__prefix}/%{name}/


%post
# create config file if not exists
if [ ! -f %{__prefix}/%{name}/etc/gossip.conf ]; then
	mkdir -p %{__prefix}/%{name}/etc/
    cp %{__prefix}/%{name}/src/%{name}/contrib/gossip.conf %{__prefix}/%{name}/etc/gossip.conf
fi

ldconfig

# registering services
if [ $1 -eq 1 ];
then
    /sbin/chkconfig --add %{name}
fi


%clean
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root,-)
%{_initrddir}/%{name}
%{__prefix}/%{name}/
