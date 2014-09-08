#!/bin/sh

perl -pi -e "s/br/us/" /etc/apt/sources.list
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get upgrade -y

apt-get install -y postgresql python-psycopg2 python-dev python-pip python-virtualenv

su postgres -c 'createdb vagrant'
su postgres -c 'createuser -DRS vagrant'

if [ ! -e env ] ; then
    su vagrant -c 'virtualenv ~/env'
fi
su vagrant -c '~/env/bin/pip install -r /vagrant/requirements.txt'
