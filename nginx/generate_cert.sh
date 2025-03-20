#!/bin/bash

# Configura i nomi
PREFIX="coldfront"
DOMAIN=".hpc"

# Chiave privata e certificato della CA (non necessario per un certificato auto-firmato semplice)
openssl genrsa -out server.key 2048

# Genera il certificato SSL auto-firmato
openssl req -new -x509 -days 365 -key server.key -subj "/C=IT/ST=IT/L=LZ/O=$PREFIX Acme/CN=$PREFIX$DOMAIN" -out server.crt

# Opzionale: verifica il certificato generato
openssl x509 -in server.crt -text -noout
