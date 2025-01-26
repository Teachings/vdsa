from confluent_kafka import Consumer, Producer
from workflow_langgrapgh_dynamic_agent import app
from models import AgentDecision
from helpers import log, load_config
import json

# Load configuration
config = load_config()
BROKER = config["kafka"]["broker"]
TOPIC_INPUT = config["kafka"]["topic_dsa"]
TOPIC_OUTPUT = config["kafka"]["topic_dsa_response"]
CONSUMER_GROUP_DSA_NAME = config["kafka"]["consumer_group_dsa_name"]
AUTO_OFFSET_RESET_DSA = config["kafka"]["auto_offset_reset_dsa"]

def consume_messages():
    """Continuously listens to the Kafka topic and invokes the LangGraph agent."""
    consumer_config = {
        "bootstrap.servers": BROKER,
        "group.id": CONSUMER_GROUP_DSA_NAME,
        "auto.offset.reset": AUTO_OFFSET_RESET_DSA
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe([TOPIC_INPUT])
    
    log(f"Listening for messages on topic: {TOPIC_INPUT}", level="INFO")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            if msg.error():
                log(f"Consumer error: {msg.error()}", level="ERROR")
                continue

            # Deserialize the message value
            transcription_data = json.loads(msg.value().decode('utf-8')) if msg.value() else {}

            if not transcription_data:
                log("Received empty message, skipping...", level="WARNING")
                continue

            log(f"Received transcription: {transcription_data}", level="INFO", color="yellow")

            # Prepare initial state for LangGraph workflow
            agent_state = {
                "initial_request": transcription_data["text"],
                "preprocessor_agent_result": "",
                "generated_code_result": "",
                "extracted_python_code": "",
                "code_review_result": "",
                "final_output": ""
            }

            try:
                # Invoke the workflow
                result = app.invoke(agent_state)

                # Construct AgentDecision object
                agent_decision = AgentDecision(
                    timestamp=transcription_data["timestamp"],
                    user="DSA Agent",
                    initial_request=agent_state["initial_request"],
                    preprocessor_agent_result=result.get("preprocessor_agent_result", ""),
                    extracted_python_code=result.get("extracted_python_code", ""),
                    final_output=result.get("final_output", "")
                )

                # Publish response back to Kafka
                produce_message(agent_decision.model_dump())

            except Exception as e:
                log(f"Error processing message: {e}", level="ERROR", color="red")

    except KeyboardInterrupt:
        log("Consumer shutting down...", level="INFO")
    finally:
        consumer.close()

def produce_message(message_dict):
    """Publishes a JSON message to the specified Kafka topic."""
    producer_config = {
        "bootstrap.servers": BROKER,
    }

    producer = Producer(producer_config)

    try:
        # Produce JSON message
        producer.produce(topic=TOPIC_OUTPUT, value=json.dumps(message_dict))
        producer.flush()

        log(f"JSON message sent to topic '{TOPIC_OUTPUT}': {message_dict}",
            level="INFO", color="green")
    except Exception as e:
        log(f"Failed to send JSON message: {e}", level="ERROR", color="red")

if __name__ == "__main__":
    consume_messages()