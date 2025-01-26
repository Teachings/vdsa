from pydantic import ValidationError
from confluent_kafka import Producer
from helpers import log, load_config
from models import TranscriptionSegment
import json


def invoke_after_transcription(latest_transcription: TranscriptionSegment):
    """
    Processes the latest transcription segment and publishes it to Kafka using JSON.
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
    TOPIC_NAME = config["kafka"]["topic_dsa"]

    # Create Producer
    producer_config = {
        "bootstrap.servers": BROKER,
    }

    producer = Producer(producer_config)

    try:
        # Produce JSON message
        producer.produce(topic=TOPIC_NAME, value=json.dumps(message_dict))
        producer.flush()

        log(f"JSON message sent to topic '{TOPIC_NAME}': {message_dict}",
            level="INFO", color="green")
    except Exception as e:
        log(f"Failed to send JSON message: {e}", level="ERROR", color="red")