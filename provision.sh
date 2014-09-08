#!/bin/sh

perl -pi -e "s/br/us/" /etc/apt/sources.list

apt-get update
apt-get upgrade -y

apt-get install -y postgresql python-psycopg2 python-dev

su postgres -c 'createdb vagrant'
