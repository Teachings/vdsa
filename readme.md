# VDSA: Voice Dangerously Smart Agent

Real-time speech processing system with dynamic LangGraph agent responses using Kafka communication.

## Features

- **Real-time Speech Recognition**
  - Voice Activity Detection (VAD)
  - Multi-device microphone support
  - Configurable audio processing
- **VDSA Agent System**
  - LangGraph workflow orchestration
  - Code generation & execution
  - Docker-based sandboxing
- **Distributed Architecture**
  - Kafka message streaming
  - Modular microservices
  - Horizontal scalability

## Prerequisites

- Conda (Miniconda/Anaconda)
- Python 3.10
- Local Kafka instance
- NVIDIA GPU (recommended) or Apple Silicon
- Microphone

## Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/Teachings/vdsa.git
   cd vdsa
   ```

2. **Create Conda Environment**
   ```bash
   conda create -n vdsa python=3.10
   conda activate vdsa
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Kafka**
   ```bash
   docker-compose up -d
   ```

## Configuration

`config.yml`:
```yaml
device: "cuda"  # "mps" or "cpu"
voice-model: "large-v3-turbo"
kafka:
  broker: "localhost:9092"
  topic_vdsa: "vdsa.agent.requests"
  topic_response: "vdsa.agent.response"
```

## Usage

### Unified Launcher
```bash
conda activate vdsa
python launcher.py
```

### Manual Execution
**Terminal 1 - Speech Recognition:**
```bash
conda activate vdsa
python stt/main.py
```

**Terminal 2 - Agent System:**
```bash
conda activate vdsa
python langgraph_dynamic_agent/dsa.py
```

## Architecture

```
┌────────────┐       ┌─────────────┐
│ STT Engine │       │ VDSA Agent  │
└─────┬──────┘ Kafka └──────┬──────┘
      │                     │
      ▼                     ▼
 Microphone Input      Agent Responses
```

## Logging

- **Launcher:**
  - `logs/stt.log`
  - `logs/vdsa.log`
  
- **Manual Mode:**
  ```bash
  tail -f stt/debug.log
  tail -f langgraph_dynamic_agent/agent.log
  ```