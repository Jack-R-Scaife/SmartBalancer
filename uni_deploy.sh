#!/bin/bash

# Variables
GITHUB_REPO="https://github.com/Jack-R-Scaife/SmartBalancer.git"
CLONE_DIR="/tmp/load_balancer_repo"
AGENT_FOLDER="agent"
BACKEND_VMS=("ubs1@192.168.1.3" "ubs2@192.168.1.4" "ubs3@192.168.1.5" "ubs4@192.168.1.6" "ubs5@192.168.1.7")
LB_VM="192.168.1.2"
TARGET_DIR="load_balancer"  # Subdirectory inside the user's home directory

# Exit on error
set -e

# Clone the latest repository
if [ -d "$CLONE_DIR" ]; then
    rm -rf "$CLONE_DIR"
fi
git clone "$GITHUB_REPO" "$CLONE_DIR"

# Set permissions for the cloned directory
chmod -R 755 "$CLONE_DIR"

# Deploy to Backend VMs
for VM in "${BACKEND_VMS[@]}"; do
    echo "Deploying agent to backend VM: $VM"

    # Prepare directories on remote VM
    ssh -t "$VM" << EOF
        set -e
        mkdir -p ~/$TARGET_DIR/$AGENT_FOLDER
        chmod -R 755 ~/$TARGET_DIR
EOF

    # Copy agent files
    scp -r "$CLONE_DIR/$AGENT_FOLDER" "$VM:~/$TARGET_DIR/"

    # Set up virtual environment and install requirements
    ssh -t "$VM" << EOF
        set -e
        cd ~/$TARGET_DIR/$AGENT_FOLDER
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        deactivate
EOF

    # Create systemd service file
    ssh -t "$VM" "sudo tee /etc/systemd/system/agent.service > /dev/null" << EOF
[Unit]
Description=Agent Service
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=~/$TARGET_DIR/$AGENT_FOLDER
ExecStart=~/$TARGET_DIR/$AGENT_FOLDER/venv/bin/python ~/$TARGET_DIR/$AGENT_FOLDER/agent.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    # Enable and start the service
    ssh -t "$VM" << EOF
        set -e
        sudo systemctl daemon-reload
        sudo systemctl enable agent.service
        sudo systemctl start agent.service
EOF

    echo "Agent deployed and service started on $VM"
done

# Deploy to Load Balancer or REST VM
echo "Deploying to Load Balancer/REST VM: $LB_VM"
ssh -t "$LB_VM" "mkdir -p ~/$TARGET_DIR && chmod -R 755 ~/$TARGET_DIR"
scp -r "$CLONE_DIR"/* "$LB_VM:~/$TARGET_DIR/"

ssh -t "$LB_VM" << EOF
    set -e
    cd ~/$TARGET_DIR
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
EOF

echo "Deployment completed successfully."
