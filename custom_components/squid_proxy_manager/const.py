"""Constants for the Squid Proxy Manager integration."""

DOMAIN = "squid_proxy_manager"

# Default values
DEFAULT_PORT = 3128
DEFAULT_UPDATE_INTERVAL = 30  # seconds
DEFAULT_MEMORY_LIMIT = "512m"
DEFAULT_CPU_LIMIT = 1.0

# Port validation
MIN_PORT = 1024
MAX_PORT = 65535
SYSTEM_PORTS_WARNING = 1024  # Warn if port < 1024

# Security
MIN_PASSWORD_LENGTH = 8
CERT_VALIDITY_DAYS = 365
CERT_KEY_SIZE = 2048

# File permissions
PERM_CONFIG_FILE = 0o644
PERM_PRIVATE_KEY = 0o600
PERM_PASSWORD_FILE = 0o600
PERM_DIRECTORY = 0o755

# Docker
DOCKER_SOCKET = "/var/run/docker.sock"
DOCKER_IMAGE_NAME = "squid-proxy-manager"
DOCKER_NETWORK_MODE = "bridge"
DOCKER_USER = "squid"
DOCKER_UID = 1000
DOCKER_GID = 1000

# Paths (relative to HA config directory)
PATH_CONFIG_DIR = "squid_proxy_manager"
PATH_CERTS_DIR = "squid_proxy_manager/certs"
PATH_LOGS_DIR = "squid_proxy_manager/logs"

# Container paths
CONTAINER_CONFIG_DIR = "/etc/squid"
CONTAINER_CERT_DIR = "/etc/squid/ssl_cert"
CONTAINER_PASSWD_FILE = "/etc/squid/passwd"
CONTAINER_LOG_DIR = "/var/log/squid"

# Entity attributes
ATTR_PORT = "port"
ATTR_HTTPS_ENABLED = "https_enabled"
ATTR_USER_COUNT = "user_count"
ATTR_CONTAINER_ID = "container_id"
ATTR_CERT_EXPIRY = "certificate_expiry"
ATTR_LAST_STARTED = "last_started"
ATTR_LAST_STOPPED = "last_stopped"
ATTR_INSTANCE_NAME = "instance_name"

# Entity states
STATE_RUNNING = "running"
STATE_STOPPED = "stopped"
STATE_ERROR = "error"
STATE_UNAVAILABLE = "unavailable"

# Service names
SERVICE_START_INSTANCE = "start_instance"
SERVICE_STOP_INSTANCE = "stop_instance"
SERVICE_RESTART_INSTANCE = "restart_instance"
SERVICE_ADD_USER = "add_user"
SERVICE_REMOVE_USER = "remove_user"
SERVICE_UPDATE_CERTIFICATE = "update_certificate"
SERVICE_GET_USERS = "get_users"

# Config flow steps
STEP_USER = "user"
STEP_INSTANCE_NAME = "instance_name"
STEP_PORT = "port"
STEP_CERTIFICATE = "certificate"
STEP_INITIAL_USER = "initial_user"
STEP_REVIEW = "review"

# Error messages
ERROR_PORT_IN_USE = "port_in_use"
ERROR_INVALID_PORT = "invalid_port"
ERROR_DOCKER_NOT_AVAILABLE = "docker_not_available"
ERROR_CERT_GENERATION_FAILED = "cert_generation_failed"
ERROR_INVALID_USERNAME = "invalid_username"
ERROR_WEAK_PASSWORD = "weak_password"
ERROR_CONTAINER_CREATION_FAILED = "container_creation_failed"
