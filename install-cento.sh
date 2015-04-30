#!/bin/sh

yum update
yum upgrade -y

echo "install deps"
yum install -y postgresql libpq-dev python-dev python-pip python-virtualenv httpd

echo "Add database"
service postgresql start

echo "Add database"
su postgres -c 'createdb vagrant'
su postgres -c 'createuser -dRS vagrant'

echo "Add vagrant user"

adduser vagrant

if [ ! -e env ] ; then
    su vagrant -c 'virtualenv ~/env'
fi
su vagrant -c '~/env/bin/pip install -r `pwd`/requirements.txt'
