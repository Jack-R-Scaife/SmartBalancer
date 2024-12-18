#!/bin/bash
set -e

# Variables
GITHUB_REPO="https://github.com/Jack-R-Scaife/SmartBalancer.git"
CLONE_DIR="/tmp/load_balancer_repo"
AGENT_FOLDER="agent"
BACKEND_VMS=("ubs1@192.168.1.3" "ubs2@192.168.1.4" "ubs3@192.168.1.5" "ubs4@192.168.1.6" "ubs5@192.168.1.7")
LB_VM="192.168.1.2"
TARGET_DIR="load_balancer"

# Clean up and clone the latest repo locally
if [ -d "$CLONE_DIR" ]; then
    rm -rf "$CLONE_DIR"
fi
git clone "$GITHUB_REPO" "$CLONE_DIR"
chmod -R 755 "$CLONE_DIR"

####################################
# Deploy to Backend VMs
####################################
for VM in "${BACKEND_VMS[@]}"; do
    echo "Deploying agent to backend VM: $VM"

    # Create target directories on the backend VM
    ssh -tt "$VM" << EOF
        set -e
        mkdir -p ~/$TARGET_DIR/$AGENT_FOLDER
        chmod -R 755 ~/$TARGET_DIR
EOF

    # Copy the agent folder to the remote VM
    scp -r "$CLONE_DIR/$AGENT_FOLDER" "$VM:~/$TARGET_DIR/"

    # Check if Python 3 is installed
    if ! ssh -tt "$VM" "command -v python3 >/dev/null 2>&1"; then
        echo "Python3 is not installed on $VM. Exiting."
        exit 1
    fi

    # Set up virtual environment and install requirements
    ssh -tt "$VM" << EOF
        set -e
        cd ~/$TARGET_DIR/$AGENT_FOLDER
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        deactivate
EOF

    # Create systemd service file locally and copy it to the VM
    cat > /tmp/agent.service <<SERVICETEXT
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
SERVICETEXT

    scp /tmp/agent.service "$VM:~/agent.service"

    # Move service file into place and enable service
    ssh -tt "$VM" << EOF
        set -e
        sudo mv ~/agent.service /etc/systemd/system/agent.service
        sudo systemctl daemon-reload
        sudo systemctl enable agent.service
        sudo systemctl start agent.service
EOF

    echo "Agent deployed and service started on $VM"
done

####################################
# Deploy to Load Balancer VM
####################################
echo "Deploying to Load Balancer/REST VM: $LB_VM"

# Create target directories on the LB VM
ssh -tt "$LB_VM" << EOF
    set -e
    mkdir -p ~/$TARGET_DIR
    chmod -R 755 ~/$TARGET_DIR
EOF

# Copy the entire repo to the load balancer VM
scp -r "$CLONE_DIR"/* "$LB_VM:~/$TARGET_DIR/"

# Check if Python 3 is installed on the LB VM
if ! ssh -tt "$LB_VM" "command -v python3 >/dev/null 2>&1"; then
    echo "Python3 is not installed on Load Balancer VM ($LB_VM). Exiting."
    exit 1
fi

# Set up virtual environment and install requirements on the LB VM
ssh -tt "$LB_VM" << EOF
    set -e
    cd ~/$TARGET_DIR
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt || true  # If no requirements.txt, won't fail the deployment
    deactivate
EOF

echo "Deployment completed successfully."
