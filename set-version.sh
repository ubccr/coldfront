#!/bin/bash

echo `git describe --tags 2>/dev/null || git rev-parse --short HEAD` > VERSION
