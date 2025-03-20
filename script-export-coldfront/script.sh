#!/bin/bash

#this script has to be launched via crontab.
#you need 3 files in the same directory: clusters, ldapserver, storage
#each file must contains:
#hostname ip ssh_user ssh_password

# Variabili configurabili
quota_size="10000"  # Sostituisci XXXX con il valore desiderato in mb
home_server_ip="XX.XX.XX.XX" #ricordati di copiare la chiave pubblica ssh su questo server

# quota default per beegfs se non definita in fs/disk su coldfront
default_fs_disk=20000  # Quota predefinita in MB

# Define the Docker container name
container_name="coldfront"

# Define the output directory inside the container
output_dir="/opt/coldfront/coldfront_dump"

# Run the coldfront slurm_dump command inside the Docker container
docker exec "${container_name}" coldfront slurm_dump -o "${output_dir}"

# Check if the command was successful
if [[ $? -eq 0 ]]; then
    echo "The slurm_dump command executed successfully."
else
    echo "Error: The slurm_dump command failed."
fi

# Ottieni la data e l'ora attuali nel formato desiderato (YYYYMMDD_HHMM)
current_time=$(date +'%Y%m%d_%H%M')
current_date=$(date +'%Y%m%d')

# Percorso dove sono salvati i file .cfg
dump_dir="${output_dir}/coldfront_dump_${current_time}"

# Funzione per eseguire SCP per copiare il file .cfg
copy_cfg_file() {
    local ip=$1
    local username=$2
    local password=$3
    local cfg_file=$4

    # Copia il file .cfg sul server remoto
    sshpass -p "${password}" scp -o "StrictHostKeyChecking=no" "${cfg_file}" "${username}@${ip}:/tmp/"
}

# Funzione per eseguire SSH e caricare il file .cfg con sacctmgr
load_cfg_with_sacctmgr() {
    local ip=$1
    local username=$2
    local password=$3
    local cfg_file=$4

    # Carica il file .cfg con sacctmgr
    sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "echo 'y' | sacctmgr load /tmp/$(basename ${cfg_file})"
}

# Funzione per eseguire sacctmgr dump e copiare il file dump
dump_and_copy_file() {
    local ip=$1
    local username=$2
    local password=$3
    local cluster=$4

    # Nome del file di dump da creare
    local dump_file="/tmp/${cluster}_dump_data_${current_date}.cfg"

    # Esegui sacctmgr dump sul cluster remoto
    sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "sacctmgr dump ${cluster} file=${dump_file}"

    # Copia il file dump dal server remoto al server locale
    sshpass -p "${password}" scp -o "StrictHostKeyChecking=no" "${username}@${ip}:${dump_file}" "${dump_file}"
}

# Funzione per estrarre solo i comandi sacctmgr dall'output di coldfront slurm_check
extract_sacctmgr_commands() {
    local cluster=$1

    coldfront slurm_check -i "/tmp/${cluster}_dump_data_${current_date}.cfg" -s -n 2>&1 | grep "NOOP - Slurm cmd: /usr/bin/" | sed 's/^NOOP - Slurm cmd: \/usr\/bin\///' |
    while IFS= read -r line; do
        echo "$line"
        execute_sacctmgr_commands "$ip" "$username" "$password" "$line"
    done
}

# Funzione per eseguire i comandi sacctmgr su un cluster remoto
execute_sacctmgr_commands() {
    local ip=$1
    local username=$2
    local password=$3
    shift 3  # Shift per rimuovere ip, username, password e ottenere solo i comandi

    echo "Esecuzione dei comandi sacctmgr su $ip"

    # Itera su ogni comando passato come argomento
    for cmd in "$@"; do
        echo "Singolo comando nel for: ${cmd}"
        # Esegui il comando con sshpass e ssh
        sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "$cmd"

        # Controlla lo stato di uscita del comando
        if [[ $? -eq 0 ]]; then
            echo "Comando \"$cmd\" eseguito con successo su $ip"
        else
            echo "Errore durante l'esecuzione del comando \"$cmd\" su $ip"
            # Puoi decidere di gestire eventuali errori qui
        fi
    done
}

# Funzione per verificare se il percorso esiste su un server remoto
check_path_on_storage() {
    local ip=$1
    local username=$2
    local password=$3
    local path=$4

    sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "[[ -d $path ]] && echo 'Path $path exists on $ip' || echo 'Path $path does not exist on $ip'"
}

