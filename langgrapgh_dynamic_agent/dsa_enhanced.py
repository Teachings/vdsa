import time
from confluent_kafka import Consumer, Producer
from workflow_langgrapgh_dynamic_agent import app
from models import AgentDecision, AgentState, CodeReviewResult
from helpers import log, load_config
import json
from pydantic import ValidationError
from datetime import datetime
import uuid

class KafkaManager:
    def __init__(self):
        self.config = load_config()
        self._log_kafka_config()
        self.producer = Producer({"bootstrap.servers": self.config["kafka"]["broker"]})
        log("✅ Kafka producer initialized", level="SUCCESS", color="green")

    def _log_kafka_config(self):
        """Log Kafka configuration details"""
        log("Initializing Kafka connection with configuration:", level="INFO")
        log(f"  Broker: {self.config['kafka']['broker']}", level="DEBUG")
        log(f"  Input Topic: {self.config['kafka']['topic_dsa']}", level="DEBUG")
        log(f"  Output Topic: {self.config['kafka']['topic_dsa_response']}", level="DEBUG")
        log(f"  Consumer Group: {self.config['kafka']['consumer_group_dsa_name']}", level="DEBUG")

    def produce(self, message: dict):
        """Produce message with enhanced logging"""
        message_id = str(uuid.uuid4())[:8]
        try:
            log(f"📤 Preparing to send message ID {message_id}", level="DEBUG")
            self.producer.produce(
                topic=self.config["kafka"]["topic_dsa_response"],
                value=json.dumps(message),
                callback=lambda err, msg: self._delivery_report(err, msg, message_id)
            )
            self.producer.poll(0)
            log(f"📩 Message ID {message_id} queued for delivery", level="DEBUG")
        except Exception as e:
            log(f"❌ Failed to queue message ID {message_id}: {str(e)}", level="ERROR")

    @staticmethod
    def _delivery_report(err, msg, message_id: str):
        """Handle delivery reports with detailed logging"""
        if err:
            log(f"❌ Failed to deliver message ID {message_id}: {err}", level="ERROR")
        else:
            log(f"📬 Successfully delivered message ID {message_id} to {msg.topic()}[{msg.partition()}]", 
                level="INFO", color="green")

def consume_messages():
    """Optimized Kafka consumer with detailed startup logging"""
    config = load_config()
    
    log("\n" + "="*50, level="INFO")
    log("🚀 Starting Dynamic Service Agent (DSA)", level="INFO", color="yellow")
    log(f"🕒 System Start Time: {datetime.now().isoformat()}", level="INFO")
    log("="*50, level="INFO")
    
    try:
        # Validate configuration before initializing components
        _validate_kafka_config(config)
        
        consumer_config = {
            "bootstrap.servers": config["kafka"]["broker"],
            "group.id": config["kafka"]["consumer_group_dsa_name"],
            "auto.offset.reset": config["kafka"]["auto_offset_reset_dsa"],
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000
        }
        
        log("🛠 Initializing Kafka consumer...", level="INFO")
        log(f"🔧 Consumer configuration: {json.dumps(consumer_config, indent=2)}", level="DEBUG")
        
        consumer = Consumer(consumer_config)
        kafka = KafkaManager()
        
        log(f"🔔 Subscribing to topic: {config['kafka']['topic_dsa']}", level="INFO")
        consumer.subscribe([config["kafka"]["topic_dsa"]])
        
        log("\n" + "="*50, level="INFO")
        log("✅ System initialization complete!", level="SUCCESS", color="green")
        log("📡 Listening for incoming messages...", level="INFO", color="cyan")
        log("="*50 + "\n", level="INFO")

        _operation_loop(consumer, kafka)

    except KeyboardInterrupt:
        log("\n🛑 Received shutdown signal", level="WARNING")
    except Exception as e:
        log(f"❌ Critical initialization error: {str(e)}", level="ERROR")
    finally:
        log("🔌 Closing Kafka connections...", level="INFO")
        consumer.close()
        log("📴 Kafka connections closed", level="INFO")

def _validate_kafka_config(config: dict):
    """Validate Kafka configuration with detailed error reporting"""
    required_keys = ["broker", "topic_dsa", "topic_dsa_response", "consumer_group_dsa_name"]
    errors = []
    
    for key in required_keys:
        if not config["kafka"].get(key):
            errors.append(f"Missing required Kafka config key: {key}")
    
    if errors:
        log("❌ Invalid Kafka configuration:", level="ERROR")
        for error in errors:
            log(f"  - {error}", level="ERROR")
        raise ValueError("Invalid Kafka configuration")

