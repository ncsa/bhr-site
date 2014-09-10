#!/bin/sh
exec python manage.py test -v 2 bhr.tests.ApiTest.test_all_in_one
