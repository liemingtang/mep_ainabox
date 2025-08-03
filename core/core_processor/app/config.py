"""
Configuration management for the Core Processor
"""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class SystemConfig(BaseModel):
    name: str = "Modular Document Intelligence System"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True


class ProcessingConfig(BaseModel):
    max_file_size: str = "100MB"
    supported_formats: List[str] = ["pdf", "docx", "txt", "html", "jpg", "jpeg", "png", "tiff"]
    parallel_processing: bool = True
    batch_size: int = 10
    timeout_seconds: int = 300
    retry_attempts: int = 3
    retry_delay_seconds: int = 5


class PostgreSQLConfig(BaseModel):
    host: str = Field(default="postgres", env="POSTGRES_HOST")
    port: int = Field(default=5432, env="POSTGRES_PORT")
    database: str = Field(default="mep_ainabox", env="POSTGRES_DB")
    user: str = Field(default="mep_user", env="POSTGRES_USER")
    password: str = Field(default="mep_password", env="POSTGRES_PASSWORD")
    pool_size: int = Field(default=10, env="POSTGRES_POOL_SIZE")
    max_overflow: int = Field(default=20, env="POSTGRES_MAX_OVERFLOW")


class ElasticsearchConfig(BaseModel):
    host: str = Field(default="elasticsearch", env="ELASTICSEARCH_HOST")
    port: int = Field(default=9200, env="ELASTICSEARCH_PORT")
    index_prefix: str = Field(default="documents", env="ELASTICSEARCH_INDEX_PREFIX")
    username: str = Field(default="elastic", env="ELASTICSEARCH_USERNAME")
    password: str = Field(default="elastic_password", env="ELASTICSEARCH_PASSWORD")
    timeout: int = Field(default=30, env="ELASTICSEARCH_TIMEOUT")


class QdrantConfig(BaseModel):
    host: str = Field(default="qdrant", env="QDRANT_HOST")
    port: int = Field(default=6333, env="QDRANT_PORT")
    api_key: str = Field(default="qdrant_api_key", env="QDRANT_API_KEY")
    timeout: int = Field(default=30, env="QDRANT_TIMEOUT")


class Neo4jConfig(BaseModel):
    uri: str = Field(default="bolt://neo4j:7687", env="NEO4J_URI")
    user: str = Field(default="neo4j", env="NEO4J_USER")
    password: str = Field(default="neo4j_password", env="NEO4J_PASSWORD")
    max_connections: int = Field(default=50, env="NEO4J_MAX_CONNECTIONS")


class MinIOConfig(BaseModel):
    endpoint: str = Field(default="minio:9000", env="MINIO_ENDPOINT")
    access_key: str = Field(default="minio_access_key", env="MINIO_ACCESS_KEY")
    secret_key: str = Field(default="minio_secret_key", env="MINIO_SECRET_KEY")
    bucket_name: str = Field(default="documents", env="MINIO_BUCKET_NAME")
    use_ssl: bool = Field(default=False, env="MINIO_USE_SSL")


class RedisConfig(BaseModel):
    host: str = Field(default="redis", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: str = Field(default="redis_password", env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")


class StorageConfig(BaseModel):
    postgresql: PostgreSQLConfig = PostgreSQLConfig()
    elasticsearch: ElasticsearchConfig = ElasticsearchConfig()
    qdrant: QdrantConfig = QdrantConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    minio: MinIOConfig = MinIOConfig()
    redis: RedisConfig = RedisConfig()


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]
    rate_limit_per_minute: int = 100
    timeout_seconds: int = 30


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    output: str = "stdout"
    file_path: str = "/app/logs/app.log"
    max_size_mb: int = 100
    backup_count: int = 5


class CoreConfig(BaseModel):
    processing: ProcessingConfig = ProcessingConfig()
    storage: StorageConfig = StorageConfig()
    api: APIConfig = APIConfig()
    logging: LoggingConfig = LoggingConfig()


class ClimateExtractorConfig(BaseModel):
    enabled: bool = True
    confidence_threshold: float = 0.7
    validation: dict = Field(default_factory=dict)


class ClimateComplianceConfig(BaseModel):
    enabled: bool = True
    version: str = "2021"
    validation_strict: bool = False


class ClimateConfig(BaseModel):
    enabled: bool = True
    extractors: dict = Field(default_factory=dict)
    compliance: dict = Field(default_factory=dict)


class FinancialConfig(BaseModel):
    enabled: bool = True
    extractors: dict = Field(default_factory=dict)
    calculators: dict = Field(default_factory=dict)
    confidence_threshold: float = 0.8


class LegalConfig(BaseModel):
    enabled: bool = False
    extractors: dict = Field(default_factory=dict)
    confidence_threshold: float = 0.8


class ModulesConfig(BaseModel):
    climate: ClimateConfig = ClimateConfig()
    financial: FinancialConfig = FinancialConfig()
    legal: LegalConfig = LegalConfig()


class ProcessingStepConfig(BaseModel):
    enabled: bool = True
    timeout: int = 60
    retry_attempts: int = 2


class ProcessingPipelineConfig(BaseModel):
    steps: dict = Field(default_factory=dict)


class RoutingRuleCondition(BaseModel):
    field: str
    operator: str
    value: List[str]


class RoutingRuleAction(BaseModel):
    enable_module: Optional[str] = None
    priority: Optional[str] = None


class RoutingRule(BaseModel):
    name: str
    conditions: List[RoutingRuleCondition]
    actions: List[RoutingRuleAction]


class DocumentRouterConfig(BaseModel):
    routing_rules: List[RoutingRule] = Field(default_factory=list)


class DataDistributionConfig(BaseModel):
    metadata: str = "postgresql"
    content: str = "elasticsearch"
    embeddings: str = "qdrant"
    relationships: str = "neo4j"
    files: str = "minio"
    cache: str = "redis"


class ConsistencyConfig(BaseModel):
    eventual_consistency: bool = True
    sync_interval_seconds: int = 300
    validation_enabled: bool = True


class BackupConfig(BaseModel):
    enabled: bool = True
    schedule: str = "0 2 * * *"
    retention_days: int = 30


class StorageManagerConfig(BaseModel):
    data_distribution: DataDistributionConfig = DataDistributionConfig()
    consistency: ConsistencyConfig = ConsistencyConfig()
    backup: BackupConfig = BackupConfig()


class MetricsConfig(BaseModel):
    enabled: bool = True
    port: int = 9090
    path: str = "/metrics"


class HealthCheckConfig(BaseModel):
    enabled: bool = True
    interval_seconds: int = 30
    timeout_seconds: int = 10


class AlertingConfig(BaseModel):
    enabled: bool = True
    webhook_url: str = ""
    email_notifications: bool = False


class MonitoringConfig(BaseModel):
    metrics: MetricsConfig = MetricsConfig()
    health_checks: HealthCheckConfig = HealthCheckConfig()
    alerting: AlertingConfig = AlertingConfig()


class AuthenticationConfig(BaseModel):
    enabled: bool = True
    jwt_secret: str = "your-jwt-secret-key"
    jwt_expiry_hours: int = 24


class AuthorizationConfig(BaseModel):
    enabled: bool = True
    default_role: str = "user"


class EncryptionConfig(BaseModel):
    enabled: bool = True
    algorithm: str = "AES-256-GCM"


class AuditLoggingConfig(BaseModel):
    enabled: bool = True
    log_level: str = "INFO"


class SecurityConfig(BaseModel):
    authentication: AuthenticationConfig = AuthenticationConfig()
    authorization: AuthorizationConfig = AuthorizationConfig()
    encryption: EncryptionConfig = EncryptionConfig()
    audit_logging: AuditLoggingConfig = AuditLoggingConfig()


class Settings(BaseSettings):
    system: SystemConfig = SystemConfig()
    core: CoreConfig = CoreConfig()
    modules: ModulesConfig = ModulesConfig()
    processing_pipeline: ProcessingPipelineConfig = ProcessingPipelineConfig()
    document_router: DocumentRouterConfig = DocumentRouterConfig()
    storage_manager: StorageManagerConfig = StorageManagerConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    security: SecurityConfig = SecurityConfig()

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Allow extra fields from environment variables
    }


def load_config() -> Settings:
    """Load configuration from YAML file and environment variables"""
    config_path = os.getenv("CONFIG_PATH", "/app/config")
    config_file = Path(config_path) / "main.yaml"
    
    settings = Settings()
    
    # Load YAML configuration if file exists
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
        
        # Update settings with YAML config
        for key, value in yaml_config.items():
            if hasattr(settings, key):
                current_value = getattr(settings, key)
                if isinstance(current_value, BaseModel):
                    # Update nested model
                    updated_value = current_value.model_validate(value)
                    setattr(settings, key, updated_value)
                else:
                    setattr(settings, key, value)
    
    return settings


# Global settings instance
settings = load_config() 