# Funzione per gestire le directory e i gruppi degli account
manage_account_directories_and_groups() {
    local ip=$1
    local username=$2
    local password=$3
    local account=$4
    local users=$5

    echo "Connettendosi a ${ip} con utente ${username} per gestire l'account ${account}..."

    # Sostituzione delle variabili esterne al comando SSH
    local ssh_command=$(cat <<EOF

        # Controlla se l'account è 'root'
        if [[ "${account}" == "root" ]]; then
            echo "Skipping account 'root' and its users."
            exit 0
        fi


        # Controlla se ci sono utenti 'root' nell'elenco
        if echo "${users}" | grep -qw "root"; then
            echo "Skipping users 'root' for account ${account}."
            users=$(echo "${users}" | grep -vw "root")
        fi

        echo "Verifica se la directory /mnt/beegfs/proj/${account} esiste..."
        if [[ ! -d "/mnt/beegfs/proj/${account}" ]]; then
            echo "La directory /mnt/beegfs/proj/${account} non esiste. Creazione in corso..."
            mkdir "/mnt/beegfs/proj/${account}"
            echo "Creata cartella /mnt/beegfs/proj/${account})"
        else
            echo "La directory /mnt/beegfs/proj/${account} esiste già."
        fi


        echo "Verifica se il gruppo ${account} esiste..."
        if ! getent group "${account}" > /dev/null 2>&1; then
            echo "Il gruppo ${account} non esiste. Creazione in corso..."
            #groupadd "${account}"
            echo  "faccio group add ${account}; group commit"
            cmsh -c "group add ${account}; group commit"
            echo "Creato gruppo ${account}"
        else
            echo "Il gruppo ${account} esiste già."
        fi

        echo "Verifica della ownership della cartella /mnt/beegfs/proj/${account}..."
        ####if [[ \$(stat -c %G "/mnt/beegfs/proj/${account}") != "${account}" ]]; then
            echo "Aggiornamento della ownership della cartella /mnt/beegfs/proj/${account} al gruppo ${account}..."
            chown :${account} "/mnt/beegfs/proj/${account}"
            chmod g+wrs,o-rwx "/mnt/beegfs/proj/${account}"
            echo "Aggiornata ownership della cartella /mnt/beegfs/proj/${account} al gruppo ${account}"
        ####fi
        echo "**********************************************"
        echo "Verifica per cancellazione degli utenti del gruppo ${account}..."
        echo "**********************************************"
        current_users=\$(getent group "${account}" | cut -d':' -f4 | sed "s/,/ /g")
        if [[ -n "\${current_users}" ]]; then
            echo "current_users = \${current_users}"
            for user in \${current_users}; do
                echo "utente ciclo =\$user utenti del progetto  = ${users} utenti del gruppo linux = \${current_users}"
                if ! echo "${users}" | grep -qw "\${user}"; then
                    echo "Rimozione dell'utente \${user} dal gruppo ${account}..."
                    # gpasswd -d "\${user}" "${account}"
                    echo "faccio group removefrom ${account} members \${user}; group commit"
                    cmsh -c "group removefrom ${account} members \${user}; group commit"
                    echo "Rimosso utente \${user} dal gruppo ${account}"
                fi
            done
        fi

        echo "**********************************************"
        echo "Aggiunta degli utenti ${users} al gruppo ${account}..."
        echo "**********************************************"
        utenti="${users}"
        for user in ${users}; do
            echo "ecco utente \${user} ... di ${users}"
           if id -nG "\${user}" ; then 
            if ! id -nG "\${user}" | grep -qw "${account}"; then
                echo "Aggiunta dell utente \${user} al gruppo ${account}..."
                #usermod -aG "${account}" "\${user}"
                echo "faccio group append ${account} members \${user}; group commit"
                cmsh -c "group append ${account} members \${user}; group commit"
                echo "Aggiunto utente \${user} al gruppo ${account}"
            fi
           fi 
        done
        echo "...lancio il comando..."
EOF
)

###echo "[command]\n ${ssh_command}" >> /tmp/scripts-command.log

    # Esecuzione del comando SSH con il comando costruito
    sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "${ssh_command}"
}

