#!/bin/sh -ex

REMOTE=bhr@bhr-sec

function test() {
    Echo "Testing.."
    ./test 
}

function setup() {
    ssh $REMOTE '[ -d bhr_env/bin ] || virtualenv --system-site-packages -p python2.7 bhr_env' 
}

function upload() {
    echo "Uploading.."
    rsync --exclude '*settings_local.py' -a . ${REMOTE}:bhr_project/
}

function install() {
    ssh $REMOTE 'bhr_env/bin/pip install -r bhr_project/requirements.txt'
}

function migrate() {
    ssh -t $REMOTE 'cd bhr_project; ~/bhr_env/bin/python manage.py syncdb'
    ssh -t $REMOTE 'cd bhr_project; ~/bhr_env/bin/python manage.py migrate'
    ssh -t $REMOTE 'cd bhr_project; ~/bhr_env/bin/python manage.py collectstatic --noinput'
}

function reload() {
    ssh $REMOTE 'touch bhr_project/bhr_site/wsgi.py'
}

function deploy () {
    #test
    setup
    upload
    install
    migrate
    reload
}

deploy
