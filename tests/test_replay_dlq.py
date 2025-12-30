"""
Unit tests for replay_dlq script
Tests the Kafka connection configuration strategy
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.replay_dlq import replay_messages


@pytest.mark.unit
class TestReplayDLQKafkaConfig:
    """Test Kafka configuration logic in replay_dlq"""
    
    @patch('scripts.replay_dlq.get_config')
    @patch('scripts.replay_dlq.NewsKafkaConsumer')
    @patch('scripts.replay_dlq.NewsKafkaProducer')
    def test_uses_full_config_when_default(self, mock_producer, mock_consumer, mock_get_config):
        """Test that full connection config is used when no argument is provided"""
        # Setup mock config
        mock_config = Mock()
        mock_config.kafka.bootstrap_servers = "prod.kafka.example.com:9093"
        mock_config.kafka.connection_config = {
            'bootstrap.servers': 'prod.kafka.example.com:9093',
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': 'test_user',
            'sasl.password': 'test_pass'
        }
        mock_get_config.return_value = mock_config
        
        # Mock consumer and producer to avoid actual connections
        mock_consumer_instance = Mock()
        mock_consumer_instance.consumer.poll.return_value = None
        mock_consumer.return_value = mock_consumer_instance
        
        mock_producer_instance = Mock()
        mock_producer_instance.producer.flush.return_value = None
        mock_producer.return_value = mock_producer_instance
        
        # Call function without kafka_bootstrap_servers argument (defaults to None)
        replay_messages(
            source_topic='test-source',
            target_topic='test-target',
            kafka_bootstrap_servers=None,
            max_messages=1,
            dry_run=True
        )
        
        # Verify that consumer and producer were created with full config dict
        mock_consumer.assert_called_once()
        consumer_call_kwargs = mock_consumer.call_args[1]
        assert consumer_call_kwargs['bootstrap_servers'] == mock_config.kafka.connection_config
        
        mock_producer.assert_called_once()
        producer_call_kwargs = mock_producer.call_args[1]
        assert producer_call_kwargs['bootstrap_servers'] == mock_config.kafka.connection_config
    
    @patch('scripts.replay_dlq.get_config')
    @patch('scripts.replay_dlq.NewsKafkaConsumer')
    @patch('scripts.replay_dlq.NewsKafkaProducer')
    def test_uses_full_config_when_matching_string(self, mock_producer, mock_consumer, mock_get_config):
        """Test that full connection config is used when provided string matches config"""
        # Setup mock config
        mock_config = Mock()
        mock_config.kafka.bootstrap_servers = "prod.kafka.example.com:9093"
        mock_config.kafka.connection_config = {
            'bootstrap.servers': 'prod.kafka.example.com:9093',
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': 'test_user',
            'sasl.password': 'test_pass'
        }
        mock_get_config.return_value = mock_config
        
        # Mock consumer and producer
        mock_consumer_instance = Mock()
        mock_consumer_instance.consumer.poll.return_value = None
        mock_consumer.return_value = mock_consumer_instance
        
        mock_producer_instance = Mock()
        mock_producer_instance.producer.flush.return_value = None
        mock_producer.return_value = mock_producer_instance
        
        # Call function with kafka_bootstrap_servers matching config
        replay_messages(
            source_topic='test-source',
            target_topic='test-target',
            kafka_bootstrap_servers='prod.kafka.example.com:9093',
            max_messages=1,
            dry_run=True
        )
        
        # Verify that consumer and producer were created with full config dict
        mock_consumer.assert_called_once()
        consumer_call_kwargs = mock_consumer.call_args[1]
        assert consumer_call_kwargs['bootstrap_servers'] == mock_config.kafka.connection_config
        
        mock_producer.assert_called_once()
        producer_call_kwargs = mock_producer.call_args[1]
        assert producer_call_kwargs['bootstrap_servers'] == mock_config.kafka.connection_config
    
    @patch('scripts.replay_dlq.get_config')
    @patch('scripts.replay_dlq.NewsKafkaConsumer')
    @patch('scripts.replay_dlq.NewsKafkaProducer')
    def test_uses_simple_string_when_different(self, mock_producer, mock_consumer, mock_get_config):
        """Test that simple string is used when provided string differs from config"""
        # Setup mock config
        mock_config = Mock()
        mock_config.kafka.bootstrap_servers = "prod.kafka.example.com:9093"
        mock_config.kafka.connection_config = {
            'bootstrap.servers': 'prod.kafka.example.com:9093',
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': 'test_user',
            'sasl.password': 'test_pass'
        }
        mock_get_config.return_value = mock_config
        
        # Mock consumer and producer
        mock_consumer_instance = Mock()
        mock_consumer_instance.consumer.poll.return_value = None
        mock_consumer.return_value = mock_consumer_instance
        
        mock_producer_instance = Mock()
        mock_producer_instance.producer.flush.return_value = None
        mock_producer.return_value = mock_producer_instance
        
        # Call function with different kafka_bootstrap_servers (e.g., localhost override)
        replay_messages(
            source_topic='test-source',
            target_topic='test-target',
            kafka_bootstrap_servers='localhost:9093',
            max_messages=1,
            dry_run=True
        )
        
        # Verify that consumer and producer were created with simple string
        mock_consumer.assert_called_once()
        consumer_call_kwargs = mock_consumer.call_args[1]
        assert consumer_call_kwargs['bootstrap_servers'] == 'localhost:9093'
        
        mock_producer.assert_called_once()
        producer_call_kwargs = mock_producer.call_args[1]
        assert producer_call_kwargs['bootstrap_servers'] == 'localhost:9093'
