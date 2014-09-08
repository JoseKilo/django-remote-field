#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='django_remote_field',
    version='1.0.3',
    author='rockabox',
    author_email='tech@rockabox.com',
    packages=['remotefields'],
    include_package_data=True,
    url='https://github.com/rockabox/django-remote-field',
    license='MIT',
    description='Django Remote Field',
    classifiers=[
        'Development Status :: 2 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'Django>=1.6.5',
        'djangorestframework>=2.3.13'
    ],
)
