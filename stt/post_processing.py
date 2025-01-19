from pydantic import ValidationError
from typing import Optional
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer
from helpers import log, load_config
from models import TranscriptionSegment


def invoke_after_transcription(latest_transcription: TranscriptionSegment):
    """
    Processes the latest transcription segment and publishes it to Kafka using Avro.
    """
    log("Post-processing transcription", level="INFO")

    try:
        # Validate and prepare the transcription data
        transcription_data = latest_transcription.model_dump()

        # Log and produce the message
        log(f"Publishing transcription: {transcription_data['text']}",
            level="INFO", color="yellow")
        produce_message(transcription_data)

    except ValidationError as e:
        log(f"Validation error: {e}", level="ERROR")


def produce_message(message_dict):
    config = load_config()
    BROKER = config["kafka"]["broker"]
    TOPIC_NAME = config["kafka"]["topic_transcriptions_all"]
    SCHEMA_LOCATION = config["kafka"]["agent_requests_schema_location"]
    SCHEMA_REGISTRY_URL = config["kafka"]["schema_registry_url"]

    # Initialize Schema Registry Client
    schema_registry_client = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})

    # Load the Avro schema
    with open(SCHEMA_LOCATION, "r") as schema_file:
        value_schema_str = schema_file.read()

    # Create Avro Serializer
    avro_serializer = AvroSerializer(schema_registry_client, value_schema_str)

    # Create Serializing Producer
    producer_config = {
        "bootstrap.servers": BROKER,
        "key.serializer": StringSerializer("utf_8"),  # Key is None, but needs serializer
        "value.serializer": avro_serializer
    }

    producer = SerializingProducer(producer_config)

    try:
        # Produce Avro message
        producer.produce(topic=TOPIC_NAME, key=None, value=message_dict)
        producer.flush()

        log(f"Avro message sent to topic '{TOPIC_NAME}': {message_dict}",
            level="INFO", color="green")
    except Exception as e:
        log(f"Failed to send Avro message: {e}", level="ERROR", color="red")
