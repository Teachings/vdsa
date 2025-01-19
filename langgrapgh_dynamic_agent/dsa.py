from confluent_kafka import DeserializingConsumer, SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import StringDeserializer, StringSerializer
from workflow_langgrapgh_dynamic_agent import app  # Import compiled LangGraph workflow
from models import AgentState, AgentDecision
from helpers import log, load_config
import json

# Load config
config = load_config()
BROKER = config["kafka"]["broker"]
TOPIC_INPUT = config["kafka"]["topic_transcriptions_all"]
TOPIC_OUTPUT = "agent.response"
SCHEMA_REGISTRY_URL = config["kafka"]["schema_registry_url"]
AGENT_REQUESTS_SCHEMA_LOCATION = config["kafka"]["agent_requests_schema_location"]
AGENT_DECISION_SCHEMA_LOCATION = config["kafka"]["agent_decision_schema_location"]

# Initialize Schema Registry Client
schema_registry_client = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})

# Load Avro schema
with open(AGENT_REQUESTS_SCHEMA_LOCATION, "r") as schema_file:
    agent_requests_value_schema_str = schema_file.read()
# Avro serializers/deserializers
avro_deserializer = AvroDeserializer(schema_registry_client, agent_requests_value_schema_str)

with open(AGENT_DECISION_SCHEMA_LOCATION, "r") as schema_file:
    agent_decision_value_schema_str = schema_file.read()
#to produce messages for agent_decision topic
avro_serializer = AvroSerializer(schema_registry_client, agent_decision_value_schema_str)

# Consumer configuration
consumer_config = {
    "bootstrap.servers": BROKER,
    "group.id": "langgraph_agent_consumer",
    "auto.offset.reset": "earliest",
    "key.deserializer": StringDeserializer("utf_8"),
    "value.deserializer": avro_deserializer
}

# Producer configuration
producer_config = {
    "bootstrap.servers": BROKER,
    "key.serializer": StringSerializer("utf_8"),
    "value.serializer": avro_serializer
}


def consume_messages():
    """ Continuously listens to the Kafka topic and invokes the LangGraph agent. """
    consumer = DeserializingConsumer(consumer_config)
    producer = SerializingProducer(producer_config)

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

            transcription_data = msg.value()
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

            # Invoke the workflow
            try:
                result = app.invoke(agent_state)

                # Construct AgentDecision object
                agent_decision = AgentDecision(
                    timestamp=transcription_data["timestamp"],
                    user=transcription_data["user"],
                    initial_request=agent_state["initial_request"],
                    preprocessor_agent_result=result.get("preprocessor_agent_result", ""),
                    extracted_python_code=result.get("extracted_python_code", ""),
                    final_output=result.get("final_output", "")
                )

                # Publish response back to Kafka
                producer.produce(topic=TOPIC_OUTPUT, key=None, value=agent_decision.model_dump())
                producer.flush()

                log(f"Agent decision published to {TOPIC_OUTPUT}: {agent_decision.model_dump()}", level="INFO", color="green")

            except Exception as e:
                log(f"Error processing message: {e}", level="ERROR", color="red")

    except KeyboardInterrupt:
        log("Consumer shutting down...", level="INFO")
    finally:
        consumer.close()


if __name__ == "__main__":
    consume_messages()
