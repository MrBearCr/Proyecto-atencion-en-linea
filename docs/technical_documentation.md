---
hidden: true
---

# Client Management System - Technical Documentation

## 1. Introduction & Scope

### 1.1 Overview

The Client Management System (app.py) is a feature-rich desktop application designed for managing client relationships, inventory monitoring, and automated WhatsApp communications. Built with Python and Tkinter, this application integrates with SQL Server databases to provide a comprehensive solution for client data management, stock monitoring, and communication automation.

The system serves as a centralized platform for tracking client information, monitoring product inventory levels, and sending automated notifications to clients based on stock availability and other triggerable events. With its rich feature set, the application streamlines client communication workflows while providing critical inventory visibility.

### 1.2 System Requirements

#### Software Dependencies

* Python 3.8 or higher
* Microsoft SQL Server (2016 or later recommended)
* Windows 10 or higher (primary supported OS)

#### Required Python Libraries

* `pyodbc`: For SQL Server database connectivity
* `tkinter` and `ttk`: For the graphical user interface
* `cryptography.fernet`: For secure encryption of credentials
* `keyring`: For secure credential storage in the system keychain
* `matplotlib`: For data visualization and statistics
* `tkcalendar`: For date selection UI components
* `requests`: For API communication with WhatsApp services
* `win10toast`: For Windows 10 notifications

#### Hardware Recommendations

* 4GB RAM minimum (8GB recommended)
* 1GB available disk space
* 1366x768 screen resolution or higher
* Internet connection for WhatsApp API functionality

### 1.3 Key Features & Capabilities

#### Client Management

* Client record creation, retrieval, updating, and deletion
* Association of clients with product codes
* Client filtering and search functionality

#### Inventory Tracking

* Real-time monitoring of product stock levels
* Critical inventory alerts with configurable thresholds
* Favorite products tracking for prioritized monitoring
* CSV export of inventory reports

#### Automated Messaging

* WhatsApp integration for client notifications
* Template-based messaging for consistency
* Bulk messaging to multiple clients
* Scheduled message delivery
* Delivery status tracking

#### Security Features

* Encrypted credential storage
* Session timeout management
* SQL injection prevention
* Comprehensive audit logging
* Input validation and sanitization

#### User Interface

* Modern tabbed interface with five main areas:
  * Records: Client data management
  * Messaging: Communication tools
  * Statistics: Visual data analysis
  * Calendar: Scheduled events view
  * Stock Alerts: Inventory monitoring

#### Background Processing

* Multithreaded architecture for responsive UI
* Scheduled tasks for periodic inventory checks
* Automatic reconnection to database when needed
* Notification management for critical stock levels

The application is designed with extensibility in mind, allowing for future enhancements and integration with additional systems or APIs as business needs evolve.

## 2. Environmental Setup & Configuration

### 2.1 Installation Prerequisites

Before installing the Client Management System, ensure your environment meets the system requirements outlined in Section 1.2. This section provides step-by-step instructions for setting up the application and its dependencies.

#### 2.1.1 Python Environment Setup

