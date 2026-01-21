# GEMINI.md

## Project Overview

This project is a desktop application for customer management, developed in Python. It provides a graphical user interface (GUI) built with Tkinter for managing client information, sending bulk WhatsApp messages, and other related tasks. The application connects to a SQL Server database to store and retrieve data.

### Main Technologies

*   **Language:** Python
*   **GUI:** Tkinter
*   **Database:** SQL Server (via `pyodbc`)
*   **Dependencies:** `cryptography`, `keyring`, `tkcalendar`, `requests`, `matplotlib`, `win10toast`, `Pillow`, `bcrypt`, `packaging`, `pyodbc`

### Architecture

The application follows a modular architecture with the core logic separated into the `pal` directory. This directory is further subdivided into:

*   `core`: Contains the main business logic, including authentication, session management, and permissions.
*   `infrastructure`: Manages the database connection and data access.
*   `services`: Implements various services like caching, message sending, data exports, and business-specific modules for filtering and data processing (`filters`, `mbrp`, `stock`, `tra`).
*   `ui`: Contains the user interface components.

## Building and Running

### Prerequisites

*   Python 3
*   SQL Server
*   The required Python packages listed in `requirements.txt`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the database:**
    The application requires a `db_config.ini` file in the root directory to connect to the SQL Server database. The application will create a default `db_config.ini` if one is not found. The file should have the following structure:

    ```ini
    [Database]
    server = <your-server-address>
    database = <your-database-name>
    user = <your-username>
    password = <your-password>
    ```
    If `user` and `password` are left blank, the application will use Windows Authentication.

### Running the Application

To run the application, execute the `app.py` script:

```bash
python app.py
```

## Development Conventions

*   **Code Style:** The code generally follows PEP 8 style guidelines.
*   **Modularity:** The code is organized into modules with specific responsibilities, promoting separation of concerns.
*   **Error Handling:** The application includes error handling for database connections and other operations, with custom error codes defined in `pal/core/errors.py`.
*   **Security:** Credentials and sensitive information are handled using the `cryptography` and `keyring` libraries. Passwords are hashed using `bcrypt`.
*   **Logging:** The application uses the `logging` module for logging events and debugging information.
*   **Configuration:** Application settings, including database credentials and module configurations, are managed through the `db_config.ini` file.
*   **Database Schema:** The application automatically creates and migrates the necessary database tables upon initial connection. The schema includes tables for users, roles, permissions, sessions, and audit logs.
