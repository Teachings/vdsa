
# Voice-DSA: Dynamic Speech Agent System

A real-time speech-to-text processing system with dynamic LangGraph agent responses, powered by Kafka-based communication.

## Features

- **Real-time Speech Recognition**
  - Voice Activity Detection (VAD)
  - Multi-device microphone support
  - Configurable audio processing
- **Dynamic Agent System**
  - LangGraph workflow management
  - Code generation & execution
  - Docker-based code sandboxing
- **Distributed Architecture**
  - Kafka message broker
  - Modular service design
  - Scalable components

## Prerequisites

- Conda (Miniconda or Anaconda)
- Python 3.8+
- Kafka server running locally
- NVIDIA GPU (recommended) or Apple Silicon
- Microphone

## Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/voice-dsa.git
   cd voice-dsa
   ```

2. **Create Conda Environment**
   ```bash
   conda create -n vdsa python=3.8
   conda activate vdsa
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Kafka**
   ```bash
   # Start Kafka server (requires Docker)
   docker-compose up -d
   ```

## Configuration

Edit `config.yml` for your environment:
```yaml
device: "cuda"  # or "mps"/"cpu"
voice-model: "large-v3-turbo"
kafka:
  broker: "localhost:9092"
  topic_dsa: "dsa.agent.requests"
  topic_dsa_response: "dsa.agent.response"
```

## Usage

### Method 1: Unified Launcher (Recommended)
```bash
conda activate vdsa
python launcher.py
```

**Features:**
- Starts both STT and DSA services
- Automatic log management (`logs/` directory)
- Graceful shutdown (Ctrl+C)

### Method 2: Manual Execution
**Terminal 1 - Speech Recognition:**
```bash
conda activate vdsa
python stt/main.py
```

**Terminal 2 - Agent System:**
```bash
conda activate vdsa
python langgrapgh_dynamic_agent/dsa.py
```

## System Architecture

```
┌─────────────┐       ┌─────────────┐
│ Speech-to-  │       │ Dynamic     │
│ Text (STT)  │◄─────►│ Agent (DSA) │
└──────┬──────┘ Kafka └──────┬──────┘
       │                      │
       ▼                      ▼
  Microphone Input      Agent Responses
```

## Logging

- **Launcher Mode:**
  - STT logs: `logs/stt.log`
  - DSA logs: `logs/dsa.log`
  
- **Manual Mode:**
  ```bash
  tail -f stt/debug.log
  tail -f langgrapgh_dynamic_agent/agent.log
  ```

## Troubleshooting

**Common Issues:**
1. **Microphone Not Found**
   - Check `config.yml` favorite_microphones
   - List devices with `python stt/audio_utils.py`

2. **Conda Environment Issues**
   ```bash
   conda deactivate
   conda activate vdsa
   ```

3. **Kafka Connection Errors**
   ```bash
   docker-compose restart
   ```

## License

MIT License - See [LICENSE](LICENSE)
```

Key features of this README:
1. Clear installation and setup instructions for both launch methods
2. Architecture diagram for system understanding
3. Troubleshooting common issues
4. Configuration guidance
5. License information

The document balances technical detail with usability, making it accessible for both developers and end-users. You can customize the Kafka setup instructions and license information as needed for your specific implementation.