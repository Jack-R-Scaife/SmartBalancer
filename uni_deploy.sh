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

    # Ensure agent folder exists
    if [ ! -d "$TEMP_DIR/repo/$AGENT_FOLDER" ]; then
        echo "Error: '$AGENT_FOLDER' does not exist in the repository!"
        exit 1
    fi

    # Copy agent folder to the temporary directory
    cp -r "$TEMP_DIR/repo/$AGENT_FOLDER" "$TEMP_DIR/agent"

    # Verify the copy was successful
    if [ ! "$(ls -A $TEMP_DIR/agent)" ]; then
        echo "Error: Agent folder is empty after copying!"
        exit 1
    fi

    # Clean up repository clone
    rm -rf "$TEMP_DIR/repo"
}

deploy_to_backend() {
    echo "Deploying agent to backend servers..."
    for vm in "${BACKEND_VMS[@]}"; do
        echo "Processing $vm..."
        
        USERNAME=$(echo "$vm" | cut -d '@' -f 1)
        PASSWORD=$USERNAME

        # Copy the `agent` folder
        sshpass -p "$PASSWORD" rsync -avz "$TEMP_DIR/agent" "$vm:~/"

        # Set up environment and service
        sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -t "$vm" "
            sudo apt update && sudo apt install -y python3 python3-venv git &&
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
ExecStart=/home/$USERNAME/agent/venv/bin/python /home/$USERNAME/agent/agent_script.py
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

    # Copy repo to load balancer
    sshpass -p "$PASSWORD" rsync -avz --exclude "$AGENT_FOLDER" "$TEMP_DIR/agent" "$LB_VM:~/SmartBalancer"

    # Set up environment
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
