#!/bin/bash

# Set variables
GITHUB_REPO_URL="https://github.com/Jack-R-Scaife/SmartBalancer.git"
TEMP_DIR="/tmp/smartbalancer_deployment"
AGENT_DIR="${TEMP_DIR}/agent"
BACKEND_VMS=("server1@192.168.1.4" "server2@192.168.1.5")
REST_VM="specific-vm@192.168.1.2"

# Start SSH Agent
echo "Starting SSH Agent..."
eval "$(ssh-agent -s)"
ssh-add

# Clone the GitHub repository
echo "Cloning GitHub repository..."
rm -rf "$TEMP_DIR"
git clone "$GITHUB_REPO_URL" "$TEMP_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to clone GitHub repository."
    exit 1
fi

# Ensure the agent directory exists
if [ ! -d "$AGENT_DIR" ]; then
    echo "Error: 'agent' directory not found in the repository."
    exit 1
fi

# Deploy the `agent` directory to backend servers
for VM in "${BACKEND_VMS[@]}"; do
    echo "Deploying 'agent' to $VM..."

    ssh "$VM" "rm -rf /home/${VM%%@*}/smartbalancer/agent"
    scp -r "$AGENT_DIR" "$VM:/home/${VM%%@*}/smartbalancer/agent"

    ssh "$VM" << EOF
        echo "Setting up the agent on $VM..."
        cd /home/${VM%%@*}/smartbalancer/agent

        # Set up virtual environment
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate

        # Install dependencies from the agent's own requirements.txt
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        fi

        echo "Agent setup complete on $VM."
EOF
done

# Deploy the rest of the directory to the specific VM
echo "Deploying the rest of the code to $REST_VM..."

ssh "$REST_VM" "rm -rf /home/${REST_VM%%@*}/smartbalancer"
scp -r "$TEMP_DIR" "$REST_VM:/home/${REST_VM%%@*}/smartbalancer"

ssh "$REST_VM" << EOF
    echo "Setting up the rest of the code on $REST_VM..."
    cd /home/${REST_VM%%@*}/smartbalancer

    # Set up virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate

    # Install dependencies from the main requirements.txt
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    echo "Setup complete for the rest of the code on $REST_VM."
EOF

# Kill the SSH Agent
eval "$(ssh-agent -k)"

echo "Deployment process completed."