1. Install Python 3.8 or higher from [python.org](https://www.python.org/downloads/)
2. During installation, ensure you select "Add Python to PATH" to access Python from the command line
3.  Verify your installation by running:

    ```
    python --version
    ```

#### 2.1.2 Required Libraries Installation

Install all required Python libraries using pip:

```bash
pip install pyodbc tkinter cryptography keyring matplotlib tkcalendar requests win10toast
```

For SQL Server connectivity, ensure you have the appropriate ODBC drivers installed:

1. Download the Microsoft ODBC Driver for SQL Server from the [Microsoft Download Center](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
2. Run the installer and follow the prompts to complete installation
3. Verify installation by checking available ODBC drivers in Windows ODBC Data Source Administrator

### 2.2 Database Configuration

The application uses a SQL Server database and securely stores connection credentials in an encrypted format.

#### 2.2.1 SQL Server Setup

1. Ensure SQL Server is properly installed and running
2.  Create a dedicated database for the application:

    ```sql
    CREATE DATABASE ClientManagementDB;
    ```
3.  Create a dedicated user with appropriate permissions:

    ```sql
    USE ClientManagementDB;
    CREATE LOGIN ClientAppUser WITH PASSWORD = 'StrongPassword123';
    CREATE USER ClientAppUser FOR LOGIN ClientAppUser;
    GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE TO ClientAppUser;
    ```

#### 2.2.2 Configuring Database Credentials

The application uses an encrypted configuration file (`db_config.ini`) to store database connection information. Credentials are encrypted using the Fernet symmetric encryption algorithm with a key stored in the system's keychain.

When launching the application for the first time:

1. Open the application and navigate to the "Settings" menu
2. In the "Connection" tab, enter:
   * Server: Your SQL Server hostname or IP address
   * Database: Database name (e.g., ClientManagementDB)
   * User: Database username (e.g., ClientAppUser)
   * Password: Database user password
3. Click "Save" to encrypt and store these credentials

The application will:

* Generate an encryption key (if not already present)
* Store the key securely in the system keychain using the keyring library
* Encrypt the credentials and save them in `db_config.ini`
* Test the connection to ensure validity

For security reasons, passwords are never stored in plain text. The password is temporarily stored in an encrypted format using the system keychain and is retrieved only when needed for database connections.

### 2.3 WhatsApp API Integration

The application integrates with the WhatsApp Business API to send notifications to clients.

#### 2.3.1 Prerequisites

1. A Meta Developer account with WhatsApp Business API access
2. An approved WhatsApp Business Account
3. Approved message templates in your Meta Business Manager

#### 2.3.2 Configuring the WhatsApp API Token

1. From the Meta Developer Portal, obtain your WhatsApp API token
2. In the application, navigate to Settings → API WhatsApp tab
3. Enter your WhatsApp API token in the designated field
4. Click "Save" to securely store the encrypted token

The WhatsApp token is encrypted using the same secure mechanism as database credentials and stored in the system keychain.

#### 2.3.3 Message Templates

The application uses the following WhatsApp message templates, which need to be pre-approved in your Meta Business account:

1. `alerta_stock`: For notifying clients about product availability
2. `recordatorio_entrega`: For sending delivery reminders
3. `sede`: For notifying clients that products are available at the store

Ensure these templates are created and approved in your WhatsApp Business Manager before attempting to send messages.

### 2.4 First-Time Application Setup

#### 2.4.1 Initial Configuration

1.  Launch the application by running:

    ```
    python app.py
    ```
2. You'll be prompted to configure the database connection on first launch
3. After database connection is established, the application will automatically:
   * Create necessary database tables if they don't exist
   * Initialize logging and auditing systems
   * Start background monitoring threads

#### 2.4.2 Security Considerations

* The application creates a session timeout of 15 minutes by default (900 seconds)
* To modify the timeout duration, edit the `self.timeout` value in the `SessionManager` class
* Audit logs are stored in `audit.log` in the application directory
* Credentials are never exposed in the logs or user interface

#### 2.4.3 Configuration File Management

The following configuration files are used by the application:

* `db_config.ini`: Contains encrypted database connection information

**Important:** Never directly edit these files, as they contain encrypted data. Always use the application's settings interface to make changes.

For system administrators who need to reset configurations, you can safely delete these files and reconfigure through the application's interface.

## 3. High-Level Architecture Overview

### 3.1 Architectural Design

The Client Management System follows a multi-layered architecture that separates concerns between presentation, business logic, and data access. The application is designed as a standalone desktop application with a rich GUI interface and persistent database storage.

#### 3.1.1 Main Architectural Components

![Architecture Diagram](architecture_diagram.png)

_Note: Insert actual architecture diagram here showing the relationships between components._

The system consists of the following major components:

1. **User Interface Layer**
   * Implemented using Tkinter and ttk for a modern Windows desktop experience
   * Organized with tabs for different functional areas (Records, Messaging, etc.)
   * Includes form inputs, data display components, and user notification systems
2. **Business Logic Layer**
   * Core application logic implemented in the `DatabaseApp` class
   * Specialized managers for specific functions:
     * `SessionManager`: Handles user session state and timeout
     * `SecureCredentialsManager`: Manages secure storage and retrieval of credentials
     * `NotificationManager`: Controls system notifications
     * `ProgramadorEnvios`: Manages scheduled message delivery
     * `EnvioProgramado`: Handles message scheduling
3. **Data Access Layer**
   * `DatabaseManager` class provides a clean abstraction for database operations
   * Handles connection management, query execution, and error handling
   * Implements table creation and maintenance
4. **Security Layer**
   * `SecureCredentialsManager` for credential encryption/decryption
   * `AuditLogger` for activity logging
   * Input validation and sanitization throughout the application
5. **Background Processing**
   * Multiple threads for non-blocking operations
   * Scheduled tasks for periodic database queries and updates
   * Event-based notification system
6. **External Integration**
   * WhatsApp API integration for messaging
   * Windows notification system integration

### 3.2 Component Interaction Flow

#### 3.2.1 Primary Data Flow

```
┌───────────────┐     ┌────────────────┐     ┌─────────────────┐     ┌───────────────┐
│  User         │     │  UI Layer      │     │  Business Logic │     │  Data Access  │
│  Interaction  │────▶│  (Tkinter)     │────▶│  (DatabaseApp)  │────▶│  Layer        │
└───────────────┘     └────────────────┘     └─────────────────┘     └───────────────┘
                                                      │                      │
                                                      │                      │
                                                      ▼                      ▼
┌───────────────┐     ┌────────────────┐     ┌─────────────────┐     ┌───────────────┐
│  External     │     │  Background    │     │  Security       │     │  SQL Server   │
│  APIs         │◀───▶│  Processes     │◀───▶│  Layer          │◀───▶│  Database     │
└───────────────┘     └────────────────┘     └─────────────────┘     └───────────────┘
```

#### 3.2.2 Key Interaction Sequences

**1. Database Operation Flow:**

1. User triggers an action in the UI (e.g., searching for a client)
2. Event handler in the UI layer calls appropriate method in DatabaseApp
3. DatabaseApp validates inputs and delegates to DatabaseManager
4. DatabaseManager constructs and executes the query
5. Results are returned through the chain and displayed in the UI
6. Actions are logged by AuditLogger

**2. WhatsApp Notification Flow:**

1. Notification is triggered (manually or by scheduled task)
2. DatabaseApp or ProgramadorEnvios initiates the message process
3. Client data and product information are retrieved from the database
4. Message is constructed using appropriate template
5. SecureCredentialsManager provides the encrypted API token
6. Message is sent to the WhatsApp API
7. Result is logged and displayed to the user

**3. Background Monitoring Flow:**

1. Background threads initialize during application startup
2. Periodic checks query the database for stock levels
3. Critical stock levels trigger internal notifications
4. For favorited products, Windows notifications are generated
5. UI is updated with latest stock information

### 3.3 Key Architectural Patterns

#### 3.3.1 Model-View Separation

While not a strict Model-View-Controller implementation, the application separates:

* **View**: Tkinter UI components in the setup\_\* methods
* **Model**: Database schema and data access through DatabaseManager
* **Controller Logic**: Methods in DatabaseApp that handle user actions

#### 3.3.2 Manager Pattern

The application uses specialized manager classes for distinct responsibilities:

* **DatabaseManager**: Handles all database interactions
* **SecureCredentialsManager**: Manages credential encryption and secure storage
* **SessionManager**: Controls user session state and timeout
* **NotificationManager**: Centralizes user notification presentation

#### 3.3.3 Service Layer Pattern

The application implements service-like classes for specific business functions:

* **EnvioProgramado**: Handles message scheduling logic
* **ProgramadorEnvios**: Manages the execution of scheduled messages
* **AuditLogger**: Provides centralized logging services

#### 3.3.4 Cache Pattern

The application implements caching to reduce database load:

* **CacheDescripciones**: Caches product descriptions with time-to-live functionality

### 3.4 Thread Management

#### 3.4.1 Threading Architecture

The application uses multiple threads to maintain UI responsiveness while performing background operations:

1. **Main Thread**: Handles UI rendering and user interaction
2. **Monitoring Thread**: Continuously checks for favorite products with low stock
3. **Scheduler Thread**: Checks for and processes scheduled message deliveries
4. **Stock Update Thread**: Periodically refreshes stock information

#### 3.4.2 Thread Safety Considerations

The application implements several patterns for thread safety:

1. **Thread-Local Database Connections**: Each thread maintains its own database connection
2. **UI Update Queue**: All UI updates from background threads are queued to the main thread
3. **Database Transaction Management**: All database operations use proper transaction handling
4. **Status Flags**: Flags like `self.enviando` prevent overlapping operations

### 3.5 Error Handling Architecture

The application implements a structured error handling approach:

1. **Error Code Enumeration**: The `ErrorCode` enum defines standardized error codes and descriptions
2. **Exception Propagation**: Errors bubble up through the layers with added context
3. **User Feedback**: Errors are presented to users via the NotificationManager
4. **Audit Logging**: All errors are logged with user context and error codes
5. **Graceful Degradation**: Critical components have fallback mechanisms

This multi-layered error handling ensures that:

* Technical details are logged for administrators
* Users receive appropriate feedback
* The application can continue functioning when non-critical components fail

## 4. Class and Method Descriptions

This section provides detailed documentation for the major classes in the application, including their purpose, attributes, methods, and usage examples.

### 4.1 DatabaseApp

**Purpose:** The main application class that initializes and coordinates all components of the system. It serves as the central controller that manages the user interface, business logic, and integrates the various subsystems.

#### 4.1.1 Key Attributes

| Attribute              | Type                       | Description                                |
| ---------------------- | -------------------------- | ------------------------------------------ |
| `root`                 | `tk.Tk`                    | Main Tkinter window object                 |
| `db_manager`           | `DatabaseManager`          | Database connection and query manager      |
| `cred_manager`         | `SecureCredentialsManager` | Credentials encryption/decryption manager  |
| `session`              | `SessionManager`           | User session management                    |
| `audit_log`            | `AuditLogger`              | System for audit logging                   |
| `cache`                | `CacheDescripciones`       | Cache for product descriptions             |
| `notification_manager` | `NotificationManager`      | UI notification system                     |
| `programador`          | `ProgramadorEnvios`        | Scheduled message delivery manager         |
| `enviando`             | `bool`                     | Flag indicating if messages are being sent |
| `buttons`              | `dict`                     | Collection of UI button references         |

#### 4.1.2 Core Methods

**`__init__(self, root)`**

Initializes the application and all its components.

Parameters:

* `root` (tk.Tk): The main Tkinter window

```python
root = tk.Tk()
app = DatabaseApp(root)
root.mainloop()
```

**`attempt_auto_connect(self)`**

Attempts to connect to the database using stored credentials.

Returns:

* None

```python
# This is called automatically during initialization
# Manual call example:
app.attempt_auto_connect()
```

**`log(self, message: str, level: str = 'INFO')`**

Logs a message to the application's log panel.

Parameters:

* `message` (str): The message to log
* `level` (str): Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'SUCCESS')

```python
app.log("Operation completed successfully", "SUCCESS")
app.log("Error connecting to database", "ERROR")
```

**`setup_modern_ui(self)`**

Configures the application's user interface components.

Returns:

* None

**`enviar_mensaje_whatsapp(self, numero_cliente: str, productos: list = None, tipo_envio: str = None) -> bool`**

Sends a WhatsApp message to a client.

Parameters:

* `numero_cliente` (str): Client's phone number
* `productos` (list, optional): List of product descriptions
* `tipo_envio` (str, optional): Message type ('ENTREGA', 'DISPONIBILIDAD', or None for stock alerts)

Returns:

* `bool`: True if successful, False otherwise

```python
# Send a stock alert
success = app.enviar_mensaje_whatsapp("04141234567", ["Producto A", "Producto B"])

# Send a delivery reminder
success = app.enviar_mensaje_whatsapp("04141234567", tipo_envio="ENTREGA")
```

**`actualizar_alertas_stock(self, force_refresh=False)`**

Updates the stock alerts display with current data.

Parameters:

* `force_refresh` (bool): Force a database refresh instead of using cached data

Returns:

* None

```python
# Normal refresh using cache if available
app.actualizar_alertas_stock()

# Force a database refresh
app.actualizar_alertas_stock(force_refresh=True)
```

#### 4.1.3 UI Management Methods

**`setup_records_tab(self)`**, **`setup_messaging_tab(self)`**, **`setup_stats_tab(self)`**, **`setup_calendar_tab(self)`**, **`setup_stock_tab(self)`**

These methods initialize the respective tabs in the user interface.

**`create_header(self)`**, **`create_sidebar(self)`**, **`create_main_workspace(self)`**, **`create_status_panel(self)`**

These methods create the main structural components of the user interface.

#### 4.1.4 Database Operation Methods

**`search_records(self)`**, **`save_record(self)`**, **`update_record(self)`**, **`delete_record(self)`**

These methods handle the basic CRUD operations for client records.

#### 4.1.5 Implementation Notes

* The DatabaseApp class follows a modular design where UI components are created by dedicated methods
* Event handlers are bound to UI elements during initialization
* Background threads are started during initialization and run for the application lifetime
* The class serves as the main integration point between all subsystems

### 4.2 DatabaseManager

**Purpose:** Manages database connections, query execution, and schema maintenance. Provides an abstraction layer over the raw database operations.

#### 4.2.1 Key Attributes

| Attribute          | Type                        | Description                         |
| ------------------ | --------------------------- | ----------------------------------- |
| `conn`             | `pyodbc.Connection`         | Active database connection          |
| `cursor`           | `pyodbc.Cursor`             | Database cursor for query execution |
| `connected_server` | `str`                       | Name of the connected server        |
| `config`           | `configparser.ConfigParser` | Configuration parser                |

#### 4.2.2 Core Methods

**`connect(self, server, database, user, password)`**

Establishes a connection to the SQL Server database.

Parameters:

* `server` (str): SQL Server hostname or IP address
* `database` (str): Database name
* `user` (str): Username (empty for Windows authentication)
* `password` (str): Password (empty for Windows authentication)

Returns:

* `bool`: True if connected successfully

Raises:

* `Exception`: If connection fails

```python
try:
    db_manager = DatabaseManager()
    connected = db_manager.connect("localhost\\SQLEXPRESS", 
                                  "ClientManagementDB", 
                                  "user", "password")
    print(f"Connected: {connected}")
except Exception as e:
    print(f"Connection error: {str(e)}")
```

**`fetch_data(self, query, params=None)`**

Executes a SELECT query and returns the results.

Parameters:

* `query` (str): SQL query string
* `params` (tuple, optional): Query parameters

Returns:

* `list`: List of result tuples

Raises:

* `Exception`: If query execution fails or no connection exists

```python
try:
    results = db_manager.fetch_data(
        "SELECT * FROM clientes WHERE numero_cliente LIKE ?", 
        ("%12345%",)
    )
    for row in results:
        print(row)
except Exception as e:
    print(f"Query error: {str(e)}")
```

**`execute_query(self, query, params=None)`**

Executes an action query (INSERT, UPDATE, DELETE, etc.).

Parameters:

* `query` (str): SQL query string
* `params` (tuple, optional): Query parameters

Returns:

* `bool`: True if successful

Raises:

* `Exception`: If query execution fails

```python
try:
    success = db_manager.execute_query(
        "INSERT INTO clientes (numero_cliente, C_CODIGO) VALUES (?, ?)",
        ("12345678", "ABC123")
    )
    print(f"Query executed successfully: {success}")
except Exception as e:
    print(f"Query error: {str(e)}")
```

**`create_table(self)`**

Creates the necessary database tables if they don't exist.

Returns:

* None

Raises:

* `Exception`: If table creation fails

**`table_exists(self, table_name: str) -> bool`**

Checks if a table exists in the database.

Parameters:

* `table_name` (str): Name of the table to check

Returns:

* `bool`: True if the table exists

```python
if db_manager.table_exists("clientes"):
    print("Clientes table exists")
else:
    print("Clientes table does not exist")
```

#### 4.2.3 Implementation Notes

* The class uses parameterized queries to prevent SQL injection
* Automatic database creation if it doesn't exist
* Automatic table creation with appropriate schema
* Transaction management with commit/rollback
* Connection state validation before operations

### 4.3 SecureCredentialsManager

**Purpose:** Manages secure storage, encryption, and retrieval of sensitive credentials using system keychain and Fernet symmetric encryption.

#### 4.3.1 Key Attributes

| Attribute      | Type    | Description                     |
| -------------- | ------- | ------------------------------- |
| `service_name` | `str`   | Keyring service name identifier |
| `key`          | `bytes` | Encryption key for Fernet       |

#### 4.3.2 Core Methods

**`__init__(self)`**

Initializes the credential manager and retrieves or creates the encryption key.

**`get_or_create_key(self)`**

Retrieves the existing encryption key or generates a new one.

Returns:

* `bytes`: The encryption key

**`encrypt(self, data)`**

Encrypts the provided data.

Parameters:

* `data` (str): Data to encrypt

Returns:

* `str`: Encrypted data as a string

Raises:

* `Exception`: If encryption fails

```python
cred_manager = SecureCredentialsManager()
try:
    encrypted = cred_manager.encrypt("my_secret_password")
    print(f"Encrypted: {encrypted}")
except Exception as e:
    print(f"Encryption error: {str(e)}")
```

**`decrypt(self, encrypted_data)`**

Decrypts the provided data.

Parameters:

* `encrypted_data` (str): Encrypted data to decrypt

Returns:

* `str`: Decrypted data

Raises:

* `Exception`: If decryption fails

```python
try:
    decrypted = cred_manager.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
except Exception as e:
    print(f"Decryption error: {str(e)}")
```

**`store_temp_password(self, password)`**

Stores a temporary password in the system keychain.

Parameters:

* `password` (str): Password to store

Returns:

* None

**`get_temp_password(self)`**

Retrieves the temporary password from the system keychain.

Returns:

* `str` or `None`: Decrypted password or None if not found

```python
# Store password
cred_manager.store_temp_password("SecurePassword123")

# Later, retrieve password
password = cred_manager.get_temp_password()
```

**`store_whatsapp_token(self, token)`**, **`get_whatsapp_token(self)`**

Methods to store and retrieve the WhatsApp API token securely.

#### 4.3.3 Implementation Notes

* Uses the system keychain via the keyring library for master key storage
* Uses Fernet symmetric encryption for data protection
* Keys are generated automatically on first use
* Temporary passwords are cleared when the session expires

### 4.4 SessionManager

**Purpose:** Manages user session state, including activity tracking and timeout handling.

#### 4.4.1 Key Attributes

| Attribute        | Type    | Description                               |
| ---------------- | ------- | ----------------------------------------- |
| `root`           | `tk.Tk` | Main application window                   |
| `last_activity`  | `float` | Timestamp of last user activity           |
| `timeout`        | `int`   | Session timeout in seconds (default: 900) |
| `session_active` | `bool`  | Flag indicating if session is active      |
| `after_id`       | `str`   | ID of scheduled timeout check             |

#### 4.4.2 Core Methods

**`__init__(self, root: tk.Tk) -> None`**

Initializes the session manager.

Parameters:

* `root` (tk.Tk): Main application window

**`update_activity(self, event=None)`**

Updates the last activity timestamp when user interaction occurs.

Parameters:

* `event` (Event, optional): Tkinter event object

Returns:

* None

**`start_session(self)`**

Starts a new user session and initiates activity monitoring.

Returns:

* None

**`check_activity(self)`**

Periodically checks for user activity and handles session timeout.

Returns:

* None

**`expire_session(self)`**

Terminates the user session when timeout occurs, cleans up resources, and closes the application.

Returns:

* None

```python
# Create session manager (typically done by DatabaseApp)
session_manager = SessionManager(root_window)

# Start monitoring for user activity
session_manager.start_session()

# Reset timeout timer (called on user activity)
session_manager.update_activity()
```

#### 4.4.3 Implementation Notes

* User activity is monitored through Tkinter event bindings (key press, mouse movements, clicks)
* The session timeout is set to 15 minutes (900 seconds) by default
* Scheduled check runs every second to evaluate session expiration
* When a session expires, secure credentials are removed from memory
* Uses Tkinter's `after()` method for scheduling timeout checks

### 4.5 EnvioProgramado

**Purpose:** Manages the scheduling of client messages for future delivery. This class handles the storage and tracking of scheduled message delivery tasks.

#### 4.5.1 Key Attributes

| Attribute    | Type              | Description                                        |
| ------------ | ----------------- | -------------------------------------------------- |
| `db_manager` | `DatabaseManager` | Database connection for storing scheduled messages |

#### 4.5.2 Core Methods

**`__init__(self, db_manager)`**

Initializes the scheduled message manager.

Parameters:

* `db_manager` (DatabaseManager): Database manager instance

**`programar_envio(self, numero_cliente, fecha)`**

Schedules a message for future delivery.

Parameters:

* `numero_cliente` (str): Client's phone number
* `fecha` (datetime): Scheduled date and time for message delivery

Returns:

* `bool`: True if scheduling was successful

```python
# Create instance
envio_programado = EnvioProgramado(db_manager)

# Schedule a message for tomorrow
from datetime import datetime, timedelta
fecha_manana = datetime.now() + timedelta(days=1)
success = envio_programado.programar_envio("04141234567", fecha_manana)

if success:
    print("Message scheduled successfully")
else:
    print("Failed to schedule message")
```

#### 4.5.3 Implementation Notes

* Messages are stored in the `envios_programados` database table
* Default status for new scheduled messages is 'PENDIENTE' (pending)
* The implementation delegates database operations to the DatabaseManager
* Error handling includes logging failures but continuing execution

### 4.6 ProgramadorEnvios

**Purpose:** Continuously monitors for scheduled messages that are due for delivery and processes them. This class runs in a background thread to periodically check for pending messages.

#### 4.6.1 Key Attributes

| Attribute    | Type               | Description                                        |
| ------------ | ------------------ | -------------------------------------------------- |
| `db_manager` | `DatabaseManager`  | Database manager for querying scheduled messages   |
| `app`        | `DatabaseApp`      | Reference to main application for sending messages |
| `hilo`       | `threading.Thread` | Background thread for monitoring                   |

#### 4.6.2 Core Methods

**`__init__(self, db_manager, app)`**

Initializes the message scheduler and starts the monitoring thread.

Parameters:

* `db_manager` (DatabaseManager): Database manager instance
* `app` (DatabaseApp): Main application instance

**`verificar_envios(self)`**

Continuously checks for pending scheduled messages that need to be sent.

Returns:

* None

**`verificar_recordatorios(self)`**

Checks for upcoming scheduled deliveries and sends reminder messages.

Returns:

* None

```python
# This is automatically created during DatabaseApp initialization
programador = ProgramadorEnvios(db_manager, app)

# The thread runs continuously in the background
# No need for manual intervention after initialization
```

#### 4.6.3 Implementation Notes

* Runs in a daemon thread that automatically terminates when the application closes
* Periodic checks run every 60 seconds for pending messages
* Handles database disconnections gracefully by continuing to retry
* Sends reminders 24 hours before scheduled delivery
* All operations are logged for auditing and troubleshooting

### 4.7 AuditLogger

**Purpose:** Provides a centralized logging system for security-relevant events in the application. Maintains an audit trail of user actions, system events, and error conditions.

#### 4.7.1 Key Attributes

| Attribute | Type             | Description            |
| --------- | ---------------- | ---------------------- |
| `logger`  | `logging.Logger` | Python logger instance |

#### 4.7.2 Core Methods

**`__init__(self)`**

Initializes the audit logging system.

**`log_event(self, action, user, status, error_code=None)`**

Logs an audit event with user context and optional error information.

Parameters:

* `action` (str): The action being performed
* `user` (str): The username performing the action
* `status` (str): Outcome status (SUCCESS, FAILED, etc.)
* `error_code` (ErrorCode, optional): Error code enum if applicable

Returns:

* None

```python
# Create logger
audit_log = AuditLogger()

# Log successful action
audit_log.log_event(
    "LOGIN", 
    "admin_user", 
    "SUCCESS"
)

# Log failed action with error code
from pal.core.errors import ErrorCode
audit_log.log_event(
    "DATABASE_OPERATION", 
    "regular_user", 
    "FAILED",
    ErrorCode.DB_QUERY_EXECUTION
)
```

#### 4.7.3 Implementation Notes

* Uses Python's built-in logging module with rotating file handler
* Log files are limited to 5MB with 3 backup files
* UTF-8 encoding ensures proper handling of international characters
* Standardized log format includes timestamp, log level, and message
* Error codes provide consistent error reporting and categorization

### 4.8 UI Helper Classes

#### 4.8.1 NotificationManager

**Purpose:** Manages the display of notifications and alerts to the user in a consistent format.

**Key Attributes**

| Attribute | Type    | Description                              |
| --------- | ------- | ---------------------------------------- |
| `root`    | `tk.Tk` | Reference to the main application window |

**Core Methods**

**`__init__(self, root)`**

Initializes the notification manager.

Parameters:

* `root` (tk.Tk): The main application window

**`show_success(self, message)`**

Displays a success notification to the user.

Parameters:

* `message` (str): Message to display

Returns:

* None

**`show_error(self, message)`**

Displays an error notification to the user.

Parameters:

* `message` (str): Error message to display

Returns:

* None

**`_show_notification(self, title, message, color)`**

Internal method to display a notification with specified styling.

Parameters:

* `title` (str): Notification title
* `message` (str): Notification message
* `color` (str): Background color for notification

Returns:

* None

```python
# Get reference from DatabaseApp
notification_manager = app.notification_manager

# Show success notification
notification_manager.show_success("Operation completed successfully")

# Show error notification
notification_manager.show_error("Failed to connect to the database")
```

**Implementation Notes**

* Notifications appear as small popup windows near the top-right corner
* Notifications auto-dismiss after 3 seconds
* Uses Tkinter Toplevel windows with custom styling
* Different visual styling for different notification types

#### 4.8.2 HelpTooltips

**Purpose:** Provides contextual help tooltips for UI elements to enhance user experience.

**Key Attributes**

| Attribute        | Type          | Description                              |
| ---------------- | ------------- | ---------------------------------------- |
| `root`           | `tk.Tk`       | Reference to the main application window |
| `tooltip_window` | `tk.Toplevel` | Current tooltip window if active         |

**Core Methods**

**`__init__(self, root)`**

Initializes the tooltip manager.

Parameters:

* `root` (tk.Tk): The main application window

**`add_tooltip(self, widget, text)`**

Adds a tooltip to a specific widget.

Parameters:

* `widget` (tk.Widget): The widget to add tooltip to
* `text` (str): Tooltip text

Returns:

* None

**`show_tooltip(self, widget, text)`**

Displays a tooltip near the specified widget.

Parameters:

* `widget` (tk.Widget): The widget to show tooltip for
* `text` (str): Tooltip text

Returns:

* None

**`hide_tooltip(self)`**

Hides the currently displayed tooltip.

Returns:

* None

```python
# Get reference from DatabaseApp
help_tooltips = app.help_tooltips

# Add tooltip to a button
help_tooltips.add_tooltip(
    my_button, 
    "Click this button to save the current record"
)
```

**Implementation Notes**

* Tooltips are triggered by mouse hover events
* Tooltips are positioned near the widget they describe
* Uses Tkinter event bindings for mouse enter/leave events
* Tooltip windows have a light yellow background with a simple border

### 4.9 CacheDescripciones

**Purpose:** Implements a time-based caching mechanism for product descriptions to reduce database load and improve application performance.

#### 4.9.1 Key Attributes

| Attribute | Type   | Description                             |
| --------- | ------ | --------------------------------------- |
| `cache`   | `dict` | Dictionary storing cached descriptions  |
| `ttl`     | `int`  | Time-to-live in seconds for cache items |

#### 4.9.2 Core Methods

**`__init__(self, ttl=3600)`**

Initializes the cache with specified time-to-live.

Parameters:

* `ttl` (int): Cache time-to-live in seconds (default: 1 hour)

**`obtener(self, codigo)`**

Retrieves a description from the cache if available and not expired.

Parameters:

* `codigo` (str): Product code

Returns:

* `str` or `None`: Cached description or None if not found/expired

**`guardar(self, codigo, descripcion)`**

Stores a description in the cache with the current timestamp.

Parameters:

* `codigo` (str): Product code
* `descripcion` (str): Product description

Returns:

* None

```python
# Create cache with 30 minute TTL
cache = CacheDescripciones(ttl=1800)

# Try to get from cache first
descripcion = cache.obtener("ABC123")

if descripcion is None:
    # Not in cache, get from database
    descripcion = db_manager.fetch_data(
        "SELECT C_DESCRI FROM MA_PRODUCTOS WHERE C_CODIGO = ?", 
        ("ABC123",)
    )[0][0]
    
    # Store in cache for future use
    cache.guardar("ABC123", descripcion)

print(f"Product: {descripcion}")
```

#### 4.9.3 Implementation Notes

* Simple in-memory cache with time-based expiration
* Cache items include the value and a timestamp for TTL calculation
* Default TTL is 1 hour (3600 seconds)
* No maximum size limit (relies on Python's memory management)
* Thread-safe for basic operations (read/write)

## 5. Database Schema & Management

### 5.1 Database Overview

The Client Management System uses a SQL Server database to store client information, product data, scheduled messages, and application configuration. The database schema is designed to support the core functionality of tracking client-product relationships, monitoring inventory levels, and scheduling automated communications.

The application automatically creates the necessary database and tables during initial connection if they don't exist, making setup simple for new installations.

### 5.2 Database Schema

#### 5.2.1 Core Tables

The following diagram illustrates the primary tables and their relationships:

```
┌───────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ clientes      │     │favoritos_productos│     │envios_programados│
├───────────────┤     ├───────────────────┤     ├──────────────────┤
│ id            │     │ codigo      (PK)  │     │ id                │
│ numero_cliente│────┐│ favorito          │     │ numero_cliente    │──┐
│ C_CODIGO      │─┐  ││ fecha_creacion    │     │ fecha_programada  │  │
└───────────────┘ │  │└───────────────────┘     │ fecha_creacion    │  │
                  │  │                          │ estado            │  │
                  │  │                          │ tipo_envio        │  │
                  │  │                          └────────────────── ┘  │
                  │  │                                                 │
                  ▼  │                                                 │
┌───────────────┐    │                                                 │
│ MA_PRODUCTOS  │    │           Logical Relationships                 │
├───────────────┤    │                                                 │
│ C_CODIGO (PK) │◄───┘                                                 │
│ C_DESCRI      │                                                      │
└───────────────┘                                                      │
        │                                                              │
        ▼                                                              │
┌───────────────┐                                                      │
│ MA_DEPOPROD   │                                                      │
├───────────────┤                                                      │
│ c_codarticulo │                                                      │
│ c_coddeposito │                                                      │
│ n_cantidad    │                                                      │
└───────────────┘                                                      │
                                                                       │
┌───────────────┐                                                      │
│ TEMP_ENVIO    │                                                      │
├───────────────┤                                                      │
│ numero_cliente│◄────────────────────────────────────────────────────┘
│ codigo_producto│
│ descripcion    │
│ timestamp      │
└───────────────┘
```

#### 5.2.2 Table Definitions

**clientes**

Stores the relationship between client numbers and product codes.

```sql
CREATE TABLE clientes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    numero_cliente NVARCHAR(50) NOT NULL,
    C_CODIGO NVARCHAR(15) NOT NULL
);

CREATE INDEX idx_clientes_numero ON clientes (numero_cliente);
CREATE INDEX idx_clientes_codigo ON clientes (C_CODIGO);
```

**favoritos\_productos**

Tracks which products are marked as favorites for monitoring.

```sql
CREATE TABLE favoritos_productos (
    codigo NVARCHAR(15) PRIMARY KEY,
    favorito BIT DEFAULT 0,
    fecha_creacion DATETIME DEFAULT GETDATE()
);
```

**envios\_programados**

Manages scheduled message deliveries to clients.

```sql
CREATE TABLE envios_programados (
    id INT IDENTITY(1,1) PRIMARY KEY,
    numero_cliente NVARCHAR(50) NOT NULL,
    fecha_programada DATETIME NOT NULL,
    fecha_creacion DATETIME DEFAULT GETDATE(),
    estado NVARCHAR(20) DEFAULT 'PENDIENTE',
    tipo_envio NVARCHAR(20) NOT NULL 
        CHECK (tipo_envio IN ('ENTREGA', 'DISPONIBILIDAD'))
);

CREATE INDEX idx_envios_fecha_estado ON envios_programados (fecha_programada, estado);
CREATE INDEX idx_envios_numero ON envios_programados (numero_cliente);
```

**TEMP\_ENVIO**

Temporary table used during bulk message sending operations.

```sql
CREATE TABLE TEMP_ENVIO (
    numero_cliente NVARCHAR(50),
    codigo_producto NVARCHAR(15),
    descripcion NVARCHAR(255),
    timestamp DATETIME DEFAULT GETDATE()
);
```

**External Tables (Referenced)**

The application also interacts with existing external tables in the database:

* `MA_PRODUCTOS`: Product master table containing product codes and descriptions
* `MA_DEPOPROD`: Product inventory table with stock quantities by warehouse

### 5.3 Key Database Operations

#### 5.3.1 Client Management Operations

**Adding a New Client**

```sql
INSERT INTO clientes (numero_cliente, C_CODIGO) VALUES (?, ?);
```

**Finding Clients by Number or Product Code**

```sql
SELECT id, numero_cliente, C_CODIGO FROM clientes
WHERE numero_cliente LIKE ? AND C_CODIGO LIKE ?;
```

**Updating Client Product Association**

```sql
UPDATE clientes SET numero_cliente = ?, C_CODIGO = ? WHERE id = ?;
```

**Removing a Client**

```sql
DELETE FROM clientes WHERE id = ?;
```

#### 5.3.2 Inventory Monitoring Operations

**Retrieving Stock Alerts**

```sql
SELECT 
    c_codarticulo AS codigo,
    MAX(p.C_DESCRI) AS descripcion,
    CAST(SUM(n_cantidad) AS INT) AS stock,  
    CASE
        WHEN SUM(n_cantidad) BETWEEN 15 AND 20 THEN 'Leve'  
        WHEN SUM(n_cantidad) BETWEEN 8 AND 14 THEN 'Media'
        ELSE 'Crítica'
    END AS nivel
FROM MA_DEPOPROD d
    INNER JOIN MA_PRODUCTOS p ON d.c_codarticulo = p.C_CODIGO
    WHERE c_coddeposito = '0301'
    GROUP BY c_codarticulo
    HAVING SUM(n_cantidad) < 21  
    ORDER BY stock ASC;
```

**Managing Favorite Products**

```sql
MERGE INTO favoritos_productos AS target
USING (VALUES (?)) AS source(codigo)
ON target.codigo = source.codigo
WHEN MATCHED THEN
   UPDATE SET favorito = ~favorito
WHEN NOT MATCHED THEN
   INSERT (codigo, favorito) VALUES (source.codigo, 1);
```

**Retrieving Favorite Products with Low Stock**

```sql
SELECT 
    d.c_codarticulo AS codigo,
    SUM(d.n_cantidad) AS stock,
    CASE
        WHEN SUM(d.n_cantidad) BETWEEN 15 AND 20 THEN 'Leve'  
        WHEN SUM(d.n_cantidad) BETWEEN 8 AND 14 THEN 'Media'
        ELSE 'Crítica'
    END AS nivel
FROM MA_DEPOPROD d
INNER JOIN favoritos_productos f ON d.c_codarticulo = f.codigo
WHERE d.c_coddeposito = '0301' AND f.favorito = 1
GROUP BY d.c_codarticulo
HAVING SUM(d.n_cantidad) < 21;
```

#### 5.3.3 Message Scheduling Operations

**Scheduling a New Message**

```sql
INSERT INTO envios_programados (numero_cliente, fecha_programada, tipo_envio, estado)
VALUES (?, ?, ?, 'PENDIENTE');
```

**Finding Due Messages**

```sql
SELECT id, numero_cliente FROM envios_programados
WHERE fecha_programada <= ? AND estado = 'PENDIENTE';
```

**Finding Upcoming Messages for Reminders**

```sql
SELECT id, numero_cliente, tipo_envio FROM envios_programados
WHERE fecha_programada BETWEEN ? AND ? AND estado = 'PENDIENTE';
```

**Updating Message Status After Sending**

```sql
UPDATE envios_programados SET estado = 'ENVIADO' WHERE id = ?;
```

### 5.4 SQL Injection Prevention

The application employs several techniques to prevent SQL injection attacks:

#### 5.4.1 Parameterized Queries

All database operations use parameterized queries via the `pyodbc` library's parameter substitution mechanism:

```python
self.cursor.execute(
    "SELECT * FROM clientes WHERE numero_cliente = ?", 
    (numero_cliente,)
)
```

#### 5.4.2 Input Validation

User inputs are validated before being used in database operations:

```python
if not re.match(r'^\d{1,11}$', num):
    self.audit_log.log_event(
        "INVALID_CLIENT_NUMBER", os.getlogin(), "FAILED",
        ErrorCode.INVALID_CLIENT_NUMBER
    )
    messagebox.showwarning("Error", str(ErrorCode.INVALID_CLIENT_NUMBER))
    return False
```

#### 5.4.3 Pattern Checking for Malicious Input

The application checks for common SQL injection patterns in user input:

```python
dangerous_patterns = [r";.*--", r"/\*.*\*/", r"xp_", r"exec\(", r"union.*select"]
for field, value in inputs.items():
    if any(re.search(pattern, value, re.IGNORECASE) for pattern in dangerous_patterns):
        self.audit_log.log_event(
            f"DANGEROUS_INPUT_{field}", os.getlogin(), "FAILED",
            ErrorCode.DANGEROUS_INPUT
        )
        self.notification_manager.show_warning("Error", str(ErrorCode.DANGEROUS_INPUT))
        return False
```

### 5.5 Transaction Management

The application handles database transactions to ensure data integrity:

#### 5.5.1 Automatic Commit/Rollback

Each database modification operation automatically commits on success and rolls back on failure:

```python
def execute_query(self, query, params=None):
    try:
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.conn.commit()
        return True
    except pyodbc.Error as e:
        self.conn.rollback()
        error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
        raise Exception(error_msg) from e
```

#### 5.5.2 Table Creation Transactions

The table creation process uses implicit transactions to ensure all schema modifications are atomic:

```python
def create_table(self):
    try:
        # Create tables with indexes
        self.cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='clientes' AND xtype='U')
            CREATE TABLE clientes (
                ...
            );
            ...
        """)
        self.conn.commit()
        
        # Additional tables...
        self.conn.commit()
    except pyodbc.Error as e:
        self.conn.rollback()
        error_msg = f"{ErrorCode.DB_TABLE_CREATION}: {str(e)}"
        raise Exception(error_msg) from e
```

### 5.6 Error Handling Strategies

The application implements robust error handling for database operations:

#### 5.6.1 Connection Error Handling

Before any database operation, the application verifies if a connection exists:

```python
if not self.conn:
    error_msg = f"{ErrorCode.DB_CONNECTION_FAILED}: No hay conexión activa"
    raise Exception(error_msg)
```

#### 5.6.2 Standardized Error Codes

Database errors are mapped to standardized error codes:

```python
except pyodbc.Error as e:
    error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
    raise Exception(error_msg) from e
```

#### 5.6.3 Graceful Fallbacks

Background processes handle database errors gracefully to prevent application crashes:

```python
try:
    # Database operations
    ...
except Exception as e:
    self.app.log(f"Error en programador: {str(e)}", "ERROR")
time.sleep(60)  # Continue retry after delay
```

#### 5.6.4 Error Auditing

All database errors are logged for later investigation:

```python
self.audit_log.log_event(
    "DATABASE_OPERATION",
    os.getlogin(),
    "FAILED",
    ErrorCode.DB_QUERY_EXECUTION
)
```

## 6. Configuration & Security Considerations

### 6.1 Credential Storage and Encryption

The application implements a robust credential management system to secure sensitive information such as database passwords and API tokens.

#### 6.1.1 Encryption Architecture

![Encryption Architecture](encryption_architecture.png)

_Note: Insert actual encryption flow diagram here._

The encryption system uses a two-tier approach:

1. **Master Key Storage**
   * The master encryption key is stored in the system's secure keychain using the `keyring` library
   * On Windows, this leverages the Windows Credential Manager
   * The key is identified by the service name "DBClientApp" and username "encryption\_key"
2. **Data Encryption**
   * User credentials and API tokens are encrypted using the Fernet symmetric encryption algorithm
   * Fernet provides authenticated encryption ensuring data cannot be modified without detection
   * The encrypted values are stored in configuration files or temporary session storage

#### 6.1.2 Key Management

**Key Generation**

The master encryption key is generated during first use if it doesn't exist:

```python
def get_or_create_key(self):
    key = keyring.get_password(self.service_name, "encryption_key")
    if not key:    
        key = Fernet.generate_key().decode()
        keyring.set_password(self.service_name, "encryption_key", key)  
    return key.encode()
```

**Key Rotation**

For security purposes, it's recommended to rotate the encryption key periodically:

1. Manually delete the key from the system keychain
2. Delete the `db_config.ini` file
3. Restart the application, which will generate a new key
4. Re-enter database and API credentials

#### 6.1.3 Password Management

**Temporary Password Storage**

Database passwords are never stored in plain text. During an active session, the password is temporarily stored in an encrypted format:

```python
def store_temp_password(self, password):
    if password:
        encrypted = self.encrypt(password)
        keyring.set_password(self.service_name, "temp_pass", encrypted)
```

**Password Retrieval**

```python
def get_temp_password(self):
    encrypted = keyring.get_password(self.service_name, "temp_pass")
    return self.decrypt(encrypted) if encrypted else None
```

**Password Disposal**

When a session expires, temporary passwords are automatically removed from memory:

```python
def expire_session(self):
    try:
        if keyring.get_password("DBClientApp", "temp_pass"):
            keyring.delete_password("DBClientApp", "temp_pass")
    except Exception as e:
        print(f"Error eliminando contraseña temporal: {str(e)}")
```

### 6.2 Session Management

The application implements a session management system to control user access and automatically terminate inactive sessions.

#### 6.2.1 Session Lifecycle

1. **Session Initialization**
   * A new session is started when the application launches
   * Initial activity timestamp is recorded
   * Event bindings for user activity are established
2. **Activity Monitoring**
   * User interactions (keyboard, mouse) reset the inactivity timer
   * A background task checks for inactivity every second
3. **Session Termination**
   * After 15 minutes (configurable) of inactivity, the session expires
   * Temporary credentials are securely removed from memory
   * The application exits with a notification to the user

#### 6.2.2 Implementation Details

**User Activity Detection**

The SessionManager binds to Tkinter events to detect user activity:

```python
root.bind("<Key>", self.update_activity)
root.bind("<Button>", self.update_activity)
root.bind("<Motion>", self.update_activity)
```

**Inactivity Monitoring**

Regular checks compare the current time against the last activity timestamp:

```python
def check_activity(self):
    if self.session_active and (time.time() - self.last_activity) > self.timeout:
        self.expire_session()
    elif self.session_active:
        self.after_id = self.root.after(1000, self.check_activity)
```

#### 6.2.3 Session Configuration

The default session timeout is 15 minutes (900 seconds). To modify this timeout:

1.  Edit the `SessionManager` class initialization:

    ```python
    self.timeout = 900  # Change to desired timeout in seconds
    ```
2. Recommended timeout values:
   * Minimum: 300 seconds (5 minutes) for high-security environments
   * Standard: 900 seconds (15 minutes) for normal usage
   * Extended: 1800 seconds (30 minutes) for development or low-risk environments

### 6.3 Input Validation and Sanitization

The application implements multiple layers of input validation and sanitization to protect against malicious input and ensure data integrity.

#### 6.3.1 Client-side Validation

**Format Validation**

Client numbers are validated against specific patterns:

```python
if not re.match(r'^\d{1,11}$', num):
    self.audit_log.log_event(
        "INVALID_CLIENT_NUMBER", os.getlogin(), "FAILED",
        ErrorCode.INVALID_CLIENT_NUMBER
    )
    messagebox.showwarning("Error", str(ErrorCode.INVALID_CLIENT_NUMBER))
    return False
```

**Malicious Pattern Detection**

User inputs are scanned for potential SQL injection patterns:

```python
dangerous_patterns = [r";.*--", r"/\*.*\*/", r"xp_", r"exec\(", r"union.*select"]
for field, value in inputs.items():
    if any(re.search(pattern, value, re.IGNORECASE) for pattern in dangerous_patterns):
        self.audit_log.log_event(
            f"DANGEROUS_INPUT_{field}", os.getlogin(), "FAILED",
            ErrorCode.DANGEROUS_INPUT
        )
        self.notification_manager.show_warning("Error", str(ErrorCode.DANGEROUS_INPUT))
        return False
```

#### 6.3.2 Database Query Protection

**Parameterized Queries**

All database interactions use parameterized queries to prevent SQL injection:

```python
def fetch_data(self, query, params=None):
    try:
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()
    except pyodbc.Error as e:
        error_msg = f"{ErrorCode.DB_QUERY_EXECUTION}: {str(e)}"
        raise Exception(error_msg) from e
```

**Input Cleaning**

For additional security, the application cleans user inputs before database operations:

```python
clean_codigo = re.sub(r'\D', '', codigo)  # Remove non-digits
```

#### 6.3.3 Message Template Security

When sending WhatsApp messages, the application ensures proper sanitization:

```python
# Format and sanitize message content
producto_limpio = re.sub(r'[\n\t]', ' ', str(producto))
if len(producto_limpio) > MAX_LENGTH:
    producto_limpio = producto_limpio[:MAX_LENGTH-3] + "..."
```

### 6.4 Audit Logging

The application implements comprehensive audit logging to track security-relevant events, user actions, and system operations.

#### 6.4.1 Logging Architecture

**Log File Configuration**

Audit logs are stored in a rotating file system to prevent excessive disk usage:

```python
handler = RotatingFileHandler(
    'audit.log',
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3,
    encoding='utf-8'
)
```

**Log Format**

All log entries follow a standardized format:

```
2025-04-11 07:45:23 | INFO | USER: admin | ACTION: LOGIN | STATUS: SUCCESS
```

#### 6.4.2 Logged Events

The application logs the following event types:

1. **Authentication Events**
   * User session starts and expirations
   * Database connection attempts
2. **Data Modification Events**
   * Record creation, updates, and deletions
   * Configuration changes
3. **Security Events**
   * Invalid input attempts
   * Potential SQL injection attempts
   * Session timeouts
4. **System Events**
   * Application startup and shutdown
   * Background thread status
   * API communication status

#### 6.4.3 Log Monitoring Recommendations

For effective security monitoring:

1. **Regular Review**
   * Implement a process for regular log review, especially for FAILED actions
   * Focus on patterns of multiple failed attempts
2. **Log File Protection**
   * Ensure audit.log files have appropriate access restrictions
   * Consider moving logs to a secure, centralized location for larger deployments
3. **Log Retention**
   * The default configuration retains approximately 20MB of logs (main + 3 backups)
   * For compliance requirements, implement additional log archiving

### 6.5 Security Best Practices

#### 6.5.1 Deployment Recommendations

**User Access Control**

1. Run the application under standard user accounts, not administrative accounts
2. Use Windows user restrictions to control who can access the application
3. Implement separate database users for different application deployments

**Network Security**

1. If the database is on a separate server, use encrypted connections
2. Consider using a VPN for database connections across untrusted networks
3. Configure firewall rules to restrict database access to specific hosts

**Application Directory Security**

1. Restrict access to the application directory
2. Ensure only authorized users can access configuration files
3. Protect audit log files from unauthorized modification

#### 6.5.2 Operational Security

**Regular Updates**

1. Keep Python dependencies updated regularly, especially security-related packages
2. Update WhatsApp API tokens as per Meta's recommended rotation schedule
3. Routinely change database credentials as part of security maintenance

**Incident Response**

1. Establish procedures for handling security incidents
2. Maintain backup of configuration prior to any significant changes
3. Document all security-related events and their resolutions

### 6.6 Environment Variable Handling

While the application primarily uses the keychain and encrypted configuration files, sensitive configuration can also be provided via environment variables for automated deployments or enterprise environments.

#### 6.6.1 Supported Environment Variables

| Variable          | Description                       | Default            |
| ----------------- | --------------------------------- | ------------------ |
| `DB_SERVER`       | Database server address           | _Uses config file_ |
| `DB_NAME`         | Database name                     | _Uses config file_ |
| `DB_USER`         | Database username                 | _Uses config file_ |
| `DB_PASS`         | Database password                 | _Uses config file_ |
| `WA_TOKEN`        | WhatsApp API token                | _Uses keychain_    |
| `SESSION_TIMEOUT` | Session timeout in seconds        | 900                |
| `LOG_LEVEL`       | Logging level (DEBUG, INFO, etc.) | INFO               |

#### 6.6.2 Environment Variable Loading

Environment variables are checked during application startup and take precedence over stored configurations:

```python
def load_from_env(self):
    """Priority loading from environment variables."""
    server = os.environ.get('DB_SERVER')
    database = os.environ.get('DB_NAME')
    user = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASS')
    
    if server and database:
        try:
            self.connect(server, database, user, password)
            return True
        except Exception as e:
            self.log(f"Failed to connect with environment variables: {str(e)}", "ERROR")
    
    return False
```

#### 6.6.3 Security Considerations for Environment Variables

When using environment variables, consider these security best practices:

1. **Avoid Persistent Environment Variables**: Set variables only for the application's process
2. **Use Process Isolation**: Run the application in an isolated environment
3. **Restrict Access**: Limit access to the environment configuration
4. **Clear Variables**: Ensure variables are cleared after application termination

## 7. WhatsApp Integration & Messaging Logic

### 7.1 WhatsApp API Integration Architecture

The application integrates with the Meta WhatsApp Business API to send automated notifications to clients. This section describes the architecture and implementation of this integration.

#### 7.1.1 Integration Overview

![WhatsApp Integration Architecture](whatsapp_architecture.png)

_Note: Insert actual architecture diagram here._

The WhatsApp integration follows these key principles:

1. **Token-based Authentication**: Uses an API token stored securely in the system keychain
2. **Template-based Messaging**: Sends pre-approved message templates as required by WhatsApp
3. **HTTP-based Communication**: Uses the requests library to communicate with the WhatsApp API
4. **Asynchronous Operation**: Sends messages in background threads to maintain UI responsiveness

#### 7.1.2 API Endpoint Configuration

The application communicates with the WhatsApp API using the Meta Graph API:

```python
# WhatsApp API endpoint (using Meta Graph API)
API_ENDPOINT = "https://graph.facebook.com/v21.0/490677417472051/messages"
```

#### 7.1.3 Authentication and Security

The application uses a bearer token for authentication with the WhatsApp API:

```python
headers = {
    "Authorization": f"Bearer {whatsapp_token}", 
    "Content-Type": "application/json"
}
```

The token is:

1. Obtained from the Meta Business dashboard by the administrator
2. Stored securely using the `SecureCredentialsManager`
3. Retrieved only when needed for API calls
4. Never logged or exposed in the user interface

### 7.2 Message Template System

WhatsApp Business API requires the use of pre-approved message templates. The application supports three primary template types:

#### 7.2.1 Supported Templates

| Template Name          | Purpose                          | Variables         |
| ---------------------- | -------------------------------- | ----------------- |
| `alerta_stock`         | Stock availability notifications | Product list      |
| `recordatorio_entrega` | Delivery reminders               | None (fixed text) |
| `sede`                 | Store pickup notifications       | None (fixed text) |

#### 7.2.2 Template Selection Logic

The appropriate template is selected based on the `tipo_envio` parameter:

```python
if tipo_envio == "ENTREGA":
    template_name = "recordatorio_entrega"
    texto_plantilla = "📦 Tu entrega está programada para mañana. ¡Estaremos listos!"
elif tipo_envio == "DISPONIBILIDAD":
    template_name = "sede"
    texto_plantilla = "🏪 ¡Tu producto ya está disponible en nuestra sede! Visítanos."
else:
    # For stock alerts
    template_name = "alerta_stock"
    # Build product list...
```

#### 7.2.3 Dynamic Content Generation

For stock notifications, the application dynamically builds the message content:

```python
MAX_ITEMS = 10
MAX_LENGTH = 45
SEPARADOR = " • "

items_procesados = []
for idx, producto in enumerate(productos[:MAX_ITEMS], 1):
    producto_limpio = re.sub(r'[\n\t]', ' ', str(producto))
    if len(producto_limpio) > MAX_LENGTH:
        producto_limpio = producto_limpio[:MAX_LENGTH-3] + "..."
    items_procesados.append(f"{idx}. {producto_limpio}")

texto_plantilla = SEPARADOR.join(items_procesados)
if len(productos) > MAX_ITEMS:
    texto_plantilla += f"{SEPARADOR}... (+{len(productos) - MAX_ITEMS} productos más)"
```

#### 7.2.4 Template JSON Structure

Each WhatsApp message is formatted as a JSON payload:

```python
payload = {
    "messaging_product": "whatsapp",
    "to": numero_formateado,
    "type": "template",
    "template": {
        "name": template_name,
        "language": {"code": "es"},
        "components": [{
            "type": "body",
            "parameters": [{"type": "text", "text": texto_plantilla}]
        }]
    }
}
```

### 7.3 Bulk Messaging Implementation

The application supports sending messages to multiple clients in a batch process.

#### 7.3.1 Bulk Messaging Flow

```
┌─────────────────┐     ┌────────────────┐     ┌───────────────────┐    
│  Start Bulk     │     │  Query Clients │     │ Create Temporary  │    
│  Process        │────▶│  & Products    │────▶│ Table for Batch   │    
└─────────────────┘     └────────────────┘     └───────────────────┘    
         │                                                │             
         │                                                │             
         ▼                                                ▼             
┌─────────────────┐     ┌────────────────┐     ┌───────────────────┐    
│  Process Each   │     │  Send WhatsApp │     │  Update UI and    │    
│  Client         │◀───▶│  Message       │────▶│  Progress Bar     │    
└─────────────────┘     └────────────────┘     └───────────────────┘    
         │                                                │             
         │                                                │             
         ▼                                                ▼             
┌─────────────────┐                             ┌───────────────────┐    
│  Delay Between  │                             │  Clean Up Temp    │    
│  Messages       │                             │  Table            │    
└─────────────────┘                             └───────────────────┘    
```

#### 7.3.2 Temporary Database Storage

To efficiently manage large batches, clients and product data are temporarily stored in a database table:

```python
self.db_manager.execute_query("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'TEMP_ENVIO')
CREATE TABLE TEMP_ENVIO (
    numero_cliente NVARCHAR(50),
    codigo_producto NVARCHAR(15),
    descripcion NVARCHAR(255),
    timestamp DATETIME DEFAULT GETDATE()
)
""")
```

#### 7.3.3 Client and Product Selection

The system queries the database to identify clients and their products with available stock:

```python
for numero, codigos in self.clientes_lista:
    for codigo in codigos:
        cantidad_result = self.db_manager.fetch_data(
            "SELECT n_cantidad FROM MA_DEPOPROD WHERE c_codarticulo = ? AND c_coddeposito = '0301'",
            (codigo,)
        )
        if cantidad_result and cantidad_result[0][0] > 0:
            desc_result = self.db_manager.fetch_data(
                "SELECT C_DESCRI FROM MA_PRODUCTOS WHERE C_CODIGO = ?",
                (codigo,)
            )
            if desc_result:
                self.db_manager.execute_query(
                    "INSERT INTO TEMP_ENVIO (numero_cliente, descripcion) VALUES (?, ?)",
                    (numero, desc_result[0][0])
                )
```

#### 7.3.4 Rate Limiting and Throttling

To prevent API rate limit issues, the application implements a delay between messages:

```python
# Process next client after 7 seconds
self.root.after(7000, self.procesar_envio_masivo)
```

#### 7.3.5 Progress Tracking and UI Updates

A progress bar and status messages keep the user informed during bulk operations:

```python
# Update progress
self.actual += 1
self.progress["value"] = self.actual
self.lbl_progreso.config(text=f"Enviando {self.actual + 1}/{self.total} | Cliente: {numero}")
```

### 7.4 Error Handling and Retry Mechanisms

The application implements robust error handling to ensure reliable message delivery.

#### 7.4.1 API Communication Errors

WhatsApp API communication errors are handled with structured exception handling:

```python
try:
    response = requests.post(
        "https://graph.facebook.com/v21.0/490677417472051/messages",
        headers={"Authorization": f"Bearer {whatsapp_token}", "Content-Type": "application/json"},
        json=payload
    )

    if response.status_code == 200:
        self.log(f"Mensaje enviado a {numero_formateado}", "SUCCESS")
        return True
    
    # Handle error response
    error_data = response.json().get('error', {})
    error_msg = error_data.get('message', 'Error desconocido')
    self.log(f"Error API: {error_msg}", "ERROR")
    messagebox.showerror("Error API", f"{error_msg}")
    return False

except Exception as e:
    self.log(f"Error crítico: {str(e)}", "ERROR")
    self.audit_log.log_event(
        "ERROR_ENVIO",
        os.getlogin(),
        "CRITICAL",
        error_code=ErrorCode.WHATSAPP_API_FAILURE
    )
    return False
```

#### 7.4.2 Common Error Types and Resolutions

| Error Type             | Description                     | Resolution                                     |
| ---------------------- | ------------------------------- | ---------------------------------------------- |
| Authentication Failure | Invalid or expired token        | Update the WhatsApp API token in settings      |
| Template Not Found     | Template name isn't recognized  | Verify template names in Meta Business Manager |
| Parameter Mismatch     | Template parameters don't match | Review template format and parameter types     |
| Rate Limiting          | Too many requests               |                                                |