# Funzione per controllare i file di configurazione e gestire directory e gruppi
check_clusters_and_cfg_files() {
    for cfg_file in "${dump_dir}"/*.cfg; do
        file_name=$(basename "${cfg_file}" .cfg)
        if [[ -n ${hosts_map[$file_name]} ]]; then
            echo "Contenuto del file di configurazione ${cfg_file}:"
            cat "${cfg_file}"

            declare -A account_users_map
            while IFS= read -r line; do
                if [[ $line == Account* ]]; then
                    account=$(echo "$line" | grep -oP "(?<=Account - ')[^']+")
                    fs_disk=$(echo "$line" | grep -oP "(?<=fs/disk=)[^:]+")
                    account_users_map["$account"]=""
                    if [[ -n $fs_disk ]]; then
                        echo "Account: $account, Quota storage (fs/disk): $fs_disk"
                    else
                        echo "Account: $account, Quota storage (fs/disk): non definita"
                    fi
                elif [[ $line == Parent* ]]; then
                    parent=$(echo "$line" | grep -oP "(?<=Parent - ')[^']+")
                elif [[ $line == User* ]]; then
                    user=$(echo "$line" | grep -oP "(?<=User - ')[^']+")
                    if [[ -n ${account_users_map[$parent]} ]]; then
                        account_users_map["$parent"]="${account_users_map[$parent]} $user"
                    else
                        account_users_map["$parent"]="$user"
                    fi
                fi
            done < "${cfg_file}"

            for account in "${!account_users_map[@]}"; do
                users=${account_users_map[$account]}
                if [[ -n $users ]]; then
                    echo "Account: $account, Users: $users"
                    ####manage_account_directories_and_groups "${storage_map["ip"]}" "${storage_map["username"]}" "${storage_map["password"]}" "$account" "$users"
                    manage_account_directories_and_groups "${ldap_map["ip"]}" "${ldap_map["username"]}" "${ldap_map["password"]}" "$account" "$users"
                fi
            done

        else
            echo "Nessuna corrispondenza trovata per $file_name nel file hosts"
        fi
    done
}


# Funzione per controllare i file di configurazione e gestire directory e gruppi
check_users_for_quotas() {
    for cfg_file in "${dump_dir}"/*.cfg; do
        file_name=$(basename "${cfg_file}" .cfg)
        if [[ -n ${hosts_map[$file_name]} ]]; then
            echo "Contenuto del file di configurazione ${cfg_file}:"
            cat "${cfg_file}"

            declare -A account_users_map
#leggo il file intero
            readarray -t linee < ${cfg_file} 
            for line in "${linee[@]}"; do
                if [[ $line == Account* ]]; then
                    account=$(echo "$line" | grep -oP "(?<=Account - ')[^']+")
                    fs_disk=$(echo "$line" | grep -oP "(?<=fs/disk=)[^:]+")
                    account_users_map["$account"]=""
                    if [[ -n $fs_disk ]]; then
                        echo "Account: $account, Quota storage (fs/disk): $fs_disk"
			set_beegfs_quota "${storage_map["ip"]}" "${storage_map["username"]}" "${storage_map["password"]}" "${account}" "${fs_disk}" 
                    else
                        echo "Account: $account, Quota storage (fs/disk): non definita. Defaulting to ${default_fs_disk}MB"
			set_beegfs_quota "${storage_map["ip"]}" "${storage_map["username"]}" "${storage_map["password"]}" "${account}"
                    fi
                elif [[ $line == Parent* ]]; then
                    parent=$(echo "$line" | grep -oP "(?<=Parent - ')[^']+")
                elif [[ $line == User* ]]; then
                    user=$(echo "$line" | grep -oP "(?<=User - ')[^']+")
                    if [[ -n ${account_users_map[$parent]} ]]; then
                        account_users_map["$parent"]="${account_users_map[$parent]} $user"
                    else
                        account_users_map["$parent"]="$user"
                    fi
                fi
            done


            for account in "${!account_users_map[@]}"; do
                users=${account_users_map[$account]}
        	for user in ${users}; do
		    user_id=$(get_user_id  "${storage_map["ip"]}" "${storage_map["username"]}" "${storage_map["password"]}" "$account" "$user")
        	    echo "Id for user ${user} is ${user_id}"
		    set_user_quota_on_remote_server "$home_server_ip" "$user_id" "$quota_size"
		done
            done

        else
            echo "Nessuna corrispondenza trovata per $file_name nel file hosts"
        fi
    done
}

read_ldap_info() {
    while read -r ldap_name ldap_ip ldap_username ldap_password; do
        ldap_map["ip"]=$ldap_ip
        ldap_map["username"]=$ldap_username
        ldap_map["password"]=$ldap_password
    done < /opt/script-export-coldfront/ldapserver
}



read_storage_info() {
    while read -r storage_name storage_ip storage_username storage_password; do
        storage_map["ip"]=$storage_ip
        storage_map["username"]=$storage_username
        storage_map["password"]=$storage_password
    done < /opt/script-export-coldfront/storage
}

# Funzione per recuperare l'ID utente su Linux
get_user_id() {
    local ip=$1
    local username=$2
    local password=$3
    local account=$4
    local user=$5


    # Sostituzione delle variabili esterne al comando SSH
    local ssh_command=$(cat <<EOF

    id -u "$user"

EOF
)

    # Esecuzione del comando SSH con il comando costruito
    sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "${ssh_command}"
}

# Funzione per impostare la quota su un server remoto
set_user_quota_on_remote_server() {
    local remote_ip=$1
    local user_id=$2
    local quota_size=$3

    # Controllo se user_id è vuoto o nullo
    if [[ -z ${user_id} ]]; then
        echo "Errore: user_id non specificato."
        return
    fi

    # Controllo se l'user_id è 'root'
    if [[ ${user_id} == "0" ]]; then
        echo "L'utente 'root' non può avere una quota impostata."
        return
    fi

    echo "Impostazione della quota per l'utente con ID ${user_id} sul server ${remote_ip}..."

    # Costruzione del comando xfs_quota da eseguire sul server remoto
    local remote_command="xfs_quota -x -c 'limit bsoft=${quota_size}m bhard=${quota_size}m isoft=0 ihard=0 ${user_id}' /home"

    # Esecuzione del comando tramite SSH
    echo "Eseguo il comando ${remote_command}"
    ssh -o "StrictHostKeyChecking=no" "${remote_ip}" "${remote_command}"

    # Controllo dell'esito del comando
    if [[ $? -eq 0 ]]; then
        echo "Quota impostata con successo per l'utente con ID ${user_id}."
    else
        echo "Errore durante l'impostazione della quota per l'utente con ID ${user_id}."
    fi
}

# Funzione principale
manage_user_quotas() {
    local remote_ip=$1
    local account_users=$2

    for user in ${account_users}; do
        if [[ "$user" == "root" ]]; then
            echo "Saltando l'utente root..."
            continue
        fi

        user_id=$(get_user_id "$user")
        if [[ -z "$user_id" ]]; then
            echo "Errore: impossibile recuperare l'ID per l'utente ${user}."
            continue
        fi

        echo "Trovato ID ${user_id} per l'utente ${user}."
        set_quota_on_remote_server "$home_server_ip" "$user_id"
    done
}

# Funzione per gestire le quote su BeeGFS
set_beegfs_quota() {
    local ip=$1
    local username=$2
    local password=$3
    local account=$4
    local fs_disk=${5:-$default_fs_disk}  # Usa il valore predefinito se fs_disk non è fornito

    echo "Impostazione della quota BeeGFS per il gruppo linux ${account} a ${fs_disk} MB"

    # Esegui il comando per impostare la quota su BeeGFS
    sshpass -p "${password}" ssh -o "StrictHostKeyChecking=no" "${username}@${ip}" "beegfs-ctl --setquota --gid ${account} --sizelimit=${fs_disk}M  --inodelimit=unlimited --storagepoolid=1"
}

# Leggi il file hosts e crea un array associativo
declare -A hosts_map
while read -r cluster ip username password; do
    hosts_map["$cluster"]=$ip
    hosts_map["${cluster}_username"]=$username
    hosts_map["${cluster}_password"]=$password
done < /opt/script-export-coldfront/clusters



# Esegui il comando coldfront per generare i file .cfg
coldfront slurm_dump -o "${dump_dir}"

# Verifica se esistono file .cfg nella directory
if [[ -n $(find "${dump_dir}" -maxdepth 1 -type f -name '*.cfg') ]]; then
    echo "File .cfg trovati nella directory ${dump_dir}"

    # Itera su tutti i file .cfg nella directory
    for cfg_file in "${dump_dir}"/*.cfg; do
        file_name=$(basename "${cfg_file}" .cfg)
        echo "Analizzando il file $cfg_file"

        # Controlla se il nome del file corrisponde a una voce nel file hosts
        if [[ -n ${hosts_map[$file_name]} ]]; then
            ip=${hosts_map[$file_name]}
            username=${hosts_map["${file_name}_username"]}
            password=${hosts_map["${file_name}_password"]}
            echo "Trovato corrispondenza per $file_name: $ip, username: $username"

            # Copia il file .cfg sul server remoto
            copy_cfg_file "$ip" "$username" "$password" "$cfg_file"

            # Esegui sacctmgr load sul server remoto
            load_cfg_with_sacctmgr "$ip" "$username" "$password" "$cfg_file"

            # Esegui sacctmgr dump e copia il file dump sul server locale
            dump_and_copy_file "$ip" "$username" "$password" "$file_name"

            # Esegui coldfront slurm_check localmente
            extract_sacctmgr_commands "$file_name"
        else
            echo "Nessuna corrispondenza trovata per $file_name nel file hosts"
        fi
    done
else
    echo "Nessun file .cfg trovato nella directory ${dump_dir}"
    exit 1
fi

# Leggi il file storage e verifica il percorso sul server di storage
if [[ -f /opt/script-export-coldfront/storage ]]; then
    while read -r storage_server ip username password; do
        echo "Verifica del percorso su $storage_server ($ip)"
        check_path_on_storage "$ip" "$username" "$password" "/mnt/beegfs/proj"
    done < /opt/script-export-coldfront/storage
else
    echo "File di storage non trovato."
fi

# Leggi le informazioni di storage
declare -A storage_map
read_storage_info

declare -A ldap_map
read_ldap_info


# Verifica corrispondenze tra nomi di cluster e file .cfg
check_clusters_and_cfg_files
check_users_for_quotas 
