#!/bin/bash

# Variables
GITHUB_REPO="https://github.com/Jack-R-Scaife/SmartBalancer.git"
BACKEND_VMS=("ubs1@192.168.1.3" "ubs2@192.168.1.4" "ubs3@192.168.1.5" "ubs4@192.168.1.6" "ubs5@192.168.1.7")
LB_VM="lb@192.168.1.2"
AGENT_FOLDER="agent"
REQUIREMENTS_FILE_BACKEND="requirements.txt"
REQUIREMENTS_FILE_LB="requirements.txt"
TEMP_DIR="/tmp/smartbalancer"

# Functions
prepare_files() {
    echo "Preparing deployment files..."
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Clone repo locally
    git clone "$GITHUB_REPO" "$TEMP_DIR/repo"

    # Ensure repository was cloned
    if [ ! -d "$TEMP_DIR/repo" ]; then
        echo "Error: Repository clone failed!"
        exit 1
    fi

    # Remove the agent folder from the cloned repository
    rm -rf "$TEMP_DIR/repo/$AGENT_FOLDER"

    # Copy the repository (minus the agent folder) to the temporary directory for the load balancer
    cp -r "$TEMP_DIR/repo/" "$TEMP_DIR/SmartBalancer"

    # Clean up repository clone
    rm -rf "$TEMP_DIR/repo"
}

copy_with_fallback() {
    local src="$1"
    local dest="$2"
    local vm="$3"
    local password="$4"

    echo "Attempting to copy using rsync..."
    sshpass -p "$PASSWORD" rsync -avz -e "ssh -o StrictHostKeyChecking=no" "$src" "$vm:$dest" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "rsync failed. Falling back to scp..."
        sshpass -p "$password" scp -r "$src" "$vm:$dest"
        if [ $? -ne 0 ]; then
            echo "Error: Both rsync and scp failed for $vm."
            exit 1
        fi
    fi
}

deploy_to_backend() {
    echo "Deploying agent to backend servers..."
    for vm in "${BACKEND_VMS[@]}"; do
        echo "Processing $vm..."
        
        USERNAME=$(echo "$vm" | cut -d '@' -f 1)
        PASSWORD=$USERNAME

        # Clean up old directories and service
        sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -t "$vm" "
            sudo systemctl stop agent.service || true &&
            sudo rm -f /etc/systemd/system/agent.service &&
            rm -rf ~/agent
        "

        # Copy the `agent` folder with fallback
        copy_with_fallback "$TEMP_DIR/agent/" "~/agent/" "$vm" "$PASSWORD"

        # Set up environment and service
        sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -t "$vm" "
            sudo apt update && sudo apt install -y python3 python3-venv git rsync &&
            python3 -m venv ~/agent/venv &&
            source ~/agent/venv/bin/activate &&
            pip install -r ~/agent/$REQUIREMENTS_FILE_BACKEND &&
            sudo chown -R $USERNAME:$USERNAME ~/agent &&
            cat << EOF | sudo tee /etc/systemd/system/agent.service
[Unit]
Description=SmartBalancer Agent Service
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=/home/$USERNAME/agent
ExecStart=/home/$USERNAME/agent/venv/bin/python /home/$USERNAME/agent/agent.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
            sudo chmod o+rx /home/$USERNAME &&
            sudo systemctl daemon-reload &&
            sudo systemctl enable agent.service &&
            sudo systemctl start agent.service
        "
        echo "Deployment to $vm completed."
    done
}

deploy_to_lb() {
    echo "Deploying to load balancer server..."
    USERNAME=$(echo "$LB_VM" | cut -d '@' -f 1)
    PASSWORD=$USERNAME

    # Clean up old directories on the load balancer
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -t "$LB_VM" "
        rm -rf ~/SmartBalancer
    "

    # Copy repository excluding the agent folder
    copy_with_fallback "$TEMP_DIR/SmartBalancer/" "~/SmartBalancer/" "$LB_VM" "$PASSWORD"

    # Set up environment on the load balancer
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -t "$LB_VM" "
        sudo apt update && sudo apt install -y python3 python3-venv git &&
        python3 -m venv ~/SmartBalancer/venv &&
        source ~/SmartBalancer/venv/bin/activate &&
        pip install -r ~/SmartBalancer/$REQUIREMENTS_FILE_LB &&
        sudo chown -R $USERNAME:$USERNAME ~/SmartBalancer
    "
    echo "Deployment to load balancer completed."
}

# Main
echo "Starting deployment process..."
prepare_files
deploy_to_backend
deploy_to_lb
echo "Deployment process completed successfully!"