def _operation_loop(consumer: Consumer, kafka: KafkaManager):
    """Main consumer loop with silent waiting and periodic health checks"""
    log("🔁 Starting main operation loop", level="INFO")
    msg_count = 0
    error_count = 0
    last_activity = time.time()
    health_check_interval = 300  # 5 minutes
    warning_threshold = 600      # 10 minutes
    
    try:
        while True:
            # Use a longer timeout to reduce polling frequency
            messages = consumer.consume(num_messages=100, timeout=1.0)
            
            if not messages:
                # Silent wait - no logging for normal timeouts
                current_time = time.time()
                
                # Periodic health check
                if current_time - last_activity > health_check_interval:
                    idle_time = current_time - last_activity
                    log(f"⏳ No messages received in {idle_time:.0f}s - system healthy", 
                        level="INFO", color="blue")
                    
                    # Reset counter to avoid spamming
                    last_activity = current_time
                    
                    # Escalate to warning after threshold
                    if idle_time > warning_threshold:
                        log(f"⚠️  No messages received in {idle_time:.0f}s - check input source", 
                            level="WARNING")
                continue
                
            # Reset activity timer
            last_activity = time.time()
            log(f"📥 Received batch of {len(messages)} messages", level="DEBUG")
            
            for msg in messages:
                msg_count += 1
                error_count = _process_single_message(msg, consumer, kafka, msg_count, error_count)
                
            # Compact health report
            log(f"📊 System Health: Processed {msg_count} messages | Active errors: {error_count}", 
                level="INFO", color="cyan")

    except Exception as e:
        log(f"❌ Unexpected error in operation loop: {str(e)}", level="ERROR")
        raise

def _process_single_message(msg, consumer: Consumer, kafka: KafkaManager, msg_count: int, error_count: int):
    """Process individual message with error tracking"""
    message_id = f"MSG-{msg_count:04d}"
    
    try:
        if msg.error():
            error_count += 1
            log(f"❌ {message_id} | Consumer error: {msg.error()}", level="ERROR")
            return

        log(f"📨 {message_id} | Received message", level="DEBUG")
        start_time = time.time()
        
        data = json.loads(msg.value().decode('utf-8'))
        log(f"🔍 {message_id} | Processing request from {data.get('user', 'unknown')}", level="INFO")
        
        process_message(data, kafka, message_id)
        consumer.commit(msg)
        
        proc_time = time.time() - start_time
        log(f"✅ {message_id} | Processing completed in {proc_time:.2f}s", level="INFO")

    except Exception as e:
        error_count += 1
        log(f"❌ {message_id} | Processing failed: {str(e)}", level="ERROR")

def process_message(data: dict, kafka: KafkaManager, message_id: str):
    """Process message with transaction-style logging"""
    try:
        log(f"🧠 {message_id} | Initializing agent state...", level="DEBUG")
        state = AgentState(
            initial_request=data["text"],
            preprocessor_agent_result="",
            generated_code_result="",
            extracted_python_code="",
            code_review_result=CodeReviewResult(result="", message=""),
            final_output=""
        )
        
        log(f"🤖 {message_id} | Invoking LangGraph workflow...", level="DEBUG")
        result = app.invoke(state)
        
        log(f"📝 {message_id} | Creating agent decision...", level="DEBUG")
        decision = AgentDecision(
            timestamp=data["timestamp"],
            user="DSA Agent",
            initial_request=result["initial_request"],
            preprocessor_agent_result=result["preprocessor_agent_result"],
            extracted_python_code=result["extracted_python_code"],
            final_output=result["final_output"]
        )
        
        log(f"📤 {message_id} | Sending response...", level="DEBUG")
        kafka.produce(decision.model_dump())
        log(f"🎉 {message_id} | End-to-end processing complete", level="INFO")

    except ValidationError as e:
        log(f"❌ {message_id} | Validation error: {str(e)}", level="ERROR")
        raise
    except Exception as e:
        log(f"❌ {message_id} | Unexpected processing error: {str(e)}", level="ERROR")
        raise

if __name__ == "__main__":
    consume_messages()