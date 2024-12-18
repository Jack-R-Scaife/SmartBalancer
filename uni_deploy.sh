#!/bin/bash

# Variables
GITHUB_REPO="https://github.com/Jack-R-Scaife/SmartBalancer.git"
BACKEND_VMS=("ubs1@192.168.1.3" "ubs2@192.168.1.4" "ubs3@192.168.1.5" "ubs4@192.168.1.6" "ubs5@192.168.1.7")
LB_VM="lb@192.168.1.2"
AGENT_FOLDER="agent"
REQUIREMENTS_FILE_BACKEND="requirements.txt"
REQUIREMENTS_FILE_LB="requirements.txt"

# Functions
deploy_to_backend() {
    echo "Deploying agent to backend servers..."
    for vm in "${BACKEND_VMS[@]}"; do
        echo "Processing $vm..."
        
        ssh "$vm" "sudo apt update && sudo apt install -y python3 python3-venv git"
        ssh "$vm" "rm -rf ~/SmartBalancer && git clone $GITHUB_REPO ~/SmartBalancer"
        
        # Copy agent folder and set up environment
        ssh "$vm" "python3 -m venv ~/SmartBalancer/${AGENT_FOLDER}/venv && source ~/SmartBalancer/${AGENT_FOLDER}/venv/bin/activate && pip install -r ~/SmartBalancer/${AGENT_FOLDER}/${REQUIREMENTS_FILE_BACKEND}"
        
        # Set up agent as a systemd service
        ssh "$vm" "cat << EOF | sudo tee /etc/systemd/system/agent.service
[Unit]
Description=SmartBalancer Agent Service
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/SmartBalancer/${AGENT_FOLDER}
ExecStart=/home/$USER/SmartBalancer/${AGENT_FOLDER}/venv/bin/python /home/$USER/SmartBalancer/${AGENT_FOLDER}/agent_script.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF"
        ssh "$vm" "sudo systemctl daemon-reload && sudo systemctl enable agent.service && sudo systemctl start agent.service"
        echo "Deployment to $vm completed."
    done
}

deploy_to_lb() {
    echo "Deploying to load balancer server..."
    
    ssh "$LB_VM" "sudo apt update && sudo apt install -y python3 python3-venv git"
    ssh "$LB_VM" "rm -rf ~/SmartBalancer && git clone $GITHUB_REPO ~/SmartBalancer"
    
    # Remove agent folder and set up environment
    ssh "$LB_VM" "rm -rf ~/SmartBalancer/${AGENT_FOLDER}"
    ssh "$LB_VM" "python3 -m venv ~/SmartBalancer/venv && source ~/SmartBalancer/venv/bin/activate && pip install -r ~/SmartBalancer/${REQUIREMENTS_FILE_LB}"
    
    echo "Deployment to load balancer completed."
}

# Main
echo "Starting deployment process..."
deploy_to_backend
deploy_to_lb
echo "Deployment process completed successfully!"